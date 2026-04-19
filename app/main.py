"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.core.database import AsyncSessionLocal
from app.core.logging import RequestIdMiddleware, configure_logging
from app.domain.auth.router import router as auth_router
from app.domain.meeting.router import router as meeting_router
from app.domain.regions.router import router as regions_router
from app.domain.regions.seed import seed_regions
from app.domain.user.router import router as user_router

settings = get_settings()
configure_logging(level=settings.LOG_LEVEL, json_format=settings.LOG_JSON)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.

    Schema creation is owned by Alembic (`alembic upgrade head`), not the
    app. The only optional startup task is region seeding, guarded by
    `RUN_STARTUP_SEED`; prod should run it as a dedicated Job.
    """
    if settings.RUN_STARTUP_SEED:
        async with AsyncSessionLocal() as session:
            await seed_regions(session)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    lifespan=lifespan,
)

app.add_middleware(RequestIdMiddleware)

if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

app.include_router(auth_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
app.include_router(regions_router, prefix="/api/v1")
app.include_router(meeting_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Hello, 각할모 World"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "gakhalmo-api"}
