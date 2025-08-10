from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.product import Product
from app.schemas import product as schemas

router = APIRouter()

@router.post("/", response_model=schemas.Product)
def create_product(
    product: schemas.ProductCreate,
    db: Session = Depends(get_db)
):
    db_product = Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.get("/", response_model=List[schemas.Product])
def read_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    products = db.query(Product).offset(skip).limit(limit).all()
    return products

@router.get("/{product_id}", response_model=schemas.Product)
def read_product(product_id: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.put("/{product_id}", response_model=schemas.Product)
def update_product(
    product_id: str,
    product: schemas.ProductUpdate,
    db: Session = Depends(get_db),
):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)

    db.commit()
    db.refresh(db_product)
    return db_product

@router.get("/organization/{org_id}", response_model=List[schemas.Product])
def read_products_by_org(org_id: str, db: Session = Depends(get_db)):
    products = db.query(Product).filter(Product.org_id == org_id).all()
    return products

@router.get("/sku/{org_id}/{sku}", response_model=schemas.Product)
def read_product_by_sku(org_id: str, sku: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(
        Product.org_id == org_id,
        Product.sku == sku
    ).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product