# Settings Backend Integration - Implementation Plan

## 🎯 **Problem Statement**

The StockPilot settings page is currently non-functional due to missing backend APIs. Frontend makes requests to endpoints that return 404 errors:

- `GET /api/v1/settings/users` → 404 Not Found
- `GET /api/v1/settings/roles` → 404 Not Found  
- `GET /api/v1/settings/permissions` → 404 Not Found

## 📊 **Current State Analysis**

### ✅ **What Exists**
- ✅ Basic User model with org_id, email, password_hash, role (string)
- ✅ Frontend components for settings UI (UserManagement, PermissionMatrix)
- ✅ Frontend API client structure (usersApi, rolesApi, permissionsApi)
- ✅ React Query hooks for data fetching
- ✅ Multi-tenant architecture patterns

### ❌ **What's Missing**
- ❌ Backend settings endpoints (`/api/v1/settings/*`)
- ❌ Role and Permission models
- ❌ Proper user management CRUD operations
- ❌ Role-Permission relationship management
- ❌ Database migrations for new models

## 🏗️ **Implementation Plan**

### **Phase 1: Backend Data Models** (2-3 hours)

#### 1.1 Enhance User Model
```python
# backend/app/models/user.py - ENHANCE EXISTING
class User(Base, BaseModel):
    __tablename__ = "users"
    
    org_id = Column(BaseModel.UUIDType, ForeignKey("organizations.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role_id = Column(BaseModel.UUIDType, ForeignKey("roles.id"), nullable=True)  # NEW
    status = Column(String(20), nullable=False, default="active")  # NEW: active|inactive|pending|suspended
    last_login_at = Column(DateTime(timezone=True), nullable=True)  # NEW
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    role = relationship("Role", back_populates="users")  # NEW
```

#### 1.2 Create Role Model
```python
# backend/app/models/role.py - NEW FILE
class Role(Base, BaseModel):
    __tablename__ = "roles"
    
    org_id = Column(BaseModel.UUIDType, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(100), nullable=False)  # "Admin", "Manager", "Viewer"
    description = Column(Text, nullable=True)
    is_system_role = Column(Boolean, default=False)  # System vs custom roles
    
    # Relationships
    organization = relationship("Organization", back_populates="roles")
    users = relationship("User", back_populates="role")
    permissions = relationship("Permission", secondary="role_permissions", back_populates="roles")
```

#### 1.3 Create Permission Model
```python
# backend/app/models/permission.py - NEW FILE
class Permission(Base, BaseModel):
    __tablename__ = "permissions"
    
    # No org_id - permissions are global/system-wide
    name = Column(String(100), nullable=False, unique=True)  # "inventory.read", "products.write"
    resource = Column(String(50), nullable=False)  # "inventory", "products", "analytics"
    action = Column(String(20), nullable=False)  # "read", "write", "delete", "admin"
    description = Column(Text, nullable=True)
    
    # Relationships
    roles = relationship("Role", secondary="role_permissions", back_populates="permissions")
```

#### 1.4 Create Role-Permission Junction Table
```python
# backend/app/models/role_permission.py - NEW FILE
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', BaseModel.UUIDType, ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', BaseModel.UUIDType, ForeignKey('permissions.id'), primary_key=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now())
)
```

### **Phase 2: Database Migration** (30 minutes)

#### 2.1 Create Migration SQL
```sql
-- backend/migrations/w7_settings_rbac.sql
-- Add new columns to users table
ALTER TABLE users ADD COLUMN first_name VARCHAR(100);
ALTER TABLE users ADD COLUMN last_name VARCHAR(100);
ALTER TABLE users ADD COLUMN role_id UUID;
ALTER TABLE users ADD COLUMN status VARCHAR(20) DEFAULT 'active';
ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP WITH TIME ZONE;

-- Create roles table
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_system_role BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create permissions table
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(20) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create role_permissions junction table
CREATE TABLE role_permissions (
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (role_id, permission_id)
);

-- Add foreign key constraint to users
ALTER TABLE users ADD CONSTRAINT fk_users_role_id FOREIGN KEY (role_id) REFERENCES roles(id);

-- Create indexes
CREATE INDEX idx_roles_org_id ON roles(org_id);
CREATE INDEX idx_users_role_id ON users(role_id);
CREATE INDEX idx_permissions_resource_action ON permissions(resource, action);

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
('settings.admin', 'settings', 'admin', 'Manage system settings');
```

### **Phase 3: Pydantic Schemas** (45 minutes)

#### 3.1 User Schemas
```python
# backend/app/schemas/user.py - ENHANCE EXISTING
class UserBase(BaseModel):
    email: str
    first_name: str
    last_name: str
    role_id: Optional[str] = None
    status: str = "active"

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role_id: Optional[str] = None
    status: Optional[str] = None

class UserResponse(UserBase):
    id: str
    org_id: str
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    role: Optional["RoleResponse"] = None
```

#### 3.2 Role Schemas
```python
# backend/app/schemas/role.py - NEW FILE
class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None

class RoleCreate(RoleBase):
    permission_ids: List[str] = []

class RoleUpdate(RoleBase):
    permission_ids: Optional[List[str]] = None

class RoleResponse(RoleBase):
    id: str
    org_id: str
    is_system_role: bool
    created_at: datetime
    updated_at: datetime
    permissions: List["PermissionResponse"] = []
```

#### 3.3 Permission Schemas
```python
# backend/app/schemas/permission.py - NEW FILE
class PermissionResponse(BaseModel):
    id: str
    name: str
    resource: str
    action: str
    description: Optional[str] = None
```

### **Phase 4: Backend API Endpoints** (2-3 hours)

#### 4.1 Create Settings Endpoints
```python
# backend/app/api/api_v1/endpoints/settings.py - NEW FILE
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_claims, require_role
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.schemas.user import UserResponse, UserCreate, UserUpdate
from app.schemas.role import RoleResponse, RoleCreate, RoleUpdate
from app.schemas.permission import PermissionResponse

router = APIRouter()

# Users endpoints
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

@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_claims)
):
    """Create a new user (admin only)"""
    require_role(claims, "admin")
    org_id = claims.get("org")
    
    # Check if email already exists
    existing_user = db.query(User).filter(
        User.email == user_data.email,
        User.org_id == org_id
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password and create user
    hashed_password = hash_password(user_data.password)
    user = User(
        **user_data.dict(exclude={"password"}),
        org_id=org_id,
        password_hash=hashed_password
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# Roles endpoints
@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_claims)
):
    """List all roles for the organization"""
    org_id = claims.get("org")
    
    roles = db.query(Role).filter(Role.org_id == org_id).all()
    return roles

@router.post("/roles", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_claims)
):
    """Create a new role (admin only)"""
    require_role(claims, "admin")
    org_id = claims.get("org")
    
    role = Role(
        **role_data.dict(exclude={"permission_ids"}),
        org_id=org_id
    )
    
    # Add permissions
    if role_data.permission_ids:
        permissions = db.query(Permission).filter(
            Permission.id.in_(role_data.permission_ids)
        ).all()
        role.permissions = permissions
    
    db.add(role)
    db.commit()
    db.refresh(role)
    return role

# Permissions endpoints
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

#### 4.2 Register Settings Router
```python
# backend/app/api/api_v1/api.py - UPDATE EXISTING
from app.api.api_v1.endpoints import settings  # ADD THIS IMPORT

# ADD THIS LINE
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
```

### **Phase 5: Frontend Hook Updates** (1 hour)

#### 5.1 Update Users Hook
```typescript
// frontend/src/hooks/use-users.ts - UPDATE ERROR HANDLING
export function useUsers(filters?: UserFilters) {
  return useQuery({
    queryKey: ['users', filters],
    queryFn: () => usersApi.list(filters),
    staleTime: 5 * 60 * 1000,
    retry: (failureCount, error: any) => {
      // Don't retry on 404 or 403 errors
      if (error?.response?.status === 404 || error?.response?.status === 403) {
        return false;
      }
      return failureCount < 3;
    },
    onError: (error: any) => {
      console.error('Failed to load users:', error);
    }
  })
}
```

#### 5.2 Create Roles Hook
```typescript
// frontend/src/hooks/use-roles.ts - NEW FILE
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { rolesApi } from '@/lib/api'

export interface Role {
  id: string
  org_id: string
  name: string
  description?: string
  is_system_role: boolean
  created_at: string
  updated_at: string
  permissions: Permission[]
}

export function useRoles() {
  return useQuery({
    queryKey: ['roles'],
    queryFn: () => rolesApi.list(),
    staleTime: 5 * 60 * 1000,
    retry: (failureCount, error: any) => {
      if (error?.response?.status === 404 || error?.response?.status === 403) {
        return false;
      }
      return failureCount < 3;
    }
  })
}
```

### **Phase 6: Component Updates** (1-2 hours)

#### 6.1 Update UserManagement Component
```typescript
// frontend/src/components/settings/UserManagement.tsx - UPDATE DATA LOADING
export function UserManagement() {
  const { data: users = [], isLoading, error } = useUsers()
  const { data: roles = [] } = useRoles()
  
  // Show proper error states
  if (error) {
    return (
      <div className="p-8 text-center">
        <AlertCircle className="h-8 w-8 text-destructive mx-auto mb-2" />
        <h3 className="text-lg font-semibold mb-2">Failed to load users</h3>
        <p className="text-muted-foreground mb-4">
          {error?.message || 'Unable to connect to the server'}
        </p>
        <Button onClick={() => refetch()}>Try Again</Button>
      </div>
    )
  }
  
  // Replace hardcoded stats with real data
  const stats = {
    total: users.length,
    active: users.filter(u => u.status === 'active').length,
    pending: users.filter(u => u.status === 'pending').length,
    admins: users.filter(u => u.role?.name === 'Admin').length,
  }
  
  // Use real user data in table
  // ... rest of component
}
```

### **Phase 7: Testing Strategy** (1 hour)

#### 7.1 Backend Tests
```python
# backend/tests/test_settings_crud.py - NEW FILE
def test_list_users_requires_auth(client):
    response = client.get("/api/v1/settings/users")
    assert response.status_code == 401

def test_list_users_filters_by_org(client, auth_headers):
    response = client.get("/api/v1/settings/users", headers=auth_headers)
    assert response.status_code == 200
    # Verify only org users returned

def test_create_user_requires_admin(client, viewer_auth_headers):
    user_data = {"email": "test@example.com", "first_name": "Test", "last_name": "User"}
    response = client.post("/api/v1/settings/users", json=user_data, headers=viewer_auth_headers)
    assert response.status_code == 403
```

#### 7.2 Frontend Tests
```typescript
// frontend/src/components/settings/__tests__/UserManagement.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { UserManagement } from '../UserManagement'

test('shows error state when API fails', async () => {
  // Mock API failure
  render(<UserManagement />)
  
  await waitFor(() => {
    expect(screen.getByText(/Failed to load users/)).toBeInTheDocument()
  })
})
```

## 🚀 **Implementation Timeline**

| Phase | Estimated Time | Dependencies |
|-------|---------------|--------------|
| 1. Backend Models | 2-3 hours | - |
| 2. Database Migration | 30 minutes | Phase 1 |
| 3. Pydantic Schemas | 45 minutes | Phase 1 |
| 4. API Endpoints | 2-3 hours | Phases 1-3 |
| 5. Frontend Hooks | 1 hour | Phase 4 |
| 6. Component Updates | 1-2 hours | Phase 5 |
| 7. Testing | 1 hour | All phases |
| **Total** | **8-11 hours** | - |

## 🧪 **Testing Checklist**

### Backend Testing
- [ ] User CRUD operations respect org boundaries
- [ ] Role/Permission relationships work correctly
- [ ] Admin role requirements enforced
- [ ] Proper error handling for invalid data
- [ ] Migration runs without errors

### Frontend Testing
- [ ] Settings page loads without 404 errors
- [ ] User list displays real data
- [ ] Role/Permission matrices work
- [ ] Error states display properly
- [ ] Create/Edit forms submit successfully

### Integration Testing
- [ ] Full user management workflow
- [ ] Role assignment updates user permissions
- [ ] Multi-tenant isolation verified
- [ ] API endpoints return consistent data structure

## 📝 **Success Criteria**

1. ✅ **No more 404 errors** on settings page
2. ✅ **Dynamic user data** loaded from backend
3. ✅ **CRUD operations** work for users/roles/permissions
4. ✅ **Multi-tenant isolation** maintained
5. ✅ **Proper error handling** throughout the flow
6. ✅ **Consistent with existing** architecture patterns

## 🎯 **Next Steps**

1. **Start with Phase 1** - Create the backend models
2. **Run migration** to update database schema  
3. **Implement API endpoints** following existing patterns
4. **Update frontend hooks** with proper error handling
5. **Test thoroughly** before deploying

This plan follows StockPilot's architectural principles and will resolve all identified issues with the settings page.
