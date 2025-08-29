# Settings Backend Integration Fix Plan

## Overview

This document outlines the implementation plan to fix the backend integration issues discovered during comprehensive testing of the StockPilot settings page. The frontend settings interface is fully functional but lacks the corresponding backend API endpoints.

## Problem Analysis

### Root Cause
The settings page frontend is making API calls to endpoints that don't exist in the backend:

**Missing API Endpoints:**
- `GET /api/v1/settings/users` - Returns 404
- `GET /api/v1/settings/roles` - Returns 404  
- `GET /api/v1/settings/permissions` - Returns 404
- All CRUD operations for users, roles, and permissions

**Missing Backend Components:**
- No `settings.py` endpoint file
- No settings router registered in the API
- Incomplete user/role/permission data models

### Current State
- ✅ Frontend: Fully implemented with comprehensive UI
- ✅ User Model: Basic model exists
- ❌ Backend APIs: Missing all settings endpoints
- ❌ Role/Permission Models: Not implemented
- ❌ Database Schema: Incomplete for RBAC

## Implementation Plan

### Phase 1: Database Models & Schemas
**Priority: HIGH** | **Estimated Time: 4-6 hours**

#### 1.1 Create Role Model
**File:** `backend/app/models/role.py`

```python
from sqlalchemy import Column, String, DateTime, func, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from .base import BaseModel

class Role(Base, BaseModel):
    __tablename__ = "roles"
    
    # Inherits id, created_at, updated_at from BaseModel
    org_id = Column(BaseModel.UUIDType, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(64), nullable=False)
    description = Column(String(255))
    permissions = Column(JSON)  # Array of permission strings
    is_default = Column(Boolean, default=False)  # Default role for new users
    
    # Relationships
    organization = relationship("Organization", back_populates="roles")
    users = relationship("User", back_populates="role")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('org_id', 'name', name='unique_role_per_org'),
    )
```

#### 1.2 Create Permission Model
**File:** `backend/app/models/permission.py`

```python
from sqlalchemy import Column, String, DateTime, func
from app.core.database import Base
from .base import BaseModel

class Permission(Base, BaseModel):
    __tablename__ = "permissions"
    
    name = Column(String(64), nullable=False, unique=True)
    category = Column(String(32), nullable=False)  # inventory, analytics, users, etc.
    description = Column(String(255))
    risk_level = Column(String(16), default="low")  # low, medium, high
    
    # Pre-defined permissions - not org-specific
    __table_args__ = (
        Index('idx_permission_category', 'category'),
    )
```

#### 1.3 Update User Model
**File:** `backend/app/models/user.py`

```python
# Add to existing User model
role_id = Column(BaseModel.UUIDType, ForeignKey("roles.id"), nullable=True)
first_name = Column(String(50))
last_name = Column(String(50))
status = Column(String(16), default="active")  # active, inactive, pending, suspended
last_login = Column(DateTime(timezone=True))

# Relationships
role = relationship("Role", back_populates="users")
organization = relationship("Organization")

@property
def full_name(self):
    return f"{self.first_name} {self.last_name}".strip()
```

#### 1.4 Create Pydantic Schemas
**File:** `backend/app/schemas/user_schemas.py`

```python
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    role_id: Optional[str] = None
    status: Optional[str] = "active"

class UserCreate(UserBase):
    password: Optional[str] = None  # For direct creation
    send_invite: bool = True  # Send email invitation

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role_id: Optional[str] = None
    status: Optional[str] = None

class UserResponse(UserBase):
    id: str
    org_id: str
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    role: Optional['RoleResponse'] = None
    
    class Config:
        from_attributes = True

class UserInvite(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    role_id: str
```

**File:** `backend/app/schemas/role_schemas.py`

```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: List[str] = []

class RoleCreate(RoleBase):
    is_default: bool = False

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None

class RoleResponse(RoleBase):
    id: str
    org_id: str
    is_default: bool
    created_at: datetime
    updated_at: datetime
    user_count: Optional[int] = 0  # Computed field
    
    class Config:
        from_attributes = True
```

**File:** `backend/app/schemas/permission_schemas.py`

```python
from pydantic import BaseModel
from typing import Optional

class PermissionResponse(BaseModel):
    id: str
    name: str
    category: str
    description: Optional[str] = None
    risk_level: str
    
    class Config:
        from_attributes = True
```

### Phase 2: API Endpoints Implementation
**Priority: HIGH** | **Estimated Time: 8-12 hours**

#### 2.1 Create Settings Endpoints
**File:** `backend/app/api/api_v1/endpoints/settings.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_claims, require_role
from app.schemas.user_schemas import UserResponse, UserCreate, UserUpdate, UserInvite
from app.schemas.role_schemas import RoleResponse, RoleCreate, RoleUpdate
from app.schemas.permission_schemas import PermissionResponse
from app.services.user_service import UserService
from app.services.role_service import RoleService
from app.services.permission_service import PermissionService

router = APIRouter()

# User Management Endpoints
@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    claims = Depends(get_current_claims)
):
    """List users for the current organization with filtering."""
    user_service = UserService(db)
    return await user_service.list_users(
        org_id=claims['org'],
        skip=skip,
        limit=limit,
        status=status,
        role=role
    )

@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    claims = Depends(require_role("admin"))
):
    """Create a new user in the current organization."""
    user_service = UserService(db)
    return await user_service.create_user(
        org_id=claims['org'],
        user_data=user_data
    )

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    claims = Depends(get_current_claims)
):
    """Get a specific user by ID."""
    user_service = UserService(db)
    return await user_service.get_user(user_id, claims['org'])

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    claims = Depends(require_role("admin"))
):
    """Update a user's information."""
    user_service = UserService(db)
    return await user_service.update_user(
        user_id=user_id,
        org_id=claims['org'],
        user_data=user_data
    )

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    claims = Depends(require_role("admin"))
):
    """Delete a user."""
    user_service = UserService(db)
    await user_service.delete_user(user_id, claims['org'])
    return {"message": "User deleted successfully"}

@router.post("/users/bulk-status")
async def bulk_update_user_status(
    user_ids: List[str],
    status: str,
    db: Session = Depends(get_db),
    claims = Depends(require_role("admin"))
):
    """Update status for multiple users."""
    user_service = UserService(db)
    return await user_service.bulk_update_status(
        user_ids=user_ids,
        status=status,
        org_id=claims['org']
    )

@router.post("/users/invite")
async def invite_user(
    invite_data: UserInvite,
    db: Session = Depends(get_db),
    claims = Depends(require_role("admin"))
):
    """Send an invitation to join the organization."""
    user_service = UserService(db)
    return await user_service.invite_user(
        org_id=claims['org'],
        invite_data=invite_data
    )

# Role Management Endpoints
@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    db: Session = Depends(get_db),
    claims = Depends(get_current_claims)
):
    """List all roles for the current organization."""
    role_service = RoleService(db)
    return await role_service.list_roles(claims['org'])

@router.post("/roles", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    db: Session = Depends(get_db),
    claims = Depends(require_role("admin"))
):
    """Create a new role."""
    role_service = RoleService(db)
    return await role_service.create_role(
        org_id=claims['org'],
        role_data=role_data
    )

@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: str,
    db: Session = Depends(get_db),
    claims = Depends(get_current_claims)
):
    """Get a specific role by ID."""
    role_service = RoleService(db)
    return await role_service.get_role(role_id, claims['org'])

@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    role_data: RoleUpdate,
    db: Session = Depends(get_db),
    claims = Depends(require_role("admin"))
):
    """Update a role."""
    role_service = RoleService(db)
    return await role_service.update_role(
        role_id=role_id,
        org_id=claims['org'],
        role_data=role_data
    )

@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: str,
    db: Session = Depends(get_db),
    claims = Depends(require_role("admin"))
):
    """Delete a role."""
    role_service = RoleService(db)
    await role_service.delete_role(role_id, claims['org'])
    return {"message": "Role deleted successfully"}

# Permission Management Endpoints
@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    claims = Depends(get_current_claims)
):
    """List all available permissions, optionally filtered by category."""
    permission_service = PermissionService(db)
    return await permission_service.list_permissions(category=category)
```

#### 2.2 Register Settings Router
**File:** `backend/app/api/api_v1/api.py`

```python
# Add import
from app.api.api_v1.endpoints import settings

# Add router registration
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
```

### Phase 3: Database Migration
**Priority: HIGH** | **Estimated Time: 2-3 hours**

#### 3.1 Create Migration Script
**File:** `backend/migrations/w7_add_roles_permissions.sql`

```sql
-- Add roles table
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(64) NOT NULL,
    description VARCHAR(255),
    permissions JSONB DEFAULT '[]'::jsonb,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_role_per_org UNIQUE(org_id, name)
);

-- Add permissions table (global, not org-specific)
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(64) NOT NULL UNIQUE,
    category VARCHAR(32) NOT NULL,
    description VARCHAR(255),
    risk_level VARCHAR(16) DEFAULT 'low',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add columns to users table
ALTER TABLE users 
ADD COLUMN role_id UUID REFERENCES roles(id),
ADD COLUMN first_name VARCHAR(50),
ADD COLUMN last_name VARCHAR(50),
ADD COLUMN status VARCHAR(16) DEFAULT 'active',
ADD COLUMN last_login TIMESTAMP WITH TIME ZONE;

-- Create indexes
CREATE INDEX idx_roles_org_id ON roles(org_id);
CREATE INDEX idx_users_role_id ON users(role_id);
CREATE INDEX idx_permissions_category ON permissions(category);
CREATE INDEX idx_users_status ON users(status);

-- Insert default permissions
INSERT INTO permissions (name, category, description, risk_level) VALUES
-- Inventory permissions
('inventory.read', 'inventory', 'View inventory data and reports', 'low'),
('inventory.write', 'inventory', 'Modify inventory levels and settings', 'medium'),
('inventory.delete', 'inventory', 'Delete inventory records', 'high'),

-- Product permissions
('products.read', 'products', 'View product information', 'low'),
('products.write', 'products', 'Create and modify products', 'medium'),
('products.delete', 'products', 'Delete products', 'high'),

-- User management permissions
('users.read', 'users', 'View user accounts and roles', 'medium'),
('users.write', 'users', 'Create and modify user accounts', 'high'),
('users.delete', 'users', 'Delete user accounts', 'high'),

-- Analytics permissions
('analytics.read', 'analytics', 'View analytics and reports', 'low'),
('analytics.export', 'analytics', 'Export analytics data', 'medium'),

-- Purchasing permissions
('purchasing.read', 'purchasing', 'View purchase orders and suppliers', 'low'),
('purchasing.write', 'purchasing', 'Create and modify purchase orders', 'medium'),
('purchasing.approve', 'purchasing', 'Approve purchase orders', 'high'),

-- Settings permissions
('settings.read', 'settings', 'View system settings', 'medium'),
('settings.write', 'settings', 'Modify system settings', 'high'),

-- Organization permissions
('organization.read', 'organization', 'View organization details', 'low'),
('organization.write', 'organization', 'Modify organization settings', 'high');

-- Create default roles for each organization
INSERT INTO roles (org_id, name, description, permissions, is_default)
SELECT 
    o.id,
    'Administrator',
    'Full system access with all permissions',
    (SELECT jsonb_agg(p.name) FROM permissions p)::jsonb,
    true
FROM organizations o;

INSERT INTO roles (org_id, name, description, permissions, is_default)
SELECT 
    o.id,
    'Manager',
    'Management access with most permissions except user management',
    (SELECT jsonb_agg(p.name) FROM permissions p WHERE p.category != 'users')::jsonb,
    false
FROM organizations o;

INSERT INTO roles (org_id, name, description, permissions, is_default)
SELECT 
    o.id,
    'Viewer',
    'Read-only access to most data',
    (SELECT jsonb_agg(p.name) FROM permissions p WHERE p.name LIKE '%.read')::jsonb,
    false
FROM organizations o;

-- Update existing users to have the default admin role
UPDATE users 
SET role_id = (
    SELECT r.id 
    FROM roles r 
    WHERE r.org_id = users.org_id 
    AND r.name = 'Administrator' 
    AND r.is_default = true
    LIMIT 1
);

-- Add trigger to automatically assign default role to new users
CREATE OR REPLACE FUNCTION assign_default_role()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.role_id IS NULL THEN
        SELECT id INTO NEW.role_id
        FROM roles 
        WHERE org_id = NEW.org_id 
        AND is_default = true 
        LIMIT 1;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_assign_default_role
    BEFORE INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION assign_default_role();

-- Add updated_at trigger for roles
CREATE TRIGGER trigger_roles_updated_at
    BEFORE UPDATE ON roles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### Phase 4: Services & Business Logic
**Priority: MEDIUM** | **Estimated Time: 6-8 hours**

#### 4.1 User Service
**File:** `backend/app/services/user_service.py`

```python
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from app.models.user import User
from app.models.role import Role
from app.schemas.user_schemas import UserCreate, UserUpdate, UserInvite
from app.core.security import hash_password
from app.services.email_service import EmailService
import uuid

class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.email_service = EmailService()
    
    async def list_users(
        self, 
        org_id: str, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[str] = None,
        role: Optional[str] = None
    ) -> List[User]:
        """List users with filtering and pagination."""
        query = self.db.query(User).filter(User.org_id == org_id)
        
        if status:
            query = query.filter(User.status == status)
        
        if role:
            query = query.join(Role).filter(Role.name == role)
        
        return query.offset(skip).limit(limit).all()
    
    async def create_user(self, org_id: str, user_data: UserCreate) -> User:
        """Create a new user."""
        # Check if user already exists
        existing = self.db.query(User).filter(
            and_(User.email == user_data.email, User.org_id == org_id)
        ).first()
        
        if existing:
            raise HTTPException(400, "User with this email already exists")
        
        # Create user
        user = User(
            id=str(uuid.uuid4()),
            org_id=org_id,
            email=user_data.email,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role_id=user_data.role_id,
            status=user_data.status,
            password_hash=hash_password("temp_password") if not user_data.send_invite else None
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        # Send invitation email if requested
        if user_data.send_invite:
            await self.email_service.send_user_invitation(user)
        
        return user
    
    async def get_user(self, user_id: str, org_id: str) -> User:
        """Get user by ID with org validation."""
        user = self.db.query(User).filter(
            and_(User.id == user_id, User.org_id == org_id)
        ).first()
        
        if not user:
            raise HTTPException(404, "User not found")
        
        return user
    
    async def update_user(
        self, 
        user_id: str, 
        org_id: str, 
        user_data: UserUpdate
    ) -> User:
        """Update user information."""
        user = await self.get_user(user_id, org_id)
        
        for field, value in user_data.dict(exclude_unset=True).items():
            setattr(user, field, value)
        
        self.db.commit()
        self.db.refresh(user)
        return user
    
    async def delete_user(self, user_id: str, org_id: str):
        """Delete a user."""
        user = await self.get_user(user_id, org_id)
        self.db.delete(user)
        self.db.commit()
    
    async def bulk_update_status(
        self, 
        user_ids: List[str], 
        status: str, 
        org_id: str
    ):
        """Update status for multiple users."""
        self.db.query(User).filter(
            and_(User.id.in_(user_ids), User.org_id == org_id)
        ).update({"status": status}, synchronize_session=False)
        self.db.commit()
        
        return {"updated_count": len(user_ids)}
    
    async def invite_user(self, org_id: str, invite_data: UserInvite) -> dict:
        """Send invitation to new user."""
        # Create pending user
        user_data = UserCreate(
            email=invite_data.email,
            first_name=invite_data.first_name,
            last_name=invite_data.last_name,
            role_id=invite_data.role_id,
            status="pending",
            send_invite=True
        )
        
        user = await self.create_user(org_id, user_data)
        return {"message": "Invitation sent successfully", "user_id": user.id}
```

#### 4.2 Role Service
**File:** `backend/app/services/role_service.py`

```python
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List
from app.models.role import Role
from app.models.user import User
from app.schemas.role_schemas import RoleCreate, RoleUpdate
from fastapi import HTTPException
import uuid

class RoleService:
    def __init__(self, db: Session):
        self.db = db
    
    async def list_roles(self, org_id: str) -> List[Role]:
        """List all roles for organization with user counts."""
        return self.db.query(Role).filter(Role.org_id == org_id).all()
    
    async def create_role(self, org_id: str, role_data: RoleCreate) -> Role:
        """Create a new role."""
        # Check if role name already exists in org
        existing = self.db.query(Role).filter(
            and_(Role.org_id == org_id, Role.name == role_data.name)
        ).first()
        
        if existing:
            raise HTTPException(400, "Role with this name already exists")
        
        role = Role(
            id=str(uuid.uuid4()),
            org_id=org_id,
            name=role_data.name,
            description=role_data.description,
            permissions=role_data.permissions,
            is_default=role_data.is_default
        )
        
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role
    
    async def get_role(self, role_id: str, org_id: str) -> Role:
        """Get role by ID with org validation."""
        role = self.db.query(Role).filter(
            and_(Role.id == role_id, Role.org_id == org_id)
        ).first()
        
        if not role:
            raise HTTPException(404, "Role not found")
        
        return role
    
    async def update_role(
        self, 
        role_id: str, 
        org_id: str, 
        role_data: RoleUpdate
    ) -> Role:
        """Update role information."""
        role = await self.get_role(role_id, org_id)
        
        for field, value in role_data.dict(exclude_unset=True).items():
            setattr(role, field, value)
        
        self.db.commit()
        self.db.refresh(role)
        return role
    
    async def delete_role(self, role_id: str, org_id: str):
        """Delete a role if no users are assigned."""
        role = await self.get_role(role_id, org_id)
        
        # Check if any users have this role
        user_count = self.db.query(User).filter(User.role_id == role_id).count()
        if user_count > 0:
            raise HTTPException(
                400, 
                f"Cannot delete role: {user_count} users are assigned to this role"
            )
        
        self.db.delete(role)
        self.db.commit()
```

#### 4.3 Permission Service
**File:** `backend/app/services/permission_service.py`

```python
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.permission import Permission

class PermissionService:
    def __init__(self, db: Session):
        self.db = db
    
    async def list_permissions(self, category: Optional[str] = None) -> List[Permission]:
        """List permissions, optionally filtered by category."""
        query = self.db.query(Permission)
        
        if category:
            query = query.filter(Permission.category == category)
        
        return query.order_by(Permission.category, Permission.name).all()
    
    async def get_categories(self) -> List[str]:
        """Get all permission categories."""
        return [
            category[0] for category in 
            self.db.query(Permission.category).distinct().all()
        ]
    
    async def validate_permissions(self, permission_names: List[str]) -> bool:
        """Validate that all permission names exist."""
        existing_count = self.db.query(Permission).filter(
            Permission.name.in_(permission_names)
        ).count()
        
        return existing_count == len(permission_names)
```

### Phase 5: Testing & Validation
**Priority: MEDIUM** | **Estimated Time: 4-6 hours**

#### 5.1 API Tests
**File:** `backend/tests/test_settings_api.py`

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token

client = TestClient(app)

@pytest.fixture
def auth_headers():
    token = create_access_token({"sub": "test@example.com", "org": "test-org-id"})
    return {"Authorization": f"Bearer {token}"}

class TestUserEndpoints:
    def test_list_users(self, auth_headers):
        response = client.get("/api/v1/settings/users", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_create_user(self, auth_headers):
        user_data = {
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
            "role_id": "some-role-id"
        }
        response = client.post("/api/v1/settings/users", json=user_data, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["email"] == user_data["email"]

class TestRoleEndpoints:
    def test_list_roles(self, auth_headers):
        response = client.get("/api/v1/settings/roles", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_create_role(self, auth_headers):
        role_data = {
            "name": "Test Role",
            "description": "A test role",
            "permissions": ["inventory.read", "analytics.read"]
        }
        response = client.post("/api/v1/settings/roles", json=role_data, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == role_data["name"]

class TestPermissionEndpoints:
    def test_list_permissions(self, auth_headers):
        response = client.get("/api/v1/settings/permissions", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_filter_permissions_by_category(self, auth_headers):
        response = client.get("/api/v1/settings/permissions?category=inventory", headers=auth_headers)
        assert response.status_code == 200
        permissions = response.json()
        assert all(p["category"] == "inventory" for p in permissions)
```

### Phase 6: Security & Validation
**Priority: HIGH** | **Estimated Time: 3-4 hours**

#### 6.1 Security Middleware
**File:** `backend/app/core/security.py` (additions)

```python
def require_role(required_role: str):
    """Decorator to require specific role for endpoint access."""
    def role_checker(claims = Depends(get_current_claims)):
        # Implementation to check user role
        if not has_required_role(claims, required_role):
            raise HTTPException(403, "Insufficient permissions")
        return claims
    return role_checker

def require_permission(permission: str):
    """Decorator to require specific permission for endpoint access."""
    def permission_checker(claims = Depends(get_current_claims)):
        # Implementation to check user permissions
        if not has_permission(claims, permission):
            raise HTTPException(403, "Insufficient permissions")
        return claims
    return permission_checker
```

## Implementation Timeline

### Quick Win (Day 1) - 4-6 hours
- [ ] Create basic settings endpoints returning empty arrays
- [ ] Register settings router in API
- [ ] Test basic connectivity (no more 404 errors)

### Core Implementation (Days 2-3) - 12-16 hours
- [ ] Implement database models and schemas
- [ ] Create and run migration script
- [ ] Implement basic CRUD operations for users/roles/permissions

### Advanced Features (Days 4-5) - 8-12 hours
- [ ] Complete service layer implementation
- [ ] Add security and validation
- [ ] Comprehensive testing

### Polish & Production (Day 6) - 4-6 hours
- [ ] Performance optimization
- [ ] Documentation updates
- [ ] End-to-end testing

## Expected Impact

### Immediate Benefits (After Quick Win)
- ✅ Settings page loads without 404 errors
- ✅ User Management section shows proper empty state
- ✅ Basic user interface functionality restored

### Full Implementation Benefits
- ✅ Complete user management system
- ✅ Role-based access control (RBAC)
- ✅ Permission management interface
- ✅ Multi-tenant security compliance
- ✅ Scalable user onboarding process

## Risk Mitigation

### Data Safety
- All migrations are additive (no data loss)
- Existing user accounts remain functional
- Rollback plan available for each phase

### Security Considerations
- All endpoints protected by JWT authentication
- Org-level data isolation maintained
- Role/permission validation on all operations
- Audit trail for sensitive operations

### Performance Impact
- Indexes added for efficient queries
- Pagination implemented for large datasets
- Minimal impact on existing endpoints

## Success Criteria

### Phase 1 Success
- [ ] No 404 errors on settings page
- [ ] Basic user listing functionality
- [ ] Empty states display correctly

### Full Implementation Success
- [ ] Complete user CRUD operations
- [ ] Role assignment and management
- [ ] Permission-based access control
- [ ] Integration tests pass
- [ ] Frontend-backend integration working
- [ ] Multi-tenant isolation verified

## Maintenance & Future Considerations

### Monitoring
- Track API endpoint usage
- Monitor user creation/modification patterns
- Alert on permission escalation attempts

### Future Enhancements
- Advanced permission inheritance
- User group management
- Audit logging for compliance
- SSO integration capabilities
- Advanced role templates

---

**Document Version:** 1.0  
**Created:** August 19, 2025  
**Last Updated:** August 19, 2025  
**Status:** Implementation Ready
