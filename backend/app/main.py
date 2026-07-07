from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routers.analytics import router as analytics_router
from .api.routers.health import router as health_router
from .api.routers.scoreboards import router as scoreboards_router
from .core.config import settings
from .db.bootstrap import bootstrap_database

bootstrap_database()

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(scoreboards_router, prefix=settings.api_prefix)
app.include_router(analytics_router, prefix=settings.api_prefix)
