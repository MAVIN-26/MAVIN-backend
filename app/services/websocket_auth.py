from jose import JWTError

from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.repositories.token_blacklist import TokenBlacklistRepository
from app.repositories.user import UserRepository


class WebSocketAuthService:
    async def authenticate(self, token: str) -> User | None:
        try:
            payload = decode_token(token)
            user_id = int(payload["sub"])
        except (JWTError, KeyError, ValueError):
            return None

        async with AsyncSessionLocal() as db:
            blacklist = TokenBlacklistRepository(db)
            if await blacklist.is_blacklisted(token):
                return None

            users = UserRepository(db)
            user = await users.get_by_id(user_id)
            if user is None or user.is_blocked:
                return None
            return user


def get_websocket_auth_service() -> WebSocketAuthService:
    return WebSocketAuthService()
