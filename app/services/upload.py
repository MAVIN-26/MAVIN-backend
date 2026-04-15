import uuid

from fastapi import HTTPException, UploadFile, status

from app.services.storage import upload_file

MAX_SIZE = 5 * 1024 * 1024  # 5 MB


def _detect_format(data: bytes) -> tuple[str, str] | None:
    if data[:3] == b"\xff\xd8\xff":
        return "jpg", "image/jpeg"
    if data[:4] == b"\x89PNG":
        return "png", "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", "image/webp"
    return None


class UploadService:
    async def upload(self, file: UploadFile) -> str:
        data = await file.read()

        if len(data) > MAX_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds 5 MB",
            )

        fmt = _detect_format(data)
        if fmt is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file format",
            )

        ext, content_type = fmt
        filename = f"{uuid.uuid4()}.{ext}"

        return upload_file(data, filename, content_type)


def get_upload_service() -> UploadService:
    return UploadService()
