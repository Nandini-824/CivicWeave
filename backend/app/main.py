from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import (
    connect_to_mongodb,
    close_mongodb_connection,
    create_indexes,
)
from app.routers import (
    auth,
    complaints,
    ai,
    incidents,
    officer,
    admin,
    notifications,
)


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongodb()
    await create_indexes()

    yield

    # Shutdown
    await close_mongodb_connection()


app = FastAPI(
    title="CivicWeave API",
    description="AI-Based Civic Grievance Intelligence System",
    version="1.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router)
app.include_router(complaints.router)
app.include_router(ai.router)
app.include_router(incidents.router)
app.include_router(officer.router)
app.include_router(admin.router)
app.include_router(notifications.router)


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "service": "CivicWeave API",
        "database": "MongoDB",
    }