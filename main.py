import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routers import (
    ai,
    allergens,
    auth,
    cart,
    categories,
    favorites,
    menu,
    menu_categories,
    orders,
    orders_owner,
    profile,
    promo,
    restaurants,
    subscriptions,
    upload,
    websocket,
)
from app.services.storage import ensure_bucket
from app.services.subscription_expiry import run_expiry_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_bucket()
    expiry_task = asyncio.create_task(run_expiry_loop())
    try:
        yield
    finally:
        expiry_task.cancel()
        try:
            await expiry_task
        except asyncio.CancelledError:
            pass


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
app.include_router(restaurants.public_router)
app.include_router(restaurants.owner_router)
app.include_router(restaurants.admin_router)
app.include_router(menu.public_router)
app.include_router(menu.owner_router)
app.include_router(menu_categories.public_router)
app.include_router(menu_categories.owner_router)
app.include_router(profile.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(orders_owner.router)
app.include_router(websocket.router)
app.include_router(promo.customer_router)
app.include_router(promo.admin_router)
app.include_router(subscriptions.public_router)
app.include_router(subscriptions.customer_router)
app.include_router(ai.router)
app.include_router(favorites.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
