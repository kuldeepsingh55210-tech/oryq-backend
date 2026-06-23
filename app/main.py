import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import get_supabase_client
from app.api.scan import router as scan_router
from app.api.hooks import router as hooks_router

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for FastAPI application.
    Executes checks on startup and cleanup on shutdown.
    """
    logger.info("Initializing ORYQ backend application...")
    try:
        client = get_supabase_client()
        # Verify connection by running a simple query
        client.table("brands").select("id").limit(1).execute()
        logger.info("Successfully connected to Supabase database.")
    except Exception as e:
        logger.critical(f"Failed to connect to Supabase database on startup: {e}")
    yield
    logger.info("Shutting down ORYQ backend application...")

app = FastAPI(
    title="ORYQ API - AI Visibility Intelligence Platform",
    description="Backend service for tracking brand visibility across LLM providers",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configurations
allowed_origins_list = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins_list,
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"],
)

# Register routes
app.include_router(scan_router)
app.include_router(hooks_router)

@app.get("/health")
async def health_check():
    """
    Simple health check endpoint for monitoring systems.
    """
    return {
        "status": "healthy",
        "service": "oryq-backend"
    }

# DONE - main.py
