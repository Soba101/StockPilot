from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db, get_current_claims, require_role
from app.models.product import Product
from app.schemas import product as schemas

router = APIRouter()

@router.post("/", response_model=schemas.Product)
def create_product(
    product: schemas.ProductCreate,
    db: Session = Depends(get_db),
    claims = Depends(require_role("admin")),
):
    # enforce org from token if not provided
    data = product.dict()
    if not data.get("org_id"):
        data["org_id"] = claims.get("org")
    db_product = Product(**data)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.get("/", response_model=List[schemas.Product])
def read_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), claims = Depends(get_current_claims)):
    products = db.query(Product).filter(Product.org_id == claims.get("org")).offset(skip).limit(limit).all()
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

@router.post("/bulk_upsert", response_model=List[schemas.Product])
def bulk_upsert_products(
    items: List[schemas.ProductCreate],
    db: Session = Depends(get_db),
    claims = Depends(require_role("admin")),
):
    token_org = claims.get("org")
    created_or_updated: List[Product] = []
    for item in items:
        data = item.dict()
        data["org_id"] = token_org
        existing = (
            db.query(Product)
            .filter(Product.org_id == token_org, Product.sku == data["sku"]).first()
        )
        if existing:
            for k, v in data.items():
                if k != "id" and v is not None:
                    setattr(existing, k, v)
            created_or_updated.append(existing)
        else:
            obj = Product(**data)
            db.add(obj)
            created_or_updated.append(obj)
    db.commit()
    for obj in created_or_updated:
        db.refresh(obj)
    return created_or_updated

@router.get("/organization/{org_id}", response_model=List[schemas.Product])
def read_products_by_org(org_id: str, db: Session = Depends(get_db), claims = Depends(get_current_claims)):
    # ignore path org_id; enforce from token for safety
    token_org = claims.get("org")
    products = db.query(Product).filter(Product.org_id == token_org).all()
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