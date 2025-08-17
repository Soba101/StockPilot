'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowUp, ArrowDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface KPICardProps {
  title: string;
  value: string | number;
  description?: string;
  icon?: React.ComponentType<{ className?: string }>;
  trend?: {
    value: number;
    label: string;
    direction: 'up' | 'down' | 'neutral';
  };
  className?: string;
}

export function KPICard({ 
  title, 
  value, 
  description, 
  icon: Icon, 
  trend, 
  className 
}: KPICardProps) {
  const formatValue = (val: string | number) => {
    if (typeof val === 'number') {
      return val.toLocaleString();
    }
    return val;
  };

  const getTrendIcon = () => {
    switch (trend?.direction) {
      case 'up':
        return ArrowUp;
      case 'down':
        return ArrowDown;
      default:
        return Minus;
    }
  };

  const getTrendColor = () => {
    switch (trend?.direction) {
      case 'up':
        return 'text-green-600';
      case 'down':
        return 'text-red-600';
      default:
        return 'text-muted-foreground';
    }
  };

  const TrendIcon = getTrendIcon();

  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {Icon && <Icon className="h-4 w-4 text-muted-foreground" />}
      </CardHeader>
      <CardContent>
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="text-xl sm:text-2xl font-bold truncate">{formatValue(value)}</div>
            {description && (
              <p className="text-xs text-muted-foreground mt-1">{description}</p>
            )}
          </div>
          {trend && (
            <div className={cn("flex items-center gap-1 text-xs flex-shrink-0", getTrendColor())}>
              <TrendIcon className="h-3 w-3" />
              <span className="font-medium">{Math.abs(trend.value).toFixed(1)}%</span>
              <span className="text-muted-foreground hidden sm:inline">{trend.label}</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}