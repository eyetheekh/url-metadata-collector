import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core import settings
from .db.database import init_db, close_client
from .db.indexes import create_indexes
from .api.v1.endpoints import metadata
from .workers import bind_worker


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def db_lifespan(app: FastAPI):
    # startup
    await init_db(app, settings)
    logger.info("Database client initialized.")

    await create_indexes(app, settings.MONGODB_METADATA_COLLECTION_NAME)
    logger.info("Database indexes created.")

    await bind_worker(app, settings)
    logger.info("Global Background worker binded.")

    yield

    # shutdown
    await close_client(app)
    logger.info("Database client closed.")


def create_application() -> FastAPI:
    """Application factory pattern."""

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="HTTP Metadata Collector Service API.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=db_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            str(origin).strip("/") for origin in settings.BACKEND_CORS_ORIGINS
        ]
        if settings.BACKEND_CORS_ORIGINS
        else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["health"])
    async def health_check():
        """Health check endpoint for monitoring."""
        return {
            "status": "healthy",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }

    @app.get("/", tags=["root"])
    async def root():
        """Root endpoint with API information."""
        return {
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "documentation": "/docs",
            "health": "/health",
        }

    app.include_router(metadata.router, prefix=settings.APP_VERSION_PREFIX)

    return app


app = create_application()
