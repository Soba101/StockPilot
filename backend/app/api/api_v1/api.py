from fastapi import APIRouter
from app.api.api_v1.endpoints import products, locations, organizations

api_router = APIRouter()
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(locations.router, prefix="/locations", tags=["locations"])
api_router.include_router(products.router, prefix="/products", tags=["products"])