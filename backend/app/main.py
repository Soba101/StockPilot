from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.api_v1.api import api_router

# Import models to ensure they are registered with SQLAlchemy
from app.models.organization import Organization
from app.models.location import Location
from app.models.product import Product
from app.models.inventory import InventoryMovement
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.supplier import Supplier
from app.models.user import User
from app.models.order import Order, OrderItem
from app.core.database import Base, engine
import os

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

# Auto-create tables in non-Postgres environments (tests use SQLite)
db_url = os.getenv("DATABASE_URL", settings.DATABASE_URL)
if db_url.startswith("sqlite"):
    Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {"message": "StockPilot API", "version": "1.0.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}