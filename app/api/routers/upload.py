from fastapi import APIRouter, Depends, UploadFile, status

from app.api.deps import require_role
from app.services.upload import UploadService, get_upload_service

router = APIRouter(tags=["upload"])


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload(
    file: UploadFile,
    _: object = Depends(require_role("restaurant_admin", "site_admin")),
    service: UploadService = Depends(get_upload_service),
):
    url = await service.upload(file)
    return {"url": url}
