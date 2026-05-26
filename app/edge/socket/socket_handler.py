from typing import Any, Dict
import structlog
from app.edge.socket.connection_manager import manager
from app.schemas.socket_schema import SocketEvent, SocketResponse

logger = structlog.get_logger(__name__)

class SocketHandler:
    """Handles incoming WebSocket message logic with validation"""
    
    async def handle_message(self, client_id: str, data: Dict[str, Any], user_id: str):
        """
        Process incoming message based on type
        """
        try:
            # Validate incoming data
            event = SocketEvent(**data)
            msg_type = event.type
            payload = event.payload
            
            logger.info(f"Handling '{msg_type}' message from {user_id} ({client_id})")
            
            if msg_type == "ping":
                await manager.send_personal_message({"type": "pong"}, client_id)
                
            elif msg_type == "subscribe":
                room_id = payload.get("room_id")
                if room_id:
                    await manager.join_room(client_id, room_id)
                    await manager.send_personal_message(
                        SocketResponse(type="subscribed", data={"room_id": room_id}).model_dump(),
                        client_id
                    )
                    
            elif msg_type == "unsubscribe":
                room_id = payload.get("room_id")
                if room_id:
                    await manager.leave_room(client_id, room_id)
                    await manager.send_personal_message(
                        SocketResponse(type="unsubscribed", data={"room_id": room_id}).model_dump(),
                        client_id
                    )
                    
            elif msg_type == "room_message":
                room_id = payload.get("room_id")
                content = payload.get("content")
                if room_id:
                    await manager.send_to_room({
                        "type": "room_notification",
                        "from": user_id,
                        "room_id": room_id,
                        "content": content
                    }, room_id, exclude_client=client_id)
                    
            elif msg_type == "broadcast":
                content = payload.get("content", "")
                await manager.broadcast({
                    "type": "notification",
                    "from": user_id,
                    "content": content
                })
            
            else:
                logger.warning(f"Unknown message type received: {msg_type}")
                await manager.send_personal_message(
                    SocketResponse(type="error", data={}, status="error", message="Unknown message type").model_dump(),
                    client_id
                )

        except Exception as e:
            logger.error(f"Error handling socket message: {e}")
            await manager.send_personal_message(
                SocketResponse(type="error", data={}, status="error", message=str(e)).model_dump(),
                client_id
            )

# Global instance
handler = SocketHandler()
