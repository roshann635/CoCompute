from fastapi import WebSocket
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Maps worker_uid to WebSocket object
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, worker_uid: str):
        await websocket.accept()
        self.active_connections[worker_uid] = websocket
        logger.info(f"Worker {worker_uid} connected via WebSocket")

    def disconnect(self, worker_uid: str):
        if worker_uid in self.active_connections:
            del self.active_connections[worker_uid]
            logger.info(f"Worker {worker_uid} disconnected")

    async def send_personal_message(self, message: dict, worker_uid: str):
        if worker_uid in self.active_connections:
            websocket = self.active_connections[worker_uid]
            await websocket.send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)

manager = ConnectionManager()
