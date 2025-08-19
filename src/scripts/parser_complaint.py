import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, date
import os
import json
import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from urllib.parse import urljoin
import asyncio
from pathlib import Path

BASE_URL = "https://forum.majestic-rp.ru"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
COOKIES_FILE = "majestic_cookies.json"

# Основные форумы жалоб и их закрытые разделы (с указанием статуса)
PLAYER_COMPLAINT_FORUMS = {
    37: {"name": "New York", "closed": {112: "Решено", 172: "Отклонено"}},
    169: {"name": "Detroit", "closed": {173: "Решено", 174: "Отклонено"}},
    247: {"name": "Chicago", "closed": {249: "Решено", 250: "Отклонено"}},
    318: {"name": "San Francisco", "closed": {323: "Решено", 324: "Отклонено"}},
    474: {"name": "Atlanta", "closed": {475: "Решено", 506: "Отклонено"}},
    540: {"name": "San Diego", "closed": {543: "Решено", 544: "Отклонено"}},
    652: {"name": "Los Angeles", "closed": {653: "Решено", 654: "Отклонено"}},
    762: {"name": "Miami", "closed": {763: "Решено", 764: "Отклонено"}},
    859: {"name": "Las Vegas", "closed": {862: "Решено", 863: "Отклонено"}},
    936: {"name": "Washington", "closed": {937: "Решено", 938: "Отклонено"}},
    994: {"name": "Dallas", "closed": {995: "Решено", 996: "Отклонено"}},
    1059: {"name": "Boston", "closed": {1060: "Решено", 1061: "Отклонено"}},
    1148: {"name": "Seattle", "closed": {1149: "Решено", 1150: "Отклонено"}},
    1253: {"name": "Phoenix", "closed": {1254: "Решено", 1255: "Отклонено"}}
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COMPLAINT_DIR = PROJECT_ROOT / "storage/complaint"

class ForumParser:
    def __init__(self, target_date: date = None):
        self.driver = None
        self.target_date = target_date or datetime.now().date()
        
        self.data_dir = COMPLAINT_DIR / str(self.target_date)
        os.makedirs(self.data_dir, exist_ok=True)

    def is_target_date(self, date_str):
        """Проверяет, соответствует ли дата целевому дню"""
        try:
            date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
            return date_obj == self.target_date
        except Exception as e:
            print(f"Ошибка при проверке даты {date_str}: {e}")
            return False

    async def init_driver(self):
        """Инициализация драйвера Selenium"""
        if self.driver is not None:
            return
            
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument(f"user-agent={USER_AGENT}")
        
        self.driver = webdriver.Chrome(options=options)
        
        # Загружаем куки если они есть
        if os.path.exists(COOKIES_FILE):
            with open(COOKIES_FILE, "r") as f:
                cookies = json.load(f)
                self.driver.get(BASE_URL)
                for cookie in cookies:
                    if 'sameSite' in cookie:
                        del cookie['sameSite']
                    self.driver.add_cookie(cookie)
        
        # Проверяем авторизацию
        self.driver.get(BASE_URL)
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.p-navgroup--member"))
            )
        except:
            print("Не удалось загрузить главную страницу, возможно требуется авторизация")
            await self.login_manually()

    async def login_manually(self):
        """Ручная авторизация если куки невалидны"""
        print("Пожалуйста, авторизуйтесь вручную в открывшемся браузере...")
        self.driver.quit()
        
        options = Options()
        options.add_argument(f"user-agent={USER_AGENT}")
        self.driver = webdriver.Chrome(options=options)
        self.driver.get(BASE_URL)
        
        input("После успешной авторизации нажмите Enter для продолжения...")
        
        # Сохраняем куки
        cookies = self.driver.get_cookies()
        with open(COOKIES_FILE, "w") as f:
            json.dump(cookies, f)
            
        print("Куки успешно сохранены")

    async def parse_forum(self, forum_id: int, forum_info: dict):
        """Парсинг конкретного форума только за целевой день"""
        await self.init_driver()
        
        try:
            closed_threads = await self.get_all_closed_threads(forum_id, forum_info["closed"])
            
            data = {
                "forum_id": forum_id,
                "forum_name": forum_info["name"],
                "complaints": closed_threads,
                "last_updated": datetime.now().isoformat(),
                "target_date": self.target_date.isoformat()
            }
            
            filename = f"forum-{forum_id}.json"
            filepath = os.path.join(self.data_dir, filename)
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return data
        except Exception as e:
            print(f"Критическая ошибка при парсинге форума {forum_id}: {e}")
            return None

    async def get_all_closed_threads(self, forum_id: int, closed_forums: dict):
        """Получение всех закрытых тем за целевой день с указанием статуса"""
        threads = []
        
        for closed_forum_id, status in closed_forums.items():
            base_url = f"{BASE_URL}/forums/rassmotrennyye-zhaloby.{closed_forum_id}/"
            page = 1
            closed_urls = []
            stop_parsing = False

            try:
                while not stop_parsing:
                    url = f"{base_url}page-{page}" if page > 1 else base_url
                    print(f"Загружаем страницу закрытых тем: {url}")
                    
                    self.driver.get(url)
                    try:
                        WebDriverWait(self.driver, 20).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.structItemContainer"))
                        )
                    except Exception as e:
                        print(f"Не удалось загрузить страницу {url}: {e}")
                        break
                    
                    soup = BeautifulSoup(self.driver.page_source, "lxml")
                    thread_blocks = soup.select("div.structItem--thread")
                    
                    if not thread_blocks:
                        print(f"Страница {page} закрытых тем пуста (forum_id: {closed_forum_id})")
                        break

                    page_has_target_date = False
                    for thread in thread_blocks:
                        try:
                            title_tag = thread.select_one("a[data-tp-primary='on']")
                            date_tag = thread.select_one("li.structItem-startDate time.u-dt")
                            
                            if not title_tag or not date_tag:
                                continue
                                
                            date_str = date_tag["datetime"].replace("+0300", "+03:00")
                            thread_date = datetime.fromisoformat(date_str).date()
                            
                            # Если тема старше целевой даты - прекращаем парсинг
                            if thread_date < self.target_date:
                                if page > 1:  # Если это не первая страница
                                    stop_parsing = True
                                    break
                                continue  # На первой странице просто пропускаем
                            
                            # Если тема новее целевой даты - продолжаем искать
                            if thread_date > self.target_date:
                                continue
                                
                            thread_url = urljoin(BASE_URL, title_tag["href"])
                            closed_urls.append((thread_url, date_str, status))
                            page_has_target_date = True
                        except Exception as e:
                            print(f"Ошибка при обработке закрытой темы: {e}")
                            continue

                    if stop_parsing:
                        break

                    print(f"Страница {page}: найдено {len(thread_blocks)} тем")

                    # Если на странице не было тем за целевой день и это не первая страница - выходим
                    if not page_has_target_date and page > 1:
                        break

                    # Проверяем наличие следующей страницы
                    next_page = soup.select_one('a.pageNav-jump--next')
                    if not next_page:
                        break

                    page += 1
                    time.sleep(random.uniform(1, 3))

            except Exception as e:
                print(f"Ошибка при парсинге закрытых тем форума {closed_forum_id}: {e}")
                continue

            print(f"Найдено {len(closed_urls)} закрытых тем за {self.target_date} для анализа из форума {closed_forum_id}")

            # Парсим каждую закрытую тему
            for i, (url, created_at, status) in enumerate(closed_urls, 1):
                try:
                    closed_data = await self.parse_closed_thread(url, forum_id, status)
                    if closed_data:
                        closed_data["startDate"] = created_at
                        threads.append(closed_data)
                    print(f"Обработано {i}/{len(closed_urls)} закрытых тем", end="\r")
                except Exception as e:
                    print(f"Ошибка при парсинге темы {url}: {e}")
                    continue

        return threads

    async def parse_closed_thread(self, url: str, forum_id: int, status: str):
        """Парсинг отдельной закрытой темы"""
        try:
            clean_url = url.replace("/unread", "")
            print(f"Парсим закрытую тему: {clean_url}")
            self.driver.get(clean_url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "article.message"))
            )
            
            soup = BeautifulSoup(self.driver.page_source, "lxml")
            
            title_tag = soup.select_one("h1.p-title-value")
            author_tag = soup.select_one("a.username")
            
            admin_posts = [p for p in soup.select("article.message") if p.select_one("span.username--style3, span.username--style9, span.username--style6, username--style40")]
            end_date = admin = None

            if admin_posts:
                closed_tag = admin_posts[-1].select_one("time.u-dt")
                end_date = datetime.fromisoformat(closed_tag['datetime'].replace("+0000", "+00:00")) if closed_tag else None

                admin_tag = admin_posts[-1].select_one("span.username--style3, span.username--style9, span.username--style6")
                admin = admin_tag.text.strip() if admin_tag else None

            # Получаем ID жалобы из URL
            report_id = clean_url.split(".")[-1].split("/")[0] if "." in clean_url else None
            
            # Вычисляем длительность
            duration_str = ""
            if end_date:
                start_date = datetime.fromisoformat(soup.select_one("time.u-dt")['datetime'].replace("+0000", "+00:00"))
                duration = end_date - start_date
                days = duration.days
                hours, remainder = divmod(duration.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                duration_str = f"{days}d {hours}h {minutes}m {seconds}s"

            return {
                "forum_id": forum_id,
                "title": title_tag.text.strip() if title_tag else None,
                "author": author_tag.text.strip() if author_tag else None,
                "admin": admin,
                "status": status,
                "startDate": None,
                "endDate": end_date.isoformat() if end_date else None,
                "link": clean_url,
                "report_id": report_id,
                "durationFormatted": duration_str
            }
        except Exception as e:
            print(f"Ошибка при парсинге закрытой темы {url}: {e}")
            return None

    async def run_daily_parse(self):
        """Парсинг всех форумов за целевой день"""
        try:
            await self.init_driver()
            
            all_data = {}
            for forum_id, forum_info in PLAYER_COMPLAINT_FORUMS.items():
                print(f"\nПарсинг форума {forum_info['name']} (ID: {forum_id})...")
                forum_data = await self.parse_forum(forum_id, forum_info)
                if forum_data:
                    all_data[forum_id] = forum_data
                time.sleep(random.uniform(2, 5))
            
            return all_data
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

async def scheduled_parser(target_date: date = None):
    """Запланированный парсер для конкретной даты"""
    parser = ForumParser(target_date=target_date)
    try:
        await parser.run_daily_parse()
        print(f"Парсинг за {target_date} успешно завершен")
    except Exception as e:
        print(f"Ошибка при парсинге: {e}")

def run_parser_for_date(target_date: str):
    """Запуск парсера для конкретной даты"""
    try:
        if isinstance(target_date, str):
            parts = target_date.split('-')
            if len(parts) == 3:
                year, month, day = parts
                month = month.zfill(2)
                day = day.zfill(2)
                normalized_date = f"{year}-{month}-{day}"
                target_date = date.fromisoformat(normalized_date)
            else:
                raise ValueError("Неверный формат даты. Ожидается YYYY-MM-DD")
        
        asyncio.create_task(scheduled_parser(target_date))
    except ValueError as e:
        print(f"Ошибка в формате даты: {e}")

def run_parser_background():
    """Запуск парсера в фоновом режиме (для текущей даты)"""
    asyncio.create_task(scheduled_parser())