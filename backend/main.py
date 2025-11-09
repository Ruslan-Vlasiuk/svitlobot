from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import uvicorn

from config import settings
from database import init_db, close_db
from redis_client import redis_client

# Налаштування логування
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting СвітлоБот API...")
    await init_db()
    await redis_client.connect()
    logger.info("✅ Application started successfully")

    yield

    # Shutdown
    logger.info("🛑 Shutting down...")
    await redis_client.close()
    await close_db()
    logger.info("✅ Application stopped")


# FastAPI app
app = FastAPI(
    title="СвітлоБот API",
    description="Backend для Telegram-бота моніторингу електропостачання",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "СвітлоБот API v1.0",
        "status": "running",
        "environment": settings.ENVIRONMENT
    }


# Health check
@app.get("/health")
async def health():
    return {"status": "healthy"}


# Підключити роутери
from api import users, queues, addresses, notifications, iot

app.include_router(users.router)
app.include_router(queues.router)
app.include_router(addresses.router)
app.include_router(notifications.router)
app.include_router(iot.router)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )