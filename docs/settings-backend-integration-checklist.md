# Settings Backend Integration - Quick Implementation Checklist

## Overview
This checklist provides a streamlined implementation plan to fix the 404 errors in the StockPilot settings page by implementing the missing backend API endpoints.

## Current Issues
- ❌ `GET /api/v1/settings/users` - 404 Not Found
- ❌ `GET /api/v1/settings/roles` - 404 Not Found  
- ❌ `GET /api/v1/settings/permissions` - 404 Not Found

## Quick Implementation Steps

### 🚀 Phase 1: Immediate Fix (2-4 hours)

#### Step 1: Create Basic Settings Endpoint
```bash
# Create the endpoint file
touch backend/app/api/api_v1/endpoints/settings.py
```

#### Step 2: Implement Minimal Endpoints
Add to `backend/app/api/api_v1/endpoints/settings.py`:

```python
from fastapi import APIRouter, Depends
from app.core.security import get_current_claims

router = APIRouter()

@router.get("/users")
async def list_users(claims = Depends(get_current_claims)):
    """Temporary endpoint - returns empty list"""
    return []

@router.get("/roles") 
async def list_roles(claims = Depends(get_current_claims)):
    """Temporary endpoint - returns empty list"""
    return []

@router.get("/permissions")
async def list_permissions(claims = Depends(get_current_claims)):
    """Temporary endpoint - returns empty list"""
    return []
```

#### Step 3: Register Router
Add to `backend/app/api/api_v1/api.py`:

```python
from app.api.api_v1.endpoints import settings

# Add this line after existing router includes
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
```

#### Step 4: Test
```bash
# Restart backend server
uvicorn app.main:app --reload

# Test endpoints
curl http://localhost:8000/api/v1/settings/users
curl http://localhost:8000/api/v1/settings/roles  
curl http://localhost:8000/api/v1/settings/permissions
```

**Expected Result:** No more 404 errors, settings page loads with empty states.

---

### 📋 Phase 2: Database Schema (4-6 hours)

#### Step 1: Create Models
Create these files:

- `backend/app/models/role.py`
- `backend/app/models/permission.py`
- Update `backend/app/models/user.py`

#### Step 2: Create Migration
Create `backend/migrations/w7_add_roles_permissions.sql`

#### Step 3: Run Migration
```bash
# Apply migration to database
psql -d stockpilot -f backend/migrations/w7_add_roles_permissions.sql
```

---

### 🔧 Phase 3: Full Implementation (8-12 hours)

#### Step 1: Create Schemas
- `backend/app/schemas/user_schemas.py`
- `backend/app/schemas/role_schemas.py`
- `backend/app/schemas/permission_schemas.py`

#### Step 2: Create Services
- `backend/app/services/user_service.py`
- `backend/app/services/role_service.py`
- `backend/app/services/permission_service.py`

#### Step 3: Implement Full CRUD Endpoints
Update `backend/app/api/api_v1/endpoints/settings.py` with complete implementation.

#### Step 4: Add Tests
Create `backend/tests/test_settings_api.py`

---

## Testing Checklist

### After Phase 1 (Immediate Fix)
- [ ] Settings page loads without 404 errors
- [ ] User Management shows "0 users" instead of error
- [ ] Roles & Permissions shows empty state
- [ ] No console errors in browser

### After Phase 2 (Database Schema)
- [ ] Database tables created successfully
- [ ] Default roles and permissions inserted
- [ ] Existing users have roles assigned

### After Phase 3 (Full Implementation)
- [ ] Can create new users
- [ ] Can assign roles to users
- [ ] Can modify permissions
- [ ] All CRUD operations work
- [ ] Multi-tenant isolation working

## Files to Create/Modify

### New Files
```
backend/app/api/api_v1/endpoints/settings.py
backend/app/models/role.py
backend/app/models/permission.py
backend/app/schemas/user_schemas.py
backend/app/schemas/role_schemas.py
backend/app/schemas/permission_schemas.py
backend/app/services/user_service.py
backend/app/services/role_service.py
backend/app/services/permission_service.py
backend/migrations/w7_add_roles_permissions.sql
backend/tests/test_settings_api.py
```

### Modified Files
```
backend/app/api/api_v1/api.py (add router registration)
backend/app/models/user.py (add role relationship)
```

## Command Reference

### Start Development
```bash
# Backend
cd backend && uvicorn app.main:app --reload

# Frontend  
cd frontend && npm run dev
```

### Database Operations
```bash
# Connect to database
psql -d stockpilot

# Run migration
psql -d stockpilot -f backend/migrations/w7_add_roles_permissions.sql

# Check tables
\dt
```

### Testing
```bash
# Run backend tests
cd backend && pytest

# Test specific file
pytest tests/test_settings_api.py

# Test API endpoints
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/settings/users
```

## Success Criteria

✅ **Phase 1 Complete When:**
- No 404 errors in browser console
- Settings page loads completely
- All sections show empty states instead of errors

✅ **Phase 2 Complete When:**
- Database migration runs successfully
- Default roles and permissions exist
- Users have assigned roles

✅ **Full Implementation Complete When:**
- All user CRUD operations work
- Role assignment functional
- Permission management working
- Frontend-backend integration complete
- Tests passing

## Troubleshooting

### Common Issues

**404 Errors Persist:**
- Check router registration in `api.py`
- Verify import statements
- Restart backend server

**Database Errors:**
- Check connection string
- Verify migration syntax
- Check for foreign key conflicts

**Authentication Errors:**
- Verify JWT token format
- Check `get_current_claims` function
- Validate org_id filtering

**Import Errors:**
- Check Python path
- Verify all dependencies installed
- Check for circular imports

---

**Quick Start:** Focus on Phase 1 first to eliminate 404 errors, then gradually implement Phases 2-3 for full functionality.
