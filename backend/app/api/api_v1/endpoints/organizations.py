from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.organization import Organization
from app.schemas import organization as schemas

router = APIRouter()

@router.post("/", response_model=schemas.Organization)
def create_organization(
    organization: schemas.OrganizationCreate,
    db: Session = Depends(get_db)
):
    db_org = Organization(**organization.dict())
    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    return db_org

@router.get("/", response_model=List[schemas.Organization])
def read_organizations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    organizations = db.query(Organization).offset(skip).limit(limit).all()
    return organizations

@router.get("/{organization_id}", response_model=schemas.Organization)
def read_organization(organization_id: str, db: Session = Depends(get_db)):
    organization = db.query(Organization).filter(Organization.id == organization_id).first()
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization

@router.put("/{organization_id}", response_model=schemas.Organization)
def update_organization(
    organization_id: str,
    organization: schemas.OrganizationUpdate,
    db: Session = Depends(get_db)
):
    db_org = db.query(Organization).filter(Organization.id == organization_id).first()
    if db_org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    update_data = organization.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_org, key, value)
    
    db.commit()
    db.refresh(db_org)
    return db_org