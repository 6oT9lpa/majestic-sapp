from tkinter import SE
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, and_, func
from typing import Optional, Dict, List
from pathlib import Path
from datetime import datetime, timedelta, date
from collections import defaultdict
import os
import json
import re

from src.database import get_session
from src.models.appeal_model import (
    Appeal,
    AppealStatus,
    AppealType,
    AppealAssignment,
)
from src.models.user_model import User

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COMPLAINT_DIR = PROJECT_ROOT / "storage/complaint"
USER_STATS_DIR = PROJECT_ROOT / "storage/user_stats"
USER_STATS_FILE = USER_STATS_DIR / "custom_stats.json"

SETTINGS_DIR = PROJECT_ROOT / "storage/settings"
REWARD_SETTINGS_PATH = SETTINGS_DIR / "reward_settings.json"

class ReportService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.data_dir = COMPLAINT_DIR
        os.makedirs(COMPLAINT_DIR, exist_ok=True)
        os.makedirs(USER_STATS_DIR, exist_ok=True)
        
        if not USER_STATS_FILE.exists():
            with open(USER_STATS_FILE, 'w') as f:
                json.dump({}, f)
    
    async def _load_all_complaints_from_files(self) -> List[Dict]:
        """Загрузка всех жалоб из всех файлов в формате ddmmyyyy_reports.json"""
        all_complaints = []
        
        try:
            # Ищем все файлы с паттерном ddmmyyyy_reports.json
            pattern = re.compile(r'\d{8}_reports\.json$')
            json_files = [f for f in os.listdir(self.data_dir) if pattern.match(f)]
            
            for filename in json_files:
                file_path = self.data_dir / filename
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        file_data = json.load(f)
                        if isinstance(file_data, list):
                            all_complaints.extend(file_data)
                except Exception as e:
                    print(f"Ошибка при чтении файла {filename}: {str(e)}")
                    continue
            
            return all_complaints
            
        except Exception as e:
            print(f"Ошибка при загрузке жалоб из файлов: {str(e)}")
            return []
        
    async def get_complaints(
        self,
        status: str = "all",
        date: Optional[str] = None,
        admin: str = "",
        page: int = 1,
        per_page: int = 20
    ) -> Dict:
        """Получение жалоб с фильтрацией из нового формата JSON"""
        try:
            all_complaints = await self._load_all_complaints_from_files()
        
            if not all_complaints:
                return {
                    "complaints": [],
                    "total": 0,
                    "page": page,
                    "per_page": per_page
                }

            if status != "all":
                all_complaints = [c for c in all_complaints if c.get("status") == status]

            if admin:
                admin_lower = admin.lower()
                all_complaints = [c for c in all_complaints 
                                if c.get("staff") and admin_lower in c["staff"].lower()]

            if date:
                all_complaints = [c for c in all_complaints 
                                if c.get("reportDate") == date]

            all_complaints.sort(key=lambda x: x.get("startDate", ""), reverse=True)

            total = len(all_complaints)
        
            start = (page - 1) * per_page
            end = start + per_page
            paginated = all_complaints[start:end]
            
            return {
                "complaints": paginated,
                "total": total,
                "page": page,
                "per_page": per_page
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка при получении жалоб: {str(e)}")
    
    async def get_delayed_complaints(
        self,
        page: int = 1,
        per_page: int = 20,
        admin: str = "",
    ) -> Dict:
        """Получение просроченных жалоб из нового формата JSON"""
        try:
            # Получаем все закрытые жалобы
            all_closed = await self.get_complaints(
                status="Решено",
                date=None,
                admin=admin,
                page=1,
                per_page=10000
            )
            
            delayed = []
            for complaint in all_closed["complaints"]:
                try:
                    if not complaint.get("startDate") or not complaint.get("endDate"):
                        continue

                    start = datetime.strptime(complaint["startDate"], "%Y-%m-%dT%H:%M:%S%z")
                    end = datetime.strptime(complaint["endDate"], "%Y-%m-%dT%H:%M:%S%z")
                    processing_hours = (end - start).total_seconds() / 3600

                    if processing_hours > 24:
                        complaint["delay_hours"] = int(processing_hours - 24)
                        delayed.append(complaint)

                except Exception as e:
                    print(f"Ошибка при обработке жалобы {complaint.get('report_id')}: {str(e)}")
                    continue
            
            # Сортируем по времени просрочки
            delayed.sort(key=lambda x: x["delay_hours"], reverse=True)
            
            # Пагинация
            total = len(delayed)
            start = (page - 1) * per_page
            end = start + per_page
            paginated = delayed[start:end]
            
            return {
                "complaints": paginated,
                "total": total,
                "page": page,
                "per_page": per_page
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка при получении просроченных жалоб: {str(e)}")
    
    async def get_appeal_stats(
        self,
        status: Optional[List[AppealStatus]] = None,
        appeal_type: Optional[List[AppealType]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 20,
        moderator: Optional[str] = None
    ) -> Dict:
        """Получение статистики по всем обращениям"""
        if status is None:
            status = [AppealStatus.IN_PROGRESS, AppealStatus.PENDING, 
                    AppealStatus.REJECTED, AppealStatus.RESOLVED]
        if appeal_type is None:
            appeal_type = [AppealType.AMNESTY, AppealType.COMPLAINT, AppealType.HELP]
        
        query = select(Appeal).options(
            selectinload(Appeal.assignments),
            selectinload(Appeal.user)
        )
        
        conditions = []
        if status:
            conditions.append(Appeal.status.in_(status))
        if appeal_type:
            conditions.append(Appeal.type.in_(appeal_type))
        if date_from:
            conditions.append(Appeal.created_at >= date_from)
        if date_to:
            conditions.append(Appeal.created_at <= date_to + timedelta(days=1))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Пагинация
        total_query = select(func.count()).select_from(Appeal)
        if conditions:
            total_query = total_query.where(and_(*conditions))
        
        total_result = await self.session.execute(total_query)
        total = total_result.scalar()
        
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        # Выполнение запроса
        result = await self.session.execute(query)
        appeals = result.unique().scalars().all()
        
        # Формирование ответа
        appeals_data = []
        for appeal in appeals:
            # Получаем последнее назначение по времени (даже если оно завершено)
            last_assignment = None
            if appeal.assignments:
                last_assignment = max(
                    appeal.assignments,
                    key=lambda a: a.released_at or a.assigned_at
                )
            
            # Проверяем фильтр по модератору
            if moderator and (not last_assignment or 
                        not last_assignment.user or 
                        moderator.lower() not in last_assignment.user.username.lower()):
                continue
                
            appeal_data = {
                "id": str(appeal.id),
                "type": appeal.type.value,
                "status": appeal.status.value,
                "created_at": appeal.created_at.isoformat(),
                "creator": appeal.user.username if appeal.user else "Аноним",
                "moderator": last_assignment.user.username if last_assignment and last_assignment.user else None,
                "assigned_at": last_assignment.assigned_at.isoformat() if last_assignment else None,
                "closed_at": (last_assignment.released_at or last_assignment.assigned_at).isoformat() 
                            if last_assignment and appeal.status in [AppealStatus.RESOLVED, AppealStatus.REJECTED] 
                            else None,
                "resolution": appeal.status.value if appeal.status in [AppealStatus.RESOLVED, AppealStatus.REJECTED] else None
            }
            
            appeals_data.append(appeal_data)
        
        # Применяем фильтр по модератору к общему количеству
        if moderator:
            total = len(appeals_data)
            start = (page - 1) * per_page
            end = start + per_page
            appeals_data = appeals_data[start:end]
        
        return {
            "appeals": appeals_data,
            "total": total,
            "page": page,
            "per_page": per_page
        }
    
    async def get_user_stats(
        self,
        admin_name: str = "",
        page: int = 1,
        per_page: int = 20
    ) -> Dict:
        """Получение статистики по пользователям с учетом кастомных данных"""
        try:
            standard_stats = await self._get_standard_user_stats(admin_name)
            custom_stats = await self._load_custom_stats()

            merged_stats = []
            for user in standard_stats:
                username = user['username']
                if username in custom_stats:
                    updated_user = {
                        'username': username,
                        'server': custom_stats[username].get('server', user.get('server', "Не указан")),
                        'complaints_resolved': custom_stats[username].get('complaints_resolved', user['complaints_resolved']),
                        'complaints_rejected': custom_stats[username].get('complaints_rejected', user['complaints_rejected']),
                        'bans_issued': custom_stats[username].get('bans_issued', user.get('bans_issued', 0)),
                        'delays': custom_stats[username].get('delays', user['delays']),
                        'fine': custom_stats[username].get('fine', user['fine']),
                        'appeals_resolved': user['appeals_resolved'],
                        'appeals_rejected': user['appeals_rejected'],
                        'total': (custom_stats[username].get('complaints_resolved', user['complaints_resolved']) * 50 +
                                user['appeals_resolved'] * 30 -
                                custom_stats[username].get('fine', user['fine'])),
                        'payment_status': "Ожидает" if (custom_stats[username].get('complaints_resolved', user['complaints_resolved']) * 50 +
                                                    user['appeals_resolved'] * 30 -
                                                    custom_stats[username].get('fine', user['fine'])) > 0 else "Выплачено"
                    }
                    merged_stats.append(updated_user)
                else:
                    user['server'] = user.get('server', "Не указан")
                    merged_stats.append(user)
            
            merged_stats.sort(key=lambda x: x["total"], reverse=True)
            total = len(merged_stats)
            start = (page - 1) * per_page
            end = start + per_page
            paginated = merged_stats[start:end]
            
            return {
                "users": paginated,
                "total": total,
                "page": page,
                "per_page": per_page
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка при получении статистики пользователей: {str(e)}")

    async def get_user_activity(self, month: int = None, year: int = None) -> Dict:
        """Получение данных активности пользователей для графика по конкретному месяцу и году"""
        try:
            now = datetime.now()
            if month is None:
                month = now.month
            if year is None:
                year = now.year
                    
            start_date = datetime(year, month, 1)
            end_date = datetime(year, month + 1, 1) - timedelta(days=1) if month < 12 else datetime(year + 1, 1, 1) - timedelta(days=1)

            days_in_month = (end_date - start_date).days + 1
            labels = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') 
                    for i in range(days_in_month)]

            db_users = set()
            db_activity = defaultdict(lambda: defaultdict(int))
            
            query = select(
                User.username,
                func.date(Appeal.created_at).label("date"),
                func.count(Appeal.id)
            ).join(
                AppealAssignment,
                AppealAssignment.appeal_id == Appeal.id
            ).join(
                User,
                AppealAssignment.user_id == User.id
            ).where(
                and_(
                    Appeal.created_at >= start_date,
                    Appeal.created_at <= end_date
                )
            ).group_by(User.username, func.date(Appeal.created_at))
            
            result = await self.session.execute(query)
            for row in result:
                username = row[0]
                date = row[1]
                count = row[2]
                db_users.add(username)
                db_activity[username][date.strftime('%Y-%m-%d')] = count
                
            file_users = set()
            file_activity = defaultdict(lambda: defaultdict(int))
            
            all_complaints = await self._load_all_complaints_from_files()
        
            for complaint in all_complaints:
                if not complaint.get('staff'):
                    continue
                    
                try:
                    date_obj = datetime.strptime(
                        complaint["startDate"], 
                        "%Y-%m-%dT%H:%M:%S%z"
                    ).date()
                    date_str = date_obj.strftime('%Y-%m-%d')
                    
                    if start_date.date() <= date_obj <= end_date.date():
                        username = complaint['staff']
                        file_users.add(username)
                        file_activity[username][date_str] += 1
                except Exception as e:
                    print(f"Ошибка обработки жалобы: {e}")
                    continue

            all_users = db_users.union(file_users)
            
            datasets = []
            for username in all_users:
                combined_data = []
                for date_str in labels:
                    db_count = db_activity.get(username, {}).get(date_str, 0)
                    file_count = file_activity.get(username, {}).get(date_str, 0)
                    combined_data.append(db_count + file_count)
                
                if sum(combined_data) > 0:
                    datasets.append({
                        'label': username,
                        'data': combined_data,
                        'borderColor': self._get_random_color(username),
                        'backgroundColor': self._get_random_color(username),
                        'tension': 0.1,
                        'fill': False
                    })

            return {
                'labels': labels,
                'datasets': datasets
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Ошибка при формировании данных графика: {str(e)}"
            )
    
    async def get_reward_settings(self) -> Dict:
        """Получение текущих настроек вознаграждений из JSON"""
        try:
            if not REWARD_SETTINGS_PATH.exists():
                default_settings = {
                    "complaint_reward": 50,
                    "appeal_reward": 30,
                    "delay_penalty": 100,
                    "updated_at": datetime.utcnow().isoformat()
                }
                await self._save_reward_settings(default_settings)
                return default_settings
            
            with open(REWARD_SETTINGS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка загрузки настроек: {str(e)}"
            )

    async def update_reward_settings(self, settings_data: Dict) -> Dict:
        """Обновление настроек вознаграждений в JSON"""
        try:
            current_settings = await self.get_reward_settings()
            updated_settings = {
                **current_settings,
                **settings_data,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            await self._save_reward_settings(updated_settings)
            return updated_settings
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка обновления настроек: {str(e)}"
            )

    async def _save_reward_settings(self, settings: Dict) -> None:
        """Сохранение настроек в файл"""
        with open(REWARD_SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    
    def _get_date_dirs(self, date_filter: Optional[str] = None) -> List[Path]:
        """Получает список папок с датами, отфильтрованных по параметру"""
        date_dirs = []
        for entry in os.listdir(self.data_dir):
            entry_path = Path(self.data_dir) / entry
            if entry_path.is_dir():
                try:
                    dir_date = date.fromisoformat(entry)
                    if date_filter is None or entry == date_filter:
                        date_dirs.append(entry_path)
                except ValueError:
                    continue
        return date_dirs

    async def _get_top_active_users(self, date_from: datetime) -> List[str]:
        """Получение топ 10 самых активных пользователей"""
        date_dirs = []
        for entry in os.listdir(self.data_dir):
            entry_path = Path(self.data_dir) / entry
            if entry_path.is_dir():
                try:
                    dir_date = date.fromisoformat(entry)
                    if dir_date >= date_from.date():
                        date_dirs.append(entry_path)
                except ValueError:
                    continue
        
        complaint_users = defaultdict(int)
        for date_dir in date_dirs:
            files = [f for f in os.listdir(date_dir) if f.startswith("forum-") and f.endswith(".json")]
            
            for filename in files:
                filepath = date_dir / filename
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for complaint in data.get("complaints", []):
                        if complaint.get("admin"):
                            complaint_users[complaint["admin"]] += 1
        
        appeal_query = select(
            User.username,
            func.count(Appeal.id)
        ).join(
            AppealAssignment,
            AppealAssignment.user_id == User.id
        ).join(
            Appeal,
            Appeal.id == AppealAssignment.appeal_id
        ).where(
            Appeal.created_at >= date_from
        ).group_by(User.username)
        
        appeal_result = await self.session.execute(appeal_query)
        appeal_users = {username: count for (username, count) in appeal_result.unique().all()}
        
        # Объединяем и сортируем
        all_users = set(list(complaint_users.keys()) + list(appeal_users.keys()))
        user_activity = []
        
        for user in all_users:
            if user:
                total = complaint_users.get(user, 0) + appeal_users.get(user, 0)
                user_activity.append((user, total))
        
        user_activity.sort(key=lambda x: x[1], reverse=True)
        return [user[0] for user in user_activity[:10] if user[0]]

    async def _get_user_complaints(self, username: str, date_from: datetime) -> Dict[str, int]:
        """Получение количества жалоб пользователя по дням"""
        if not username:
            return {}
            
        date_dirs = []
        for entry in os.listdir(self.data_dir):
            entry_path = Path(self.data_dir) / entry
            if entry_path.is_dir():
                try:
                    dir_date = date.fromisoformat(entry)
                    if dir_date >= date_from.date():
                        date_dirs.append(entry_path)
                except ValueError:
                    continue
        
        date_counts = defaultdict(int)
        for date_dir in date_dirs:
            files = [f for f in os.listdir(date_dir) if f.startswith("forum-") and f.endswith(".json")]
            
            for filename in files:
                filepath = date_dir / filename
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for complaint in data.get("complaints", []):
                        if complaint.get("admin", "") == username:
                            try:
                                date_obj = datetime.fromisoformat(complaint["startDate"].replace('Z', '+00:00')).date()
                                date_str = date_obj.isoformat()
                                date_counts[date_str] += 1
                            except:
                                pass
        return date_counts

    async def _get_user_appeals(self, username: str, date_from: datetime) -> Dict[str, int]:
        """Получение количества обращений пользователя по дням"""
        if not username:
            return {}
            
        query = select(
            func.date(Appeal.created_at).label("date"),
            func.count(Appeal.id)
        ).join(
            AppealAssignment,
            AppealAssignment.appeal_id == Appeal.id
        ).join(
            User,
            AppealAssignment.user_id == User.id
        ).where(
            and_(
                User.username == username,
                Appeal.created_at >= date_from
            )
        ).group_by(func.date(Appeal.created_at))
        
        result = await self.session.execute(query)
        return {date.isoformat(): count for (date, count) in result.unique().all()}

    def _get_random_color(self, username: str) -> str:
        """Генерация цвета на основе имени пользователя для консистентности"""
        if not username:
            return "rgb(0, 0, 0)"
            
        hash_val = hash(username)
        r = (hash_val & 0xFF0000) >> 16
        g = (hash_val & 0x00FF00) >> 8
        b = hash_val & 0x0000FF
        return f"rgb({r}, {g}, {b})"

    async def _load_custom_stats(self) -> Dict:
        with open(USER_STATS_FILE, 'r') as f:
            return json.load(f)

    async def _save_custom_stats(self, stats: Dict) -> None:
        with open(USER_STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=2)
    
    async def _get_standard_user_stats(self, admin_name: str = "") -> List[Dict]:
        """Получение стандартной статистики из нового формата JSON"""
        try:
            settings = await self.get_reward_settings()
            COMPLAINT_REWARD = settings["complaint_reward"]  # Вознаграждение за решенную жалобу
            COMPLAINT_REJECTED_REWARD = settings.get("complaint_rejected_reward", 0)  # Вознаграждение за отклоненную жалобу
            BAN_REWARD = settings.get("ban_reward", 0)  # Вознаграждение за выданный бан
            APPEAL_REWARD = settings["appeal_reward"]  # Вознаграждение за закрытое обращение
            DELAY_PENALTY = settings["delay_penalty"]  # Штраф за просрочку
            
            all_complaints = await self._load_all_complaints_from_files()

            # Группируем по администраторам
            admin_stats = defaultdict(lambda: {
                'complaints_resolved': 0,  # Решенные жалобы
                'complaints_rejected': 0,  # Отклоненные жалобы
                'bans_issued': 0,         # Выданные баны
                'delays': 0               # Просрочки
            })
            
            for complaint in all_complaints:
                admin_name_complaint = complaint.get("staff")
                if not admin_name_complaint:
                    continue

                # Фильтрация по имени администратора, если указано
                if admin_name and admin_name.lower() not in admin_name_complaint.lower():
                    continue

                # Считаем статусы жалоб
                if complaint.get("status") == "Решено":
                    admin_stats[admin_name_complaint]['complaints_resolved'] += 1
                    
                    # Проверяем просрочку
                    if complaint.get("startDate") and complaint.get("endDate"):
                        try:
                            start = datetime.strptime(complaint["startDate"], "%Y-%m-%dT%H:%M:%S%z")
                            end = datetime.strptime(complaint["endDate"], "%Y-%m-%dT%H:%M:%S%z")
                            if (end - start).total_seconds() / 3600 > 24:
                                admin_stats[admin_name_complaint]['delays'] += 1
                        except:
                            pass
                            
                elif complaint.get("status") == "Отклонено":
                    admin_stats[admin_name_complaint]['complaints_rejected'] += 1
                
                # Считаем выданные баны
                if "бан" in complaint.get("title", "").lower() or "ban" in complaint.get("title", "").lower():
                    admin_stats[admin_name_complaint]['bans_issued'] += 1
            
            # Получаем статистику по обращениям из БД
            appeal_query = select(
                User.username,
                func.count(Appeal.id),
                Appeal.status
            ).join(
                AppealAssignment,
                AppealAssignment.appeal_id == Appeal.id
            ).join(
                User,
                AppealAssignment.user_id == User.id
            )
            
            if admin_name:
                appeal_query = appeal_query.where(User.username.ilike(f"%{admin_name}%"))
            
            appeal_query = appeal_query.group_by(User.username, Appeal.status)
            
            appeal_result = await self.session.execute(appeal_query)
            
            appeal_stats = defaultdict(lambda: {
                'appeals_resolved': 0,  # Закрытые обращения
                'appeals_rejected': 0   # Отклоненные обращения
            })
            
            for username, count, status in appeal_result.unique().all():
                if status == AppealStatus.RESOLVED:
                    appeal_stats[username]['appeals_resolved'] = count
                elif status == AppealStatus.REJECTED:
                    appeal_stats[username]['appeals_rejected'] = count
            
            # Формируем итоговую статистику
            user_stats = []
            all_usernames = set(admin_stats.keys()).union(set(appeal_stats.keys()))
            
            for username in all_usernames:
                # Расчет вознаграждения
                total = (
                    admin_stats[username]['complaints_resolved'] * COMPLAINT_REWARD +  # Решенные жалобы
                    admin_stats[username]['complaints_rejected'] * COMPLAINT_REJECTED_REWARD +  # Отклоненные жалобы
                    admin_stats[username]['bans_issued'] * BAN_REWARD +  # Выданные баны
                    appeal_stats[username]['appeals_resolved'] * APPEAL_REWARD -  # Закрытые обращения
                    admin_stats[username]['delays'] * DELAY_PENALTY  # Штраф за просрочки
                )
                
                # Если сумма отрицательная - устанавливаем 0
                total = max(0, total)
                
                stats = {
                    'username': username,
                    'complaints_resolved': admin_stats[username]['complaints_resolved'],
                    'complaints_rejected': admin_stats[username]['complaints_rejected'],
                    'bans_issued': admin_stats[username]['bans_issued'],
                    'delays': admin_stats[username]['delays'],
                    'fine': admin_stats[username]['delays'] * DELAY_PENALTY,
                    'appeals_resolved': appeal_stats[username]['appeals_resolved'],
                    'appeals_rejected': appeal_stats[username]['appeals_rejected'],
                    'total': total,
                    'payment_status': "Ожидает" if total > 0 else "Выплачено"
                }
                user_stats.append(stats)
            
            return user_stats
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка при формировании стандартной статистики: {str(e)}")
    
async def get_report_service(session: AsyncSession = Depends(get_session)) -> ReportService:
    return ReportService(session)

