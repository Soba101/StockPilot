from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

class LocationBase(BaseModel):
    name: str
    type: str  # 'warehouse', 'store', 'virtual'
    address: Optional[str] = None

class LocationCreate(LocationBase):
    org_id: uuid.UUID

class LocationUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    address: Optional[str] = None

class Location(LocationBase):
    id: uuid.UUID
    org_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True