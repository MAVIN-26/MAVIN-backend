from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status

from app.services.websocket_auth import WebSocketAuthService, get_websocket_auth_service
from app.services.ws_manager import manager

router = APIRouter(tags=["websocket"])


def _extract_token(websocket: WebSocket) -> str | None:
    raw = websocket.headers.get("sec-websocket-protocol")
    if not raw:
        return None
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    if len(parts) == 1:
        return parts[0]
    return None


def _pick_subprotocol(websocket: WebSocket) -> str | None:
    raw = websocket.headers.get("sec-websocket-protocol")
    if not raw:
        return None
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return parts[0] if parts else None


@router.websocket("/ws/orders")
async def orders_ws(
    websocket: WebSocket,
    auth: WebSocketAuthService = Depends(get_websocket_auth_service),
):
    token = _extract_token(websocket)
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user = await auth.authenticate(token)
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept(subprotocol=_pick_subprotocol(websocket))
    await manager.connect(user.id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(user.id, websocket)
