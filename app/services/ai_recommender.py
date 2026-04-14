import json
import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 30.0
MAX_ATTEMPTS = 2


class AIServiceUnavailable(Exception):
    pass


@dataclass
class MenuItemContext:
    id: int
    name: str
    description: str | None
    price: float
    calories: int | None
    proteins: float | None
    fats: float | None
    carbs: float | None
    allergens: list[str]


@dataclass
class AIResult:
    ai_text: str
    recommended_dish_ids: list[int]


def _build_system_prompt(menu: list[MenuItemContext], user_allergens: list[str]) -> str:
    menu_lines = []
    for m in menu:
        parts = [f"id={m.id}", f"название={m.name}", f"цена={m.price}₽"]
        if m.calories is not None:
            parts.append(f"ккал={m.calories}")
        if m.proteins is not None:
            parts.append(f"Б={m.proteins}")
        if m.fats is not None:
            parts.append(f"Ж={m.fats}")
        if m.carbs is not None:
            parts.append(f"У={m.carbs}")
        if m.allergens:
            parts.append("аллергены=" + ",".join(m.allergens))
        if m.description:
            parts.append(f"описание={m.description}")
        menu_lines.append("- " + "; ".join(parts))
    menu_block = "\n".join(menu_lines) if menu_lines else "(меню пусто)"

    allergens_block = ", ".join(user_allergens) if user_allergens else "нет"

    return (
        "Ты — нутрициолог-ассистент MAVIN. Отвечай на русском.\n"
        f"Меню ресторана:\n{menu_block}\n\n"
        f"Аллергены пользователя: {allergens_block}.\n"
        "Рекомендуй блюда с учётом КБЖУ и аллергенов. "
        "Исключи блюда, содержащие аллергены пользователя.\n"
        "Ответь строго в JSON-формате: "
        '{"text": "краткий комментарий на русском", "dish_ids": [<id рекомендованных блюд>]}. '
        "Используй только id из меню выше. Никакого текста вне JSON."
    )


def _parse_llm_content(content: str) -> AIResult:
    try:
        data = json.loads(content)
        text = str(data.get("text", "")).strip()
        raw_ids = data.get("dish_ids", [])
        ids = [int(x) for x in raw_ids if isinstance(x, (int, str)) and str(x).lstrip("-").isdigit()]
    except (json.JSONDecodeError, ValueError, TypeError):
        text = content.strip()
        ids = []
    return AIResult(ai_text=text, recommended_dish_ids=ids)


async def recommend(
    user_prompt: str,
    menu: list[MenuItemContext],
    user_allergens: list[str],
) -> AIResult:
    if not settings.OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY is not configured")
        raise AIServiceUnavailable()

    system_prompt = _build_system_prompt(menu, user_allergens)
    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    url = f"{settings.OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"

    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code >= 500:
                raise httpx.HTTPStatusError("LLM 5xx", request=resp.request, response=resp)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return _parse_llm_content(content)
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            last_error = exc
            logger.warning("LLM attempt %d failed: %s", attempt, exc)

    logger.error("LLM unavailable after %d attempts: %s", MAX_ATTEMPTS, last_error)
    raise AIServiceUnavailable()
