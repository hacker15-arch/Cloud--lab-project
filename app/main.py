import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.auth import init_auth_db, router as auth_router
from app.api.health import router as health_router
from app.api.nodes import router as nodes_router
from app.api.objects import router as objects_router
from app.config import settings
from app.core.metadata import metadata_manager
from app.storage.storage_manager import storage_manager

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("vault")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: ensure storage nodes and metadata database exist on startup."""
    logger.info("Starting %s v%s", settings.PROJECT_NAME, settings.VERSION)
    storage_manager.initialize_all()
    metadata_manager.initialize()
    init_auth_db()
    logger.info(
        "Initialized %d storage node(s), SQLite metadata catalog at %s, and user auth database at %s",
        len(storage_manager.list_nodes()),
        settings.metadata_db_path,
        settings.BASE_STORAGE_PATH / "users.db",
    )
    yield
    logger.info("Shutting down Vault server.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Fault-tolerant distributed object storage system.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health_router)
app.include_router(nodes_router)
app.include_router(auth_router)
app.include_router(objects_router)
app.include_router(admin_router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "nodes_count": len(settings.STORAGE_NODES),
        "default_replication_factor": settings.DEFAULT_REPLICATION_FACTOR,
        "docs_url": "/docs",
        "health_url": "/health",
        "nodes_url": "/nodes",
    }
