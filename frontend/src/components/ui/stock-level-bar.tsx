import * as React from "react"
import { cn } from "@/lib/utils"
import { TrendingUp, TrendingDown, Minus } from "lucide-react"

export interface StockLevelBarProps {
  current: number
  maximum: number
  reorderPoint?: number
  showLabels?: boolean
  showPercentage?: boolean
  showTrend?: boolean
  trend?: "up" | "down" | "stable"
  size?: "sm" | "default" | "lg"
  className?: string
}

export function StockLevelBar({
  current,
  maximum,
  reorderPoint,
  showLabels = false,
  showPercentage = false,
  showTrend = false,
  trend = "stable",
  size = "default",
  className,
}: StockLevelBarProps) {
  const percentage = Math.min((current / maximum) * 100, 100)
  const reorderPercentage = reorderPoint ? (reorderPoint / maximum) * 100 : 0
  
  // Determine color based on stock level
  const getStockColor = () => {
    if (current === 0) return "bg-stock-out"
    if (reorderPoint && current <= reorderPoint) return "bg-stock-low"
    if (percentage < 30) return "bg-stock-medium"
    return "bg-stock-high"
  }

  const getStockLevel = () => {
    if (current === 0) return "Out of Stock"
    if (reorderPoint && current <= reorderPoint) return "Low Stock"
    if (percentage < 30) return "Medium Stock"
    return "In Stock"
  }

  const sizeClasses = {
    sm: "h-2",
    default: "h-3",
    lg: "h-4",
  }

  const TrendIcon = trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : Minus

  return (
    <div className={cn("space-y-2", className)}>
      {showLabels && (
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium">{getStockLevel()}</span>
          <div className="flex items-center gap-2">
            {showPercentage && (
              <span className="text-muted-foreground">{percentage.toFixed(0)}%</span>
            )}
            {showTrend && (
              <TrendIcon 
                className={cn(
                  "h-4 w-4",
                  trend === "up" && "text-stock-high",
                  trend === "down" && "text-stock-out",
                  trend === "stable" && "text-muted-foreground"
                )} 
              />
            )}
          </div>
        </div>
      )}
      
      <div className="relative">
        {/* Background bar */}
        <div className={cn(
          "w-full rounded-full bg-muted overflow-hidden",
          sizeClasses[size]
        )}>
          {/* Stock level bar */}
          <div
            className={cn(
              "h-full transition-all duration-500 ease-in-out rounded-full",
              getStockColor()
            )}
            style={{ width: `${percentage}%` }}
          />
        </div>
        
        {/* Reorder point indicator */}
        {reorderPoint && reorderPercentage > 0 && (
          <div
            className="absolute top-0 w-0.5 bg-destructive opacity-60 rounded-full"
            style={{ 
              left: `${reorderPercentage}%`, 
              height: "100%",
              transform: "translateX(-50%)"
            }}
            title={`Reorder point: ${reorderPoint}`}
          />
        )}
      </div>
      
      {showLabels && (
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>0</span>
          <span>{current}/{maximum}</span>
        </div>
      )}
    </div>
  )
}

// Convenience function to determine stock status from numbers
export function getStockStatus(current: number, reorderPoint?: number): "in_stock" | "low_stock" | "out_of_stock" {
  if (current === 0) return "out_of_stock"
  if (reorderPoint && current <= reorderPoint) return "low_stock"
  return "in_stock"
}