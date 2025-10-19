"""MindBase FastAPI Application"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import health, conversations, embeddings

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(conversations.router)
app.include_router(embeddings.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MindBase API - AI Conversation Knowledge Management",
        "version": settings.API_VERSION,
        "docs": "/docs",
        "health": "/health"
    }
