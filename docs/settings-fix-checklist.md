# Settings Backend Integration - Implementation Checklist

## 🎯 **Immediate Fix Plan**

Based on Playwright investigation, here's the step-by-step plan to fix the settings page 404 errors:

## ✅ **Step-by-Step Implementation**

### **Step 1: Create Missing Backend Models** ⏱️ 2 hours

#### 1.1 Create Role Model
```bash
# Create new file
touch backend/app/models/role.py
```

**File: `backend/app/models/role.py`**
```python
from sqlalchemy import Column, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from .base import BaseModel

class Role(Base, BaseModel):
    __tablename__ = "roles"
    
    org_id = Column(BaseModel.UUIDType, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_system_role = Column(Boolean, default=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="roles")
    users = relationship("User", back_populates="role")
```

#### 1.2 Create Permission Model
```bash
# Create new file
touch backend/app/models/permission.py
```

**File: `backend/app/models/permission.py`**
```python
from sqlalchemy import Column, String, Text
from app.core.database import Base
from .base import BaseModel

class Permission(Base, BaseModel):
    __tablename__ = "permissions"
    
    name = Column(String(100), nullable=False, unique=True)
    resource = Column(String(50), nullable=False)
    action = Column(String(20), nullable=False)
    description = Column(Text, nullable=True)
```

#### 1.3 Update User Model
**File: `backend/app/models/user.py` - ADD THESE FIELDS**
```python
# Add these imports at the top
from sqlalchemy.orm import relationship

# Add these columns to User class
first_name = Column(String(100), nullable=True)
last_name = Column(String(100), nullable=True)
status = Column(String(20), nullable=False, default="active")
last_login_at = Column(DateTime(timezone=True), nullable=True)
role_id = Column(BaseModel.UUIDType, ForeignKey("roles.id"), nullable=True)

# Add this relationship
role = relationship("Role", back_populates="users")
```

### **Step 2: Create Pydantic Schemas** ⏱️ 30 minutes

#### 2.1 Create User Schemas
**File: `backend/app/schemas/user.py` - CREATE IF MISSING**
```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserResponse(BaseModel):
    id: str
    org_id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: str
    role_id: Optional[str] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    email: str
    first_name: str
    last_name: str
    password: str
    role_id: Optional[str] = None
    status: str = "active"

class UserUpdate(BaseModel):
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role_id: Optional[str] = None
    status: Optional[str] = None
```

#### 2.2 Create Role Schemas
**File: `backend/app/schemas/role.py` - NEW FILE**
```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class RoleResponse(BaseModel):
    id: str
    org_id: str
    name: str
    description: Optional[str] = None
    is_system_role: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
```

#### 2.3 Create Permission Schemas
**File: `backend/app/schemas/permission.py` - NEW FILE**
```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PermissionResponse(BaseModel):
    id: str
    name: str
    resource: str
    action: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

### **Step 3: Create Settings API Endpoints** ⏱️ 1.5 hours

#### 3.1 Create Settings Endpoint File
```bash
# Create new file
touch backend/app/api/api_v1/endpoints/settings.py
```

**File: `backend/app/api/api_v1/endpoints/settings.py`**
```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_claims
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.schemas.user import UserResponse, UserCreate, UserUpdate
from app.schemas.role import RoleResponse, RoleCreate
from app.schemas.permission import PermissionResponse

router = APIRouter()

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    status: Optional[str] = Query(None),
    role_id: Optional[str] = Query(None),
    skip: int = Query(0),
    limit: int = Query(100),
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_claims)
):
    """List all users in the organization"""
    org_id = claims.get("org")
    
    query = db.query(User).filter(User.org_id == org_id)
    
    if status:
        query = query.filter(User.status == status)
    if role_id:
        query = query.filter(User.role_id == role_id)
    
    users = query.offset(skip).limit(limit).all()
    return users

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_claims)
):
    """Get a specific user"""
    org_id = claims.get("org")
    
    user = db.query(User).filter(
        User.id == user_id,
        User.org_id == org_id
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_claims)
):
    """List all roles for the organization"""
    org_id = claims.get("org")
    
    roles = db.query(Role).filter(Role.org_id == org_id).all()
    return roles

@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    resource: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_claims)
):
    """List all available permissions"""
    query = db.query(Permission)
    
    if resource:
        query = query.filter(Permission.resource == resource)
    
    permissions = query.all()
    return permissions
```

#### 3.2 Register Settings Router
**File: `backend/app/api/api_v1/api.py` - ADD IMPORT AND ROUTER**
```python
# Add this import
from app.api.api_v1.endpoints import settings

# Add this line after other router includes
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
```

### **Step 4: Update Main App Imports** ⏱️ 5 minutes

**File: `backend/app/main.py` - ADD MODEL IMPORTS**
```python
# Add these imports after existing model imports
from app.models.role import Role
from app.models.permission import Permission
```

### **Step 5: Database Migration** ⏱️ 15 minutes

#### 5.1 Create Migration File
```bash
# Create migration file
touch backend/migrations/w7_settings_rbac.sql
```

**File: `backend/migrations/w7_settings_rbac.sql`**
```sql
-- Add new columns to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS role_id UUID;

-- Create roles table
CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_system_role BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create permissions table
CREATE TABLE IF NOT EXISTS permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(20) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add foreign key constraint to users (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_users_role_id'
    ) THEN
        ALTER TABLE users ADD CONSTRAINT fk_users_role_id FOREIGN KEY (role_id) REFERENCES roles(id);
    END IF;
END $$;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_roles_org_id ON roles(org_id);
CREATE INDEX IF NOT EXISTS idx_users_role_id ON users(role_id);
CREATE INDEX IF NOT EXISTS idx_permissions_resource_action ON permissions(resource, action);

-- Insert default system permissions
INSERT INTO permissions (name, resource, action, description) VALUES
('inventory.read', 'inventory', 'read', 'View inventory data'),
('inventory.write', 'inventory', 'write', 'Modify inventory data'),
('products.read', 'products', 'read', 'View products'),
('products.write', 'products', 'write', 'Modify products'),
('analytics.read', 'analytics', 'read', 'View analytics and reports'),
('purchasing.read', 'purchasing', 'read', 'View purchase orders'),
('purchasing.write', 'purchasing', 'write', 'Create and modify purchase orders'),
('users.admin', 'users', 'admin', 'Manage users and permissions'),
('settings.admin', 'settings', 'admin', 'Manage system settings')
ON CONFLICT (name) DO NOTHING;

-- Create default admin role for each organization
INSERT INTO roles (org_id, name, description, is_system_role)
SELECT id, 'Admin', 'Full system access', true
FROM organizations
ON CONFLICT DO NOTHING;

-- Update existing users to have first_name, last_name from email
UPDATE users 
SET 
    first_name = COALESCE(first_name, split_part(email, '@', 1)),
    last_name = COALESCE(last_name, 'User'),
    status = COALESCE(status, 'active')
WHERE first_name IS NULL OR last_name IS NULL OR status IS NULL;
```

#### 5.2 Run Migration
```bash
cd backend
# If you have a migration runner, use it. Otherwise, run manually:
psql $DATABASE_URL -f migrations/w7_settings_rbac.sql
```

### **Step 6: Test the Fix** ⏱️ 15 minutes

#### 6.1 Restart Backend Server
```bash
cd backend
uvicorn app.main:app --reload
```

#### 6.2 Test Endpoints Manually
```bash
# Test users endpoint
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/settings/users

# Test roles endpoint  
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/settings/roles

# Test permissions endpoint
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/settings/permissions
```

#### 6.3 Test Frontend
1. Open http://localhost:3000/settings
2. Click on "User Management" - should load without 404 errors
3. Click on "Roles & Permissions" - should load without 404 errors
4. Check browser console - no more 404 errors

## 🚨 **Common Issues & Solutions**

### Issue: Import Errors
**Problem:** `ModuleNotFoundError` for new models
**Solution:** Make sure all new models are imported in `main.py`

### Issue: Database Connection Error
**Problem:** Migration fails
**Solution:** Ensure Docker containers are running: `docker-compose up -d`

### Issue: Foreign Key Constraint Error
**Problem:** Role relationship fails
**Solution:** Check that `organizations` table exists and has data

### Issue: Still Getting 404s
**Problem:** Router not registered
**Solution:** Verify settings router is added to `api.py` and imported correctly

## ✅ **Success Validation**

After implementation, verify:

1. **No 404 errors** in browser console when visiting settings page
2. **API endpoints respond** with 200 status codes
3. **User data loads** dynamically in the settings UI
4. **Database tables created** successfully with relationships
5. **Multi-tenant isolation** works (users only see their org's data)

## 🎯 **Total Implementation Time: ~4.5 hours**

- Step 1: Models (2 hours)
- Step 2: Schemas (30 minutes)  
- Step 3: API Endpoints (1.5 hours)
- Step 4: Imports (5 minutes)
- Step 5: Migration (15 minutes)
- Step 6: Testing (15 minutes)

This checklist provides a concrete, step-by-step approach to fix the settings page issues identified through Playwright testing.
