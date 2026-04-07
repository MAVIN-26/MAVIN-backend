import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.api.deps import require_role
from app.models.user import User
from app.services.storage import upload_file

router = APIRouter(tags=["upload"])

MAX_SIZE = 5 * 1024 * 1024  # 5 MB

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}

MAGIC_BYTES: dict[bytes, tuple[str, str]] = {
    b"\xff\xd8\xff": ("jpg", "image/jpeg"),
    b"\x89PNG": ("png", "image/png"),
    b"RIFF": ("webp", "image/webp"),  # RIFF????WEBP — checked below
}


def _detect_format(data: bytes) -> tuple[str, str] | None:
    if data[:3] == b"\xff\xd8\xff":
        return "jpg", "image/jpeg"
    if data[:4] == b"\x89PNG":
        return "png", "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", "image/webp"
    return None


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload(
    file: UploadFile,
    current_user: User = Depends(require_role("restaurant_admin", "site_admin")),
):
    data = await file.read()

    if len(data) > MAX_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File size exceeds 5 MB")

    fmt = _detect_format(data)
    if fmt is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file format")

    ext, content_type = fmt
    filename = f"{uuid.uuid4()}.{ext}"

    url = upload_file(data, filename, content_type)
    return {"url": url}
