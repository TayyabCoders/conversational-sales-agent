from typing import Dict, List
from fastapi import WebSocket
import structlog

logger = structlog.get_logger(__name__)

import json
import asyncio

class ConnectionManager:
    """Manages active WebSocket connections with rooms, identity, and scaling"""
    
    def __init__(self):
        # Map client_id to WebSocket connection
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Map user_id to set of client_ids
        self.user_connections: Dict[str, List[str]] = {}
        
        # Map room_id to set of client_ids
        self.rooms: Dict[str, List[str]] = {}
        
        # Injected dependencies
        self.prometheus = None
        self.redis = None
        self._pubsub_task = None

    async def start(self):
        """Start background tasks"""
        if self.redis and not self._pubsub_task:
            self._pubsub_task = asyncio.create_task(self._listen_to_redis())
            logger.info("Background task for Redis Pub/Sub started")

    async def stop(self):
        """Stop background tasks"""
        if self._pubsub_task:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass
            self._pubsub_task = None
            logger.info("Background task for Redis Pub/Sub stopped")

    def set_dependencies(self, prometheus=None, redis=None):
        self.prometheus = prometheus
        self.redis = redis

    async def _listen_to_redis(self):
        """Listen to Redis for cross-instance messages"""
        pubsub = self.redis.client.pubsub()
        pubsub.subscribe("ws_broadcast", "ws_user", "ws_room")
        
        logger.info("Started listening to Redis Pub/Sub for WebSockets")
        
        while True:
            try:
                # Since redis-py's pubsub is blocking, we use a loop or thread
                # But here we'll use the non-blocking get_message if possible
                # or better, assume the user might switch to redis.asyncio
                message = pubsub.get_message(ignore_subscribe_messages=True)
                if message:
                    channel = message['channel']
                    data = json.loads(message['data'])
                    
                    if channel == "ws_broadcast":
                        await self._local_broadcast(data)
                    elif channel == "ws_user":
                        await self._local_send_to_user(data.get("user_id"), data.get("message"))
                    elif channel == "ws_room":
                        await self._local_send_to_room(data.get("room_id"), data.get("message"), data.get("exclude_client"))
                
                await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"Error in Redis Pub/Sub listener: {e}")
                await asyncio.sleep(1)

    async def connect(self, websocket: WebSocket, client_id: str, user_id: str):
        """Accept connection and track by client_id and user_id"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(client_id)
        
        if self.prometheus:
            self.prometheus.active_connections.inc()
            
        logger.info(f"WebSocket connected: {client_id} (User: {user_id}, Total: {len(self.active_connections)})")

    def disconnect(self, client_id: str, user_id: str):
        """Remove connection and cleanup rooms"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            
        if user_id in self.user_connections:
            if client_id in self.user_connections[user_id]:
                self.user_connections[user_id].remove(client_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Cleanup rooms
        for room_clients in self.rooms.values():
            if client_id in room_clients:
                room_clients.remove(client_id)
        
        if self.prometheus:
            self.prometheus.active_connections.dec()
            
        logger.info(f"WebSocket disconnected: {client_id} (User: {user_id}, Total: {len(self.active_connections)})")

    async def join_room(self, client_id: str, room_id: str):
        """User joins a specific room (local instance only)"""
        if room_id not in self.rooms:
            self.rooms[room_id] = []
        if client_id not in self.rooms[room_id]:
            self.rooms[room_id].append(client_id)
            logger.info(f"Client {client_id} joined room {room_id}")

    async def leave_room(self, client_id: str, room_id: str):
        """User leaves a specific room (local instance only)"""
        if room_id in self.rooms and client_id in self.rooms[room_id]:
            self.rooms[room_id].remove(client_id)
            logger.info(f"Client {client_id} left room {room_id}")

    async def send_personal_message(self, message: dict, client_id: str):
        """Send message to a specific connection (local instance only)"""
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)

    async def send_to_user(self, message: dict, user_id: str):
        """Send message to all connections of a specific user (Cross-instance)"""
        if self.redis:
            self.redis.client.publish("ws_user", json.dumps({"user_id": user_id, "message": message}))
        else:
            await self._local_send_to_user(user_id, message)

    async def _local_send_to_user(self, user_id: str, message: dict):
        if user_id in self.user_connections:
            for client_id in self.user_connections[user_id]:
                await self.send_personal_message(message, client_id)

    async def send_to_room(self, message: dict, room_id: str, exclude_client: str = None):
        """Broadcast message to all users in a room (Cross-instance)"""
        if self.redis:
            self.redis.client.publish("ws_room", json.dumps({
                "room_id": room_id, 
                "message": message, 
                "exclude_client": exclude_client
            }))
        else:
            await self._local_send_to_room(room_id, message, exclude_client)

    async def _local_send_to_room(self, room_id: str, message: dict, exclude_client: str = None):
        if room_id in self.rooms:
            for client_id in self.rooms[room_id]:
                if client_id != exclude_client:
                    await self.send_personal_message(message, client_id)

    async def broadcast(self, message: dict):
        """Send message to all connected users (Cross-instance)"""
        if self.redis:
            self.redis.client.publish("ws_broadcast", json.dumps(message))
        else:
            await self._local_broadcast(message)

    async def _local_broadcast(self, message: dict):
        for connection in self.active_connections.values():
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Failed to local broadcast: {e}")

# Global instance for easy access
manager = ConnectionManager()
