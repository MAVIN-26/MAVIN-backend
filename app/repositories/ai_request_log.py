from app.models.ai_request_log import AIRequestLog
from app.repositories.base import BaseRepository


class AIRequestLogRepository(BaseRepository[AIRequestLog]):
    model = AIRequestLog

    def log(
        self,
        user_id: int,
        restaurant_id: int,
        prompt: str,
        response: str,
        recommended_dish_ids: list[int],
    ) -> AIRequestLog:
        entry = AIRequestLog(
            user_id=user_id,
            restaurant_id=restaurant_id,
            prompt=prompt,
            response=response,
            recommended_dish_ids=recommended_dish_ids,
        )
        self.db.add(entry)
        return entry
