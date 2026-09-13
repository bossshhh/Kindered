from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.db.database import init_db
from app.api.routes import router

init_db()

app = FastAPI(
    title="Behavioral Digital Twin",
    description="MVP API for an elderly-focused behavioral digital twin companion.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/app", StaticFiles(directory=frontend_dist, html=True), name="frontend")


@app.get("/")
def root():
    return {
        "name": "Behavioral Digital Twin",
        "status": "running",
        "docs": "/docs",
        "frontend": "/app",
    }
