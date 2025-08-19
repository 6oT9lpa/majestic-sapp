import datetime
from fastapi import  WebSocket
from typing import Dict, List
from datetime import datetime, timedelta

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.last_message_time: Dict[str, Dict[str, datetime]] = {}
        self.appeal_list_listeners: List[WebSocket] = []
        self.user_appeal_listeners: Dict[str, List[WebSocket]] = {}

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
    
    async def connect_appeal_list_listener(self, websocket: WebSocket):
        """Добавляем websocket для прослушивания обновлений списка обращений"""
        self.appeal_list_listeners.append(websocket)

    def disconnect_appeal_list_listener(self, websocket: WebSocket):
        """Удаляем websocket из слушателей списка обращений"""
        if websocket in self.appeal_list_listeners:
            self.appeal_list_listeners.remove(websocket)

    async def connect_user_appeal_listener(self, user_id: str, websocket: WebSocket):
        """Добавляем websocket для прослушивания обновлений списка обращений пользователя"""
        if user_id not in self.user_appeal_listeners:
            self.user_appeal_listeners[user_id] = []
        self.user_appeal_listeners[user_id].append(websocket)

    def disconnect_user_appeal_listener(self, user_id: str, websocket: WebSocket):
        """Удаляем websocket из слушателей списка обращений пользователя"""
        if user_id in self.user_appeal_listeners and websocket in self.user_appeal_listeners[user_id]:
            self.user_appeal_listeners[user_id].remove(websocket)

    async def broadcast_appeal_update(self, appeal_data: dict):
        """Отправляем обновление обращения всем слушателям"""
        message = {
            "type": "appeal_update",
            "data": appeal_data
        }
        
        for listener in self.appeal_list_listeners:
            try:
                await listener.send_json(message)
            except:
                self.disconnect_appeal_list_listener(listener)
        
        if appeal_data.get("user_id") and appeal_data["user_id"] in self.user_appeal_listeners:
            for listener in self.user_appeal_listeners[appeal_data["user_id"]]:
                try:
                    await listener.send_json(message)
                except:
                    self.disconnect_user_appeal_listener(appeal_data["user_id"], listener)

    async def broadcast_appeal_created(self, appeal_data: dict):
        """Отправляем уведомление о новом обращении"""
        message = {
            "type": "appeal_created",
            "data": appeal_data
        }
        
        for listener in self.appeal_list_listeners:
            try:
                await listener.send_json(message)
            except:
                self.disconnect_appeal_list_listener(listener)
    
manager = ConnectionManager()