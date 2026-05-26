from fastapi import APIRouter, WebSocket, WebSocketDisconnect, FastAPI, status
import structlog
from app.edge.socket.connection_manager import manager
from app.edge.socket.socket_handler import handler
from app.utils.security_util import decode_token

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["WebSocket"])

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, token: str = None):
    """
    Main WebSocket entry point with JWT authentication
    """
    # 1. Authenticate user
    if not token:
        # Check query params if not in header/as argument (FastAPI handles token=... in query)
        token = websocket.query_params.get("token")
        
    user_id = "anonymous"
    if token:
        payload = decode_token(token)
        if payload:
            user_id = payload.get("sub", "anonymous")
        else:
            logger.warning(f"Invalid token for WebSocket connection: {client_id}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    # 2. Connect
    await manager.connect(websocket, client_id, user_id)
    
    try:
        while True:
            # Wait for any incoming json messages
            data = await websocket.receive_json()
            await handler.handle_message(client_id, data, user_id)
            
    except WebSocketDisconnect:
        manager.disconnect(client_id, user_id)
    except Exception as e:
        logger.error(f"Error in WebSocket loop for {client_id}: {e}")
        manager.disconnect(client_id, user_id)

def register_socket_routes(app: FastAPI):
    """Register socket routes to the main app"""
    app.include_router(router)
