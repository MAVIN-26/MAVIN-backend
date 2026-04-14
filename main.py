from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routers import allergens, auth, categories, upload
from app.services.storage import ensure_bucket


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_bucket()
    yield


app = FastAPI(
    title="MAVIN API",
    version="1.0.0",
    root_path="/api/v1",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(allergens.public_router)
app.include_router(allergens.admin_router)
app.include_router(categories.public_router)
app.include_router(categories.admin_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
