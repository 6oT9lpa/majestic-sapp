from fastapi import Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from urllib.parse import urlparse
from sqlalchemy import func
from typing import List, Optional, Dict, Tuple
from pathlib import Path
import uuid

from src.database import get_session
from src.models.user_model import MultiAccountLog, MultiAccountFile, MultiAccount

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STORAGE_PATH = PROJECT_ROOT / "storage/files"

class MultiAccountService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_multi_accounts(
        self,
        page: int = 1,
        per_page: int = 20
    ) -> dict:
        """Получить список мультиаккаунтов"""
        offset = (page - 1) * per_page
        
        query = select(MultiAccount)
        
        count_query = select(func.count()).select_from(query)
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()
        
        result = await self.session.execute(
            query.order_by(MultiAccount.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        
        accounts = result.scalars().all()
        
        accounts_data = []
        for account in accounts:
            accounts_data.append({
                "id": str(account.id),
                "main_account": {
                    "url": account.main_account_url,
                    "id": account.main_account_id,
                    "name": account.main_account_name
                },
                "accounts_count": len(account.accounts_data) + 1,
                "comment_preview": account.comment[:100] + "..." if account.comment and len(account.comment) > 100 else account.comment,
                "created_at": account.created_at.isoformat(),
                "created_by": str(account.created_by)
            })
        
        return {
            "accounts": accounts_data,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }
        
    async def add_multi_accounts(
        self,
        main_account_url: str,
        accounts: List[Dict],
        comment: Optional[str],
        current_user: Dict
    ) -> MultiAccount:
        """Добавить запись о мультиаккаунтах"""
        
        path = urlparse(main_account_url).path
        last_part = path.strip("/").split("/")[-1]
        name_, id_ = last_part.split(".")
        
        new_account = MultiAccount(
            main_account_url=main_account_url,
            main_account_id=int(id_),
            main_account_name=name_,
            accounts_data=accounts,
            comment=comment,
            created_by=current_user["id"]
        )
        
        self.session.add(new_account)
        await self.session.commit()
        await self.session.refresh(new_account)
        
        log = MultiAccountLog(
            multi_account_id=new_account.id,
            action_type="created",
            action_details={
                "main_account": main_account_url,
                "accounts_count": len(accounts),
                "comment": comment
            },
            changed_by=current_user["id"]
        )
        self.session.add(log)
        await self.session.commit()
        
        return new_account
    
    async def get_multi_account_details(self, account_id: uuid.UUID) -> dict:
        """Получить детальную информацию о мультиаккаунте"""
        account = await self.session.get(MultiAccount, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Запись не найдена")
        
        # Получаем логи
        logs_result = await self.session.execute(
            select(MultiAccountLog)
            .options(joinedload(MultiAccountLog.user)) 
            .where(MultiAccountLog.multi_account_id == account_id)
            .order_by(MultiAccountLog.changed_at.desc())
        )
        logs = logs_result.unique().scalars().all()
    
        return {
            "account": {
                "id": str(account.id),
                "main_account": {
                    "url": account.main_account_url,
                    "id": account.main_account_id,
                    "name": account.main_account_name
                },
                "accounts": account.accounts_data,
                "comment": account.comment,
                "created_at": account.created_at.isoformat(),
                "created_by": str(account.created_by)
            },
            "logs": [{
                "id": str(log.id),
                "action_type": log.action_type,
                "action_details": log.action_details,
                "changed_by": str(log.changed_by),
                "changed_at": log.changed_at.isoformat(),
                "user_name": log.user.username if log.user else "Unknown"
            } for log in logs],
        }

    async def update_account_type(
        self,
        multi_account_id: uuid.UUID,
        account_id: int,
        account_url: str,
        new_type: str,
        current_user: Dict
    ):
        """Изменить тип аккаунта"""
        account = await self.session.get(MultiAccount, multi_account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Запись не найдена")
        
        # Проверяем, что аккаунт существует в списке
        account_found = False
        updated_accounts = []
        
        for acc in account.accounts_data:
            if acc.get('id') == account_id:
                acc['type'] = new_type
                account_found = True
            updated_accounts.append(acc)
        
        if not account_found:
            if account.main_account_id == account_id:
                return
            raise HTTPException(status_code=404, detail="Аккаунт не найден в списке")
        
        account.accounts_data = updated_accounts
        account.updated_at = func.now()
        
        self.session.add(account)
        
        # Добавляем запись в лог
        log = MultiAccountLog(
            multi_account_id=multi_account_id,
            action_type="account_type_changed",
            action_details={
                "account_id": account_id,
                "account_url": account_url,
                "new_type": new_type
            },
            changed_by=current_user["id"]
        )
        self.session.add(log)
        
        await self.session.commit()

    async def set_main_account(
        self,
        multi_account_id: uuid.UUID,
        new_main_account_id: int,
        new_main_account_url: str,
        new_main_account_name: str,
        current_user: Dict
    ):
        """Установить новый основной аккаунт"""
        account = await self.session.get(MultiAccount, multi_account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Запись не найдена")
        
        # Находим информацию о новом основном аккаунте
        new_main_account = None
        updated_accounts = []
        account_found = False
        
        for acc in account.accounts_data:
            if acc.get('id') == new_main_account_id:
                new_main_account = acc
                account_found = True
            else:
                updated_accounts.append(acc)
        
        if not account_found:
            if account.main_account_id == new_main_account_id:
                raise HTTPException(status_code=400, detail="Аккаунт уже является основным")
            raise HTTPException(status_code=404, detail="Аккаунт не найден в списке")
        
        old_main_account = {
            'url': account.main_account_url,
            'name': account.main_account_name,
            'id': account.main_account_id,
            'type': 'multi'
        }
        updated_accounts.append(old_main_account)
        
        # Обновляем данные
        account.main_account_url = new_main_account_url
        account.main_account_id = new_main_account_id
        account.main_account_name = new_main_account_name
        account.accounts_data = updated_accounts
        account.updated_at = func.now()
        
        self.session.add(account)
        
        # Добавляем запись в лог
        log = MultiAccountLog(
            multi_account_id=multi_account_id,
            action_type="main_account_changed",
            action_details={
                "old_main_account": {
                    "id": old_main_account['id'],
                    "name": old_main_account['name']
                },
                "new_main_account": {
                    "id": new_main_account_id,
                    "name": new_main_account_name
                }
            },
            changed_by=current_user["id"]
        )
        self.session.add(log)
        
        await self.session.commit()
    
    async def add_account_to_multi(
        self,
        multi_account_id: uuid.UUID,
        account_url: str,
        account_id: int,
        account_name: str,
        account_type: str,
        current_user: Dict
    ):
        """Добавить аккаунт к существующей записи мультиаккаунтов"""
        account = await self.session.get(MultiAccount, multi_account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Запись не найдена")

        if account.main_account_id == account_id:
            raise HTTPException(status_code=400, detail="Аккаунт уже является основным")
        
        for existing_account in account.accounts_data:
            if existing_account.get('id') == account_id:
                raise HTTPException(status_code=400, detail="Аккаунт уже добавлен")
        
        new_account = {
            'url': account_url,
            'name': account_name,
            'id': account_id,
            'type': account_type
        }
        
        updated_accounts = account.accounts_data + [new_account]
        account.accounts_data = updated_accounts
        account.updated_at = func.now()
        
        self.session.add(account)
        
        log = MultiAccountLog(
            multi_account_id=multi_account_id,
            action_type="account_added",
            action_details={
                "account_id": account_id,
                "account_url": account_url,
                "account_name": account_name,
                "account_type": account_type
            },
            changed_by=current_user["id"]
        )
        self.session.add(log)
        
        await self.session.commit()
    
    async def update_multi_account_comment(
        self,
        account_id: uuid.UUID,
        comment: Optional[str],
        current_user: Dict
    ):
        """Обновить комментарий мультиаккаунта"""
        account = await self.session.get(MultiAccount, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Запись не найдена")
        
        account.comment = comment
        account.updated_at = func.now()
        
        self.session.add(account)
        
        log = MultiAccountLog(
            multi_account_id=account_id,
            action_type="comment_updated",
            action_details={
                "comment": comment
            },
            changed_by=current_user["id"]
        )
        self.session.add(log)
        
        await self.session.commit()
    
    async def upload_multi_account_file(
        self,
        account_id: uuid.UUID,
        file: UploadFile,
        content: bytes,
        current_user: Dict
    ) -> Dict:
        """Загрузить файл для мультиаккаунта"""
        account = await self.session.get(MultiAccount, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Запись не найдена")
        
        account_dir = STORAGE_PATH / str(account_id)
        account_dir.mkdir(parents=True, exist_ok=True)
        
        file_extension = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = account_dir / unique_filename
        
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        file_record = MultiAccountFile(
            id=uuid.uuid4(),
            multi_account_id=account_id,
            filename=file.filename,
            file_size=len(content),
            file_path=str(file_path),
            uploaded_by=current_user["id"]
        )
        
        self.session.add(file_record)
        await self.session.commit()
        await self.session.refresh(file_record)
        
        return {
            "id": str(file_record.id),
            "filename": file_record.filename,
            "file_size": file_record.file_size,
            "uploaded_at": file_record.uploaded_at.isoformat(),
            "uploaded_by": str(file_record.uploaded_by)
        }
    
    async def get_multi_account_files(self, account_id: uuid.UUID) -> List[Dict]:
        """Получить список файлов мультиаккаунта"""
        
        result = await self.session.execute(
            select(MultiAccountFile)
            .options(joinedload(MultiAccountFile.uploaded_by_user))
            .where(MultiAccountFile.multi_account_id == account_id)
            .order_by(MultiAccountFile.uploaded_at.desc())
        )
        
        files = result.unique().scalars().all()
        
        return [{
            "id": str(file.id),
            "filename": file.filename,
            "file_size": file.file_size,
            "uploaded_at": file.uploaded_at.isoformat(),
            "uploaded_by": str(file.uploaded_by),
            "uploaded_by_name": file.uploaded_by_user.username if file.uploaded_by_user else "Unknown"
        } for file in files]

    async def get_file_path(self, account_id: uuid.UUID, file_id: uuid.UUID) -> Tuple[Path, str]:
        """Получить путь к файлу и оригинальное имя"""
        
        file_record = await self.session.get(MultiAccountFile, file_id)
        if not file_record or file_record.multi_account_id != account_id:
            raise HTTPException(status_code=404, detail="Файл не найден")
        
        return Path(file_record.file_path), file_record.filename
    
    async def delete_multi_account_file(
        self,
        account_id: uuid.UUID,
        file_id: uuid.UUID,
        current_user: Dict
    ):
        """Удалить файл мультиаккаунта"""
        
        file_record = await self.session.get(MultiAccountFile, file_id)
        if not file_record or file_record.multi_account_id != account_id:
            raise HTTPException(status_code=404, detail="Файл не найден")
        
        file_path = Path(file_record.file_path)
        if file_path.exists():
            file_path.unlink()
        
        await self.session.delete(file_record)
        
        log = MultiAccountLog(
            multi_account_id=account_id,
            action_type="file_deleted",
            action_details={
                "filename": file_record.filename,
                "file_id": str(file_id)
            },
            changed_by=current_user["id"]
        )
        self.session.add(log)
        
        await self.session.commit()
    
    
async def get_multi_account_service(session: AsyncSession = Depends(get_session)) -> MultiAccountService:
    return MultiAccountService(session)