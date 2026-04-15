from app.models.user import TokenBlacklist
from app.repositories.base import BaseRepository


class TokenBlacklistRepository(BaseRepository[TokenBlacklist]):
    model = TokenBlacklist

    def add_token(self, token: str, user_id: int) -> TokenBlacklist:
        entry = TokenBlacklist(token=token, user_id=user_id)
        self.db.add(entry)
        return entry
