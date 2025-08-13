# StockPilot Authentication Documentation

## Database Credentials

### PostgreSQL Database
- **Username**: `stockpilot`
- **Password**: `stockpilot_dev`
- **Database**: `stockpilot`
- **Host**: `localhost` (or Docker container)
- **Port**: `5432`

### Root PostgreSQL Access
- **Username**: `postgres`
- **Password**: `stockpilot_dev`
- **Database**: `stockpilot`
- **Host**: `localhost`
- **Port**: `5432`

## Application User Accounts

### TechFlow Solutions Inc. Organization
Most TechFlow users use individual passwords based on the pattern: `password123_{email}`, with one exception noted below.

| Email | Role | Organization | Password (Plain) |
|-------|------|--------------|------------------|
| `admin@admin.com` | admin | TechFlow Solutions Inc. | admin123 |
| `admin@techflow.com` | admin | TechFlow Solutions Inc. | password123_admin@techflow.com |
| `purchasing@techflow.com` | purchaser | TechFlow Solutions Inc. | password123_purchasing@techflow.com |
| `warehouse@techflow.com` | admin | TechFlow Solutions Inc. | password123_warehouse@techflow.com |
| `sales@techflow.com` | viewer | TechFlow Solutions Inc. | password123_sales@techflow.com |
| `inventory@techflow.com` | purchaser | TechFlow Solutions Inc. | password123_inventory@techflow.com |
| `support@techflow.com` | viewer | TechFlow Solutions Inc. | password123_support@techflow.com |

## Password Hash Information

All user passwords are hashed using **bcrypt** (as required by the application's security system). Two password patterns are used:

**Pattern 1: Simple admin password**
```
$2b$12$JrtOzQ6oLcvgzIxCFZm9TuXdP4DF6GRTE1d7mp2XocjsYypUtkuBO
```
This is the bcrypt hash of "admin123" (used for admin@admin.com)

**Pattern 2: Email-based passwords**

Each TechFlow user has a password following the pattern `password123_{email_address}`, hashed with bcrypt.

For example:
- admin@techflow.com → bcrypt hash of "password123_admin@techflow.com"  
- sales@techflow.com → bcrypt hash of "password123_sales@techflow.com"

All passwords have been properly hashed using bcrypt with cost factor 12 for security.

## User Roles

The system supports three user roles with different permissions:

- **admin**: Full access to all features and data management
- **viewer**: Read-only access to inventory and reports
- **purchaser**: Can create and manage purchase orders, view inventory

## Redis Configuration

- **Host**: `localhost` (or Docker container)
- **Port**: `6379`
- **Database**: `0` (default)
- **Authentication**: None (default Redis setup)

## Environment Variables for Development

The following environment variables are used for authentication:

```env
# Database
DATABASE_URL=postgresql://stockpilot:stockpilot_dev@localhost:5432/stockpilot

# JWT Security
SECRET_KEY=development-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Redis
REDIS_URL=redis://localhost:6379/0

# API Keys (optional)
OPENAI_API_KEY=your-openai-key

# Alerting (for cron jobs)
ALERT_CRON_TOKEN=dev-cron-token
```

## Multi-Tenant Architecture

The system uses a single organization model with TechFlow Solutions Inc.:

- Each user belongs to the organization (`org_id`)
- All API endpoints filter data by the user's organization  
- JWT tokens include the organization claim for access control
- Cross-organization data access is prevented at the database level

## Security Notes

⚠️ **Important**: These are development credentials and should **NEVER** be used in production.

- All sample users share the same password for development convenience
- The JWT secret key is hardcoded for development
- Database passwords are simple and predictable
- In production, use strong, unique passwords and proper secret management
- Consider implementing password complexity requirements
- Enable proper SSL/TLS encryption for database connections
- Use environment variables for all sensitive configuration

## Quick Login for Testing

For quick testing, you can use any of these login combinations:

**Simple Admin (Easiest):**

- Email: `admin@admin.com`
- Password: `admin123`

**TechFlow Admin:**

- Email: `admin@techflow.com`
- Password: `password123_admin@techflow.com`

**TechFlow Warehouse Manager:**

- Email: `warehouse@techflow.com`
- Password: `password123_warehouse@techflow.com`

All accounts provide full administrative access to TechFlow Solutions Inc.