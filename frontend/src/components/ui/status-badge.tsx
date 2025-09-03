import * as React from "react"
import { Badge } from "./badge"
import { CheckCircle, AlertTriangle, XCircle, Clock, Package } from "lucide-react"

export interface StatusConfig {
  value: string
  label: string
  variant: "stock-high" | "stock-medium" | "stock-low" | "stock-out" | "success" | "warning" | "destructive" | "info"
  icon?: React.ComponentType<{ className?: string }>
  description?: string
}

// Predefined status configurations
export const stockStatusConfig: StatusConfig[] = [
  {
    value: "in_stock",
    label: "In Stock",
    variant: "stock-high",
    icon: CheckCircle,
    description: "Product is available",
  },
  {
    value: "low_stock",
    label: "Low Stock",
    variant: "stock-medium",
    icon: AlertTriangle,
    description: "Stock level below reorder point",
  },
  {
    value: "out_of_stock",
    label: "Out of Stock",
    variant: "stock-out",
    icon: XCircle,
    description: "Product is not available",
  },
  {
    value: "reordering",
    label: "Reordering",
    variant: "info",
    icon: Clock,
    description: "Reorder in progress",
  },
]

export const orderStatusConfig: StatusConfig[] = [
  {
    value: "pending",
    label: "Pending",
    variant: "warning",
    icon: Clock,
    description: "Order is pending approval",
  },
  {
    value: "approved",
    label: "Approved",
    variant: "info",
    icon: CheckCircle,
    description: "Order has been approved",
  },
  {
    value: "shipped",
    label: "Shipped",
    variant: "stock-medium",
    icon: Package,
    description: "Order has been shipped",
  },
  {
    value: "delivered",
    label: "Delivered",
    variant: "success",
    icon: CheckCircle,
    description: "Order has been delivered",
  },
  {
    value: "cancelled",
    label: "Cancelled",
    variant: "destructive",
    icon: XCircle,
    description: "Order has been cancelled",
  },
]

export interface StatusBadgeProps {
  status: string
  config: StatusConfig[]
  size?: "sm" | "default" | "lg"
  showIcon?: boolean
  showLabel?: boolean
  className?: string
}

export function StatusBadge({ 
  status, 
  config, 
  size = "default", 
  showIcon = true, 
  showLabel = true,
  className 
}: StatusBadgeProps) {
  const statusConfig = config.find(c => c.value === status)
  
  if (!statusConfig) {
    return (
      <Badge variant="outline" size={size} className={className}>
        {status}
      </Badge>
    )
  }

  return (
    <Badge 
      variant={statusConfig.variant} 
      size={size} 
      className={className}
      icon={showIcon ? statusConfig.icon : undefined}
      title={statusConfig.description}
    >
      {showLabel ? statusConfig.label : null}
    </Badge>
  )
}

// Convenience components for common use cases
export function StockStatusBadge(props: Omit<StatusBadgeProps, 'config'>) {
  return <StatusBadge {...props} config={stockStatusConfig} />
}

export function OrderStatusBadge(props: Omit<StatusBadgeProps, 'config'>) {
  return <StatusBadge {...props} config={orderStatusConfig} />
}