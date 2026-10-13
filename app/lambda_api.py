"""AWS Lambda entry point for the HTTP API (API Gateway -> Lambda -> FastAPI)."""
from mangum import Mangum

from app.main import app

handler = Mangum(app, lifespan="off")
