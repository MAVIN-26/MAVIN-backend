from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from jose import JWTError
from sqlalchemy import select

from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.models.user import TokenBlacklist, User
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


async def _authenticate(token: str) -> User | None:
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None

    async with AsyncSessionLocal() as db:
        blacklisted = await db.scalar(
            select(TokenBlacklist).where(TokenBlacklist.token == token)
        )
        if blacklisted:
            return None
        user = await db.get(User, user_id)
        if user is None or user.is_blocked:
            return None
        return user


@router.websocket("/ws/orders")
async def orders_ws(websocket: WebSocket):
    token = _extract_token(websocket)
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user = await _authenticate(token)
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    subprotocol = None
    raw = websocket.headers.get("sec-websocket-protocol")
    if raw:
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        subprotocol = parts[0] if parts else None

    await websocket.accept(subprotocol=subprotocol)
    await manager.connect(user.id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(user.id, websocket)
