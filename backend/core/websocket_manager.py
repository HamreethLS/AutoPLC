"""
WebSocket manager for real-time communication
"""

import asyncio
import json
from typing import Dict, Set
from fastapi import WebSocket
from datetime import datetime

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.task_subscribers: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        print(f"🔌 WebSocket connected: {client_id}")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            print(f"🔌 WebSocket disconnected: {client_id}")
        
        # Remove from task subscriptions
        for task_id, subscribers in self.task_subscribers.items():
            subscribers.discard(client_id)
    
    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
            except Exception as e:
                print(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast(self, task_id: str, message: dict):
        """Broadcast message to all clients subscribed to a task"""
        message_with_metadata = {
            **message,
            "task_id": task_id,
            "timestamp": datetime.now().isoformat()
        }
        
        # Mitigate race condition: Wait up to 2 seconds for a client to subscribe.
        # This is crucial because the background task might start broadcasting
        # before the frontend has received the task_id and sent its subscription message.
        for _ in range(10):
            if self.task_subscribers.get(task_id):
                break
            await asyncio.sleep(0.2)

        subscribers = self.task_subscribers.get(task_id, set())
        if not subscribers:
            print(f"⚠️ Broadcast for task {task_id} skipped: No subscribers after waiting.")
            return

        disconnected_clients = []
        # Create a copy of the set to iterate over, as it might be modified
        for client_id in list(subscribers):
            websocket = self.active_connections.get(client_id)
            if websocket:
                try:
                    await websocket.send_text(json.dumps(message_with_metadata))
                except Exception as e:
                    print(f"Error broadcasting to {client_id}: {e}")
                    disconnected_clients.append(client_id)
            else:
                # Client is in subscriber list but not in active connections, needs cleanup
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    async def subscribe_to_task(self, client_id: str, task_id: str):
        """Subscribe client to task updates"""
        if task_id not in self.task_subscribers:
            self.task_subscribers[task_id] = set()
        self.task_subscribers[task_id].add(client_id)
    
    def get_stats(self) -> dict:
        return {
            "active_connections": len(self.active_connections),
            "task_subscriptions": len(self.task_subscribers),
            "total_subscribers": sum(len(subs) for subs in self.task_subscribers.values())
        }
