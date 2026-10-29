import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import update

from app import auth
from app.config import settings
from app.db import Base, SessionLocal, engine
from app.models import Document
from app.routers import ask, documents

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    # Small schema, so create_all on startup instead of a migration tool
    Base.metadata.create_all(engine)
    # Indexing runs in-process; anything still "processing" was cut off by a restart
    with SessionLocal() as db:
        db.execute(
            update(Document)
            .where(Document.status == "processing")
            .values(status="failed", error="Interrupted by a server restart. Re-index it.")
        )
        db.commit()
    yield


app = FastAPI(title="Papertrail API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(ask.router)


@app.get("/health")
def health() -> dict:
    return {"ok": True}
