from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.db.session import init_db
from app.services.graph import load_graph_from_db
from app.db.session import AsyncSessionLocal
from app.api import perks, builds, survivors, shrine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database...")
    await init_db()

    logger.info("Loading perk graph into memory...")
    try:
        async with AsyncSessionLocal() as db:
            await load_graph_from_db(db)
    except Exception as e:
        logger.warning(f"Graph load failed on startup (will retry after sync): {e}")

    yield

    # Shutdown
    logger.info("Shutting down...")


app = FastAPI(
    title="DBD Survivor Build Creator",
    description="Generate optimized Dead by Daylight survivor builds using perk co-occurrence graphs and AI explanations.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(perks.router)
app.include_router(builds.router)
app.include_router(survivors.router)
app.include_router(shrine.router)


@app.get("/health")
async def health():
    return {"status": "ok", "ai_enabled": settings.use_real_ai}
