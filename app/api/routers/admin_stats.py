from fastapi import APIRouter, Depends

from app.api.deps import require_role
from app.schemas.admin_stats import AdminStats
from app.services.admin_stats import AdminStatsService, get_admin_stats_service

admin_router = APIRouter(
    prefix="/admin",
    tags=["admin-stats"],
    dependencies=[Depends(require_role("site_admin"))],
)


@admin_router.get("/stats", response_model=AdminStats)
async def admin_get_stats(
    service: AdminStatsService = Depends(get_admin_stats_service),
):
    return await service.get_stats()
