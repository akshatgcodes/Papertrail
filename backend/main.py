# Lets `uvicorn main:app` work from backend/ (some hosts expect it)
from app.main import app  # noqa: F401
