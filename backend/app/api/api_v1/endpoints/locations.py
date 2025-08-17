from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db, get_current_claims, require_role
from app.models.location import Location
from app.schemas import location as schemas

router = APIRouter()

@router.post("/", response_model=schemas.Location)
def create_location(
    location: schemas.LocationCreate,
    db: Session = Depends(get_db),
    claims = Depends(require_role("admin"))
):
    data = location.dict()
    if not data.get("org_id"):
        data["org_id"] = claims.get("org")
    db_location = Location(**data)
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location

@router.get("/", response_model=List[schemas.Location])
def read_locations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), claims = Depends(get_current_claims)):
    locations = db.query(Location).filter(Location.org_id == claims.get("org")).offset(skip).limit(limit).all()
    return locations

@router.get("/{location_id}", response_model=schemas.Location)
def read_location(location_id: str, db: Session = Depends(get_db), claims = Depends(get_current_claims)):
    org_id = claims.get("org")
    location = db.query(Location).filter(Location.id == location_id, Location.org_id == org_id).first()
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return location

@router.get("/organization/{org_id}", response_model=List[schemas.Location])
def read_locations_by_org(org_id: str, db: Session = Depends(get_db), claims = Depends(get_current_claims)):
    token_org = claims.get("org")
    locations = db.query(Location).filter(Location.org_id == token_org).all()
    return locations