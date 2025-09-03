# StockPilot Pages Enhancement - Technical Specifications

## Component Architecture & Design System

### Enhanced Settings Components

#### SettingsLayout Component
```typescript
interface SettingsLayoutProps {
  children: React.ReactNode
  currentSection: string
  onSectionChange: (section: string) => void
}

interface SettingsSection {
  id: string
  title: string
  description: string
  icon: React.ComponentType<{ className?: string }>
  component: React.ComponentType
  permissions?: string[]
}
```

**Features:**
- Responsive sidebar navigation with collapsible sections
- Breadcrumb navigation for nested settings
- Progress indicators for multi-step configurations
- Auto-save functionality with optimistic updates
- Permission-based section visibility

#### Enhanced Form Components
```typescript
interface SettingsFormProps<T> {
  schema: ZodSchema<T>
  defaultValues: T
  onSubmit: (data: T) => Promise<void>
  sections?: FormSection[]
  autoSave?: boolean
  saveInterval?: number
}

interface FormSection {
  title: string
  description?: string
  fields: string[]
  collapsible?: boolean
  defaultExpanded?: boolean
}
```

#### Permission Matrix Component
```typescript
interface Permission {
  id: string
  name: string
  description: string
  category: string
  risk_level: 'low' | 'medium' | 'high'
}

interface Role {
  id: string
  name: string
  description: string
  permissions: string[]
  is_system: boolean
}

interface PermissionMatrixProps {
  roles: Role[]
  permissions: Permission[]
  onPermissionChange: (roleId: string, permissionId: string, granted: boolean) => void
  groupBy?: 'category' | 'risk_level'
  showDescriptions?: boolean
}
```

### Enhanced Reports Components

#### Report Builder Component
```typescript
interface ReportBuilderProps {
  dataSources: DataSource[]
  onSave: (report: ReportConfig) => Promise<void>
  onPreview: (config: ReportConfig) => Promise<ReportData>
  template?: ReportTemplate
}

interface DataSource {
  id: string
  name: string
  description: string
  tables: Table[]
  relationships: Relationship[]
}

interface ReportConfig {
  name: string
  description: string
  dataSource: string
  fields: ReportField[]
  filters: ReportFilter[]
  grouping: ReportGrouping[]
  sorting: ReportSorting[]
  formatting: ReportFormatting
  visualization: VisualizationConfig
}

interface ReportField {
  id: string
  name: string
  type: 'dimension' | 'measure'
  aggregation?: 'sum' | 'avg' | 'count' | 'min' | 'max'
  format?: FieldFormat
}
```

#### Scheduled Reports Component
```typescript
interface ScheduledReport {
  id: string
  name: string
  reportConfig: ReportConfig
  schedule: Schedule
  recipients: Recipient[]
  format: 'pdf' | 'excel' | 'csv'
  status: 'active' | 'paused' | 'error'
  lastRun?: Date
  nextRun?: Date
}

interface Schedule {
  frequency: 'daily' | 'weekly' | 'monthly' | 'quarterly'
  dayOfWeek?: number // 0-6 for weekly
  dayOfMonth?: number // 1-31 for monthly
  hour: number // 0-23
  timezone: string
}
```

### Enhanced Analytics Components

#### Executive Dashboard Component
```typescript
interface ExecutiveDashboardProps {
  widgets: DashboardWidget[]
  layout: DashboardLayout
  onLayoutChange: (layout: DashboardLayout) => void
  timeRange: TimeRange
  filters: DashboardFilter[]
}

interface DashboardWidget {
  id: string
  type: 'kpi' | 'chart' | 'table' | 'metric' | 'alert'
  title: string
  config: WidgetConfig
  size: WidgetSize
  position: WidgetPosition
  permissions?: string[]
}

interface KPIWidget extends DashboardWidget {
  type: 'kpi'
  config: {
    metric: string
    comparison?: ComparisonConfig
    target?: number
    format: 'currency' | 'percentage' | 'number'
    trend: boolean
  }
}
```

#### Predictive Analytics Component
```typescript
interface PredictiveAnalyticsProps {
  productId?: string
  categoryId?: string
  timeHorizon: number // days
  confidence: number // 0-100
  models: PredictionModel[]
}

interface PredictionModel {
  id: string
  name: string
  type: 'linear' | 'seasonal' | 'arima' | 'ml'
  accuracy: number
  lastTrained: Date
  parameters: ModelParameters
}

interface DemandForecast {
  productId: string
  predictions: ForecastPoint[]
  confidence_intervals: ConfidenceInterval[]
  seasonality: SeasonalityData
  trend: TrendData
}

interface ForecastPoint {
  date: string
  predicted_demand: number
  lower_bound: number
  upper_bound: number
  confidence: number
}
```

#### Real-time Monitoring Component
```typescript
interface RealTimeMonitorProps {
  metrics: RealTimeMetric[]
  alertThresholds: AlertThreshold[]
  refreshInterval: number
  maxDataPoints: number
}

interface RealTimeMetric {
  id: string
  name: string
  value: number
  unit: string
  trend: 'up' | 'down' | 'stable'
  change: number
  timestamp: Date
  status: 'normal' | 'warning' | 'critical'
}

interface WebSocketData {
  type: 'metric_update' | 'alert' | 'system_status'
  payload: any
  timestamp: string
}
```

## Database Schema Extensions

### Settings Tables
```sql
-- User roles and permissions
CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    is_system BOOLEAN DEFAULT FALSE,
    permissions JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Organization settings
CREATE TABLE organization_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    logo_url TEXT,
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    address JSONB,
    business_details JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- System configuration
CREATE TABLE system_configuration (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(100) NOT NULL,
    key VARCHAR(100) NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(category, key)
);

-- Inventory configuration
CREATE TABLE inventory_configuration (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    default_reorder_point INTEGER DEFAULT 10,
    default_safety_stock INTEGER DEFAULT 5,
    valuation_method VARCHAR(20) DEFAULT 'FIFO',
    low_stock_threshold DECIMAL(5,2) DEFAULT 10.0,
    auto_reorder_enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Reports Tables
```sql
-- Report templates
CREATE TABLE report_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    config JSONB NOT NULL,
    is_system BOOLEAN DEFAULT FALSE,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Scheduled reports
CREATE TABLE scheduled_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    template_id UUID REFERENCES report_templates(id),
    schedule_config JSONB NOT NULL,
    recipients JSONB NOT NULL,
    format VARCHAR(20) DEFAULT 'pdf',
    status VARCHAR(20) DEFAULT 'active',
    last_run TIMESTAMP,
    next_run TIMESTAMP,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Report execution history
CREATE TABLE report_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scheduled_report_id UUID REFERENCES scheduled_reports(id),
    execution_time TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) NOT NULL,
    file_path TEXT,
    error_message TEXT,
    execution_duration INTEGER, -- milliseconds
    record_count INTEGER
);
```

### Analytics Tables
```sql
-- Prediction models
CREATE TABLE prediction_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    config JSONB NOT NULL,
    accuracy DECIMAL(5,4),
    last_trained TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Demand forecasts
CREATE TABLE demand_forecasts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id),
    model_id UUID REFERENCES prediction_models(id),
    forecast_date DATE NOT NULL,
    predicted_demand DECIMAL(10,2),
    confidence_lower DECIMAL(10,2),
    confidence_upper DECIMAL(10,2),
    confidence_level DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(product_id, forecast_date, model_id)
);

-- Real-time metrics
CREATE TABLE real_time_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(100) NOT NULL,
    value DECIMAL(15,4) NOT NULL,
    unit VARCHAR(20),
    timestamp TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);

-- Dashboard configurations
CREATE TABLE dashboard_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    layout JSONB NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## API Specifications

### Settings Endpoints
```typescript
// Organization settings
GET    /api/settings/organization
PUT    /api/settings/organization
POST   /api/settings/organization/logo (multipart/form-data)

// User management
GET    /api/settings/users
POST   /api/settings/users
PUT    /api/settings/users/:id
DELETE /api/settings/users/:id
GET    /api/settings/roles
POST   /api/settings/roles
PUT    /api/settings/roles/:id

// System configuration
GET    /api/settings/system/:category
PUT    /api/settings/system/:category
GET    /api/settings/inventory
PUT    /api/settings/inventory

// Integration settings
GET    /api/settings/integrations
POST   /api/settings/integrations/:type
PUT    /api/settings/integrations/:id
DELETE /api/settings/integrations/:id
```

### Reports Endpoints
```typescript
// Report templates
GET    /api/reports/templates
POST   /api/reports/templates
PUT    /api/reports/templates/:id
DELETE /api/reports/templates/:id
POST   /api/reports/templates/:id/execute

// Scheduled reports
GET    /api/reports/scheduled
POST   /api/reports/scheduled
PUT    /api/reports/scheduled/:id
DELETE /api/reports/scheduled/:id
POST   /api/reports/scheduled/:id/run

// Report builder
GET    /api/reports/data-sources
GET    /api/reports/data-sources/:id/tables
POST   /api/reports/preview
POST   /api/reports/export
```

### Analytics Endpoints
```typescript
// Predictive analytics
GET    /api/analytics/predictions/demand/:productId
POST   /api/analytics/predictions/train-model
GET    /api/analytics/predictions/models
PUT    /api/analytics/predictions/models/:id

// Real-time metrics
GET    /api/analytics/real-time/metrics
WebSocket /api/analytics/real-time/stream

// Executive dashboard
GET    /api/analytics/executive/summary
GET    /api/analytics/executive/kpis
POST   /api/analytics/dashboards
PUT    /api/analytics/dashboards/:id
```

## Security Specifications

### Permission System
```typescript
interface Permission {
  resource: string // 'users', 'reports', 'analytics', 'settings'
  action: string   // 'read', 'write', 'delete', 'execute'
  scope?: string   // 'own', 'team', 'organization'
}

const PERMISSIONS = {
  // Settings permissions
  'settings:organization:read': 'View organization settings',
  'settings:organization:write': 'Modify organization settings',
  'settings:users:read': 'View user list',
  'settings:users:write': 'Create/modify users',
  'settings:system:read': 'View system configuration',
  'settings:system:write': 'Modify system configuration',
  
  // Reports permissions
  'reports:templates:read': 'View report templates',
  'reports:templates:write': 'Create/modify report templates',
  'reports:scheduled:read': 'View scheduled reports',
  'reports:scheduled:write': 'Create/modify scheduled reports',
  'reports:execute': 'Execute reports',
  
  // Analytics permissions
  'analytics:dashboard:read': 'View analytics dashboards',
  'analytics:dashboard:write': 'Create/modify dashboards',
  'analytics:predictions:read': 'View predictive analytics',
  'analytics:real-time:read': 'View real-time metrics'
}
```

### Data Encryption
- All sensitive configuration data encrypted at rest
- API keys and credentials encrypted using AES-256
- Personal data anonymization for analytics
- Secure file storage for report outputs

### Audit Logging
```typescript
interface AuditLog {
  id: string
  user_id: string
  action: string
  resource: string
  resource_id?: string
  changes: Record<string, any>
  ip_address: string
  user_agent: string
  timestamp: Date
}
```

## Performance Specifications

### Caching Strategy
- Redis cache for real-time metrics (TTL: 30 seconds)
- Report template cache (TTL: 1 hour)
- Dashboard configuration cache (TTL: 5 minutes)
- Prediction model cache (TTL: 24 hours)

### Database Optimization
- Indexes on frequently queried columns
- Partitioning for time-series data (real_time_metrics)
- Connection pooling with pgBouncer
- Read replicas for reporting queries

### Frontend Performance
- React.memo for expensive components
- Virtual scrolling for large datasets
- Lazy loading for dashboard widgets
- Service worker for offline functionality

## Testing Specifications

### Component Testing
```typescript
// Settings components
describe('SettingsLayout', () => {
  it('renders navigation sections based on permissions')
  it('handles section changes correctly')
  it('persists settings with auto-save')
})

describe('PermissionMatrix', () => {
  it('displays permissions grouped by category')
  it('handles permission changes')
  it('shows confirmation for high-risk permissions')
})
```

### Integration Testing
- API endpoint testing with Jest and Supertest
- Database transaction testing
- Real-time WebSocket testing
- Report generation testing

### End-to-End Testing
- Settings configuration workflows
- Report creation and scheduling
- Dashboard customization
- Permission-based access control

## Deployment Specifications

### Environment Configuration
```env
# Settings
ORGANIZATION_LOGO_STORAGE=s3://bucket/logos
ENCRYPTION_KEY=<secure-key>
SESSION_TIMEOUT=3600

# Reports
REPORT_STORAGE=s3://bucket/reports
REPORT_QUEUE_REDIS_URL=redis://localhost:6379
WKHTMLTOPDF_PATH=/usr/local/bin/wkhtmltopdf

# Analytics
ANALYTICS_CACHE_REDIS_URL=redis://localhost:6379
PREDICTION_MODEL_PATH=/app/models
WEBSOCKET_REDIS_ADAPTER=redis://localhost:6379
```

### Monitoring & Alerting
- Application metrics with Prometheus
- Error tracking with Sentry
- Performance monitoring with APM
- Database monitoring with pg_stat_statements

This comprehensive technical specification provides the foundation for implementing the enhanced StockPilot pages with enterprise-grade features, security, and performance.