from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.api_v1.api import api_router

# Import models to ensure they are registered with SQLAlchemy
from app.models.organization import Organization
from app.models.location import Location
from app.models.product import Product
from app.models.inventory import InventoryMovement

app = FastAPI(
    title="StockPilot API",
    description="Inventory + sales analytics with a trustworthy chat interface",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

if settings.ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    return {"message": "StockPilot API", "version": "1.0.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}