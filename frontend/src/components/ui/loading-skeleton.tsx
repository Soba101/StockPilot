import * as React from "react"
import { cn } from "@/lib/utils"

export interface LoadingSkeletonProps {
  className?: string
  variant?: "text" | "circular" | "rectangular" | "card" | "table" | "list"
  lines?: number
  width?: string | number
  height?: string | number
  animation?: boolean
}

export function LoadingSkeleton({
  className,
  variant = "rectangular",
  lines = 1,
  width,
  height,
  animation = true,
}: LoadingSkeletonProps) {
  const baseClasses = cn(
    "bg-muted rounded",
    animation && "animate-pulse-soft",
    className
  )

  const getVariantClasses = () => {
    switch (variant) {
      case "text":
        return "h-4 rounded-sm"
      case "circular":
        return "rounded-full"
      case "rectangular":
        return "rounded-md"
      case "card":
        return "h-48 rounded-lg"
      case "table":
        return "h-12 rounded-sm"
      case "list":
        return "h-16 rounded-lg"
      default:
        return "rounded-md"
    }
  }

  const style = {
    width: width || (variant === "text" ? "100%" : variant === "circular" ? "40px" : "100%"),
    height: height || (variant === "circular" ? "40px" : variant === "text" ? "1rem" : "auto"),
  }

  if (variant === "text" && lines > 1) {
    return (
      <div className="space-y-2">
        {Array.from({ length: lines }).map((_, index) => (
          <div
            key={index}
            className={cn(baseClasses, getVariantClasses())}
            style={{
              ...style,
              width: index === lines - 1 ? "75%" : style.width,
            }}
          />
        ))}
      </div>
    )
  }

  return (
    <div
      className={cn(baseClasses, getVariantClasses())}
      style={style}
    />
  )
}

// Pre-built skeleton components for common use cases
export function TableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="space-y-3">
      {/* Table header */}
      <div className="flex space-x-4">
        {Array.from({ length: cols }).map((_, index) => (
          <LoadingSkeleton key={index} variant="text" className="flex-1" />
        ))}
      </div>
      {/* Table rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex space-x-4">
          {Array.from({ length: cols }).map((_, colIndex) => (
            <LoadingSkeleton
              key={colIndex}
              variant="table"
              className="flex-1"
            />
          ))}
        </div>
      ))}
    </div>
  )
}

export function CardSkeleton() {
  return (
    <div className="space-y-4 p-6 border rounded-lg">
      <div className="flex items-center space-x-4">
        <LoadingSkeleton variant="circular" width={40} height={40} />
        <div className="space-y-2 flex-1">
          <LoadingSkeleton variant="text" width="60%" />
          <LoadingSkeleton variant="text" width="40%" />
        </div>
      </div>
      <LoadingSkeleton variant="text" lines={3} />
      <div className="flex space-x-2">
        <LoadingSkeleton width={80} height={32} />
        <LoadingSkeleton width={80} height={32} />
      </div>
    </div>
  )
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="p-6 border rounded-lg space-y-2">
            <LoadingSkeleton variant="text" width="50%" />
            <LoadingSkeleton variant="text" width="80%" height={28} />
            <LoadingSkeleton variant="text" width="30%" />
          </div>
        ))}
      </div>
      
      {/* Chart */}
      <div className="p-6 border rounded-lg">
        <LoadingSkeleton variant="text" width="200px" className="mb-4" />
        <LoadingSkeleton height={300} />
      </div>
      
      {/* Table */}
      <div className="p-6 border rounded-lg">
        <LoadingSkeleton variant="text" width="150px" className="mb-4" />
        <TableSkeleton rows={3} cols={5} />
      </div>
    </div>
  )
}

export function ListSkeleton({ items = 5 }: { items?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: items }).map((_, index) => (
        <div key={index} className="flex items-center space-x-4 p-4 border rounded-lg">
          <LoadingSkeleton variant="circular" width={48} height={48} />
          <div className="flex-1 space-y-2">
            <LoadingSkeleton variant="text" width="60%" />
            <LoadingSkeleton variant="text" width="40%" />
          </div>
          <LoadingSkeleton width={60} height={32} />
        </div>
      ))}
    </div>
  )
}