from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import api_router, public_router
from app.core.config import settings
from app.services.storage import storage_service


@asynccontextmanager
async def lifespan(_: FastAPI):
    storage_service.ensure_bucket()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(api_router, prefix=settings.api_v1_prefix)
app.include_router(public_router)
