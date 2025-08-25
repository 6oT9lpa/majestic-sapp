import datetime
from fastapi import  WebSocket
from typing import Dict, List
from datetime import datetime, timedelta

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.last_message_time: Dict[str, Dict[str, datetime]] = {}
        
        self.appeal_list_connections: List[WebSocket] = []
        self.user_specific_listeners: Dict[str, List[WebSocket]] = {}

    async def connect(self, appeal_id: str, websocket: WebSocket):
        if appeal_id not in self.active_connections:
            self.active_connections[appeal_id] = []
        self.active_connections[appeal_id].append(websocket)

    def disconnect(self, appeal_id: str, websocket: WebSocket):
        if appeal_id in self.active_connections:
            if websocket in self.active_connections[appeal_id]:
                self.active_connections[appeal_id].remove(websocket)
            if not self.active_connections[appeal_id]:
                del self.active_connections[appeal_id]

    async def send_message(self, appeal_id: str, message: dict):
        if appeal_id in self.active_connections:
            for connection in self.active_connections[appeal_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    self.disconnect(appeal_id, connection)
                
    def can_send_message(self, appeal_id: str, user_id: str) -> bool:
        now = datetime.now()
        
        if appeal_id not in self.active_connections:
            if appeal_id in self.last_message_time and user_id in self.last_message_time[appeal_id]:
                del self.last_message_time[appeal_id][user_id]
            return True
        
        last_msg = self.last_message_time.get(appeal_id, {}).get(user_id)
        if last_msg and (now - last_msg) < timedelta(seconds=5):
            return False
        
        if appeal_id not in self.last_message_time:
            self.last_message_time[appeal_id] = {}
        self.last_message_time[appeal_id][user_id] = now
        return True
    
    async def connect_appeal_list(self, websocket: WebSocket):
        """Подключение для обновления списка обращений"""
        self.appeal_list_connections.append(websocket)

    def disconnect_appeal_list(self, websocket: WebSocket):
        """Отключение от обновления списка обращений"""
        if websocket in self.appeal_list_connections:
            self.appeal_list_connections.remove(websocket)

    async def connect_user_listener(self, user_id: str, websocket: WebSocket):
        """Подключение для пользовательских уведомлений"""
        if user_id not in self.user_specific_listeners:
            self.user_specific_listeners[user_id] = []
        self.user_specific_listeners[user_id].append(websocket)

    def disconnect_user_listener(self, user_id: str, websocket: WebSocket):
        """Отключение от пользовательских уведомлений"""
        if user_id in self.user_specific_listeners:
            if websocket in self.user_specific_listeners[user_id]:
                self.user_specific_listeners[user_id].remove(websocket)
            if not self.user_specific_listeners[user_id]:
                del self.user_specific_listeners[user_id]

    async def broadcast_appeal_update(self, message: dict):
        """Широковещательная рассылка обновлений списка обращений"""
        disconnected = []
        for connection in self.appeal_list_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        for connection in disconnected:
            self.disconnect_appeal_list(connection)

    async def send_user_notification(self, user_id: str, message: dict):
        """Отправка уведомления конкретному пользователю"""
        if user_id in self.user_specific_listeners:
            disconnected = []
            for connection in self.user_specific_listeners[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)
            
            for connection in disconnected:
                self.disconnect_user_listener(user_id, connection)
    
    async def notify_moderator_assignment(self, appeal_id: str, moderator_id: str, assigned_by_name: str):
        """Уведомление модератора о новом назначении"""
        notification = {
            "type": "moderator_assignment",
            "appeal_id": appeal_id,
            "assigned_by": assigned_by_name,
            "message": f"Вам назначено новое обращение пользователем {assigned_by_name}",
            "timestamp": datetime.now().isoformat()
        }

        await manager.send_user_notification(moderator_id, notification)

manager = ConnectionManager()

appeal_counters_cache = {
    "pending": 0,
    "user_assigned": 0,
    "last_updated": None
}