'use client';

import React from 'react';
import { useReorderExplanation, type ReorderExplanation } from '@/hooks/use-reorder-suggestions';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Calculator, 
  TrendingUp, 
  Package, 
  Clock, 
  AlertTriangle, 
  CheckCircle2,
  Info,
  X
} from 'lucide-react';

interface ReorderExplanationProps {
  productId: string;
  strategy?: 'latest' | 'conservative';
  horizonDaysOverride?: number;
  onClose: () => void;
}

export function ReorderExplanationDrawer({ 
  productId, 
  strategy = 'latest',
  horizonDaysOverride,
  onClose 
}: ReorderExplanationProps) {
  const { 
    data: explanation, 
    isLoading, 
    error 
  } = useReorderExplanation(productId, { 
    strategy,
    horizon_days_override: horizonDaysOverride 
  });

  if (isLoading) {
    return (
      <div className="fixed inset-y-0 right-0 w-1/2 bg-white shadow-xl z-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading explanation...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-y-0 right-0 w-1/2 bg-white shadow-xl z-50 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Reorder Explanation</h2>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Error loading explanation: {error.message}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!explanation) {
    return (
      <div className="fixed inset-y-0 right-0 w-1/2 bg-white shadow-xl z-50 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Reorder Explanation</h2>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            No explanation data available for this product.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-25 z-40" 
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div className="fixed inset-y-0 right-0 w-1/2 bg-white shadow-xl z-50 overflow-y-auto">
        <div className="p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-semibold">Reorder Explanation</h2>
              <div className="text-sm text-muted-foreground mt-1">
                <span className="font-medium">{explanation.name}</span>
                <span className="ml-2">({explanation.sku})</span>
              </div>
            </div>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>

          {/* Skipped Product */}
          {explanation.skipped && (
            <Alert className="mb-6">
              <Info className="h-4 w-4" />
              <AlertDescription>
                <strong>Product Skipped:</strong> {explanation.skip_reason}
              </AlertDescription>
            </Alert>
          )}

          {/* Recommendation Summary */}
          {explanation.recommendation && (
            <Card className="mb-6">
              <CardHeader>
                <CardTitle className="flex items-center">
                  <CheckCircle2 className="h-5 w-5 mr-2 text-green-600" />
                  Recommendation
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-2xl font-bold text-green-600">
                      {explanation.recommendation.quantity?.toLocaleString()}
                    </div>
                    <div className="text-sm text-muted-foreground">Units to Order</div>
                  </div>
                  {explanation.recommendation.supplier_name && (
                    <div>
                      <div className="font-medium">{explanation.recommendation.supplier_name}</div>
                      <div className="text-sm text-muted-foreground">Preferred Supplier</div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Coverage Information */}
          {explanation.coverage && (
            <div className="grid grid-cols-2 gap-4 mb-6">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center">
                    <Clock className="h-4 w-4 mr-2" />
                    Current Coverage
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-lg font-semibold">
                    {explanation.coverage.days_cover_current ? 
                      `${explanation.coverage.days_cover_current.toFixed(1)} days` : 
                      'N/A'
                    }
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center">
                    <TrendingUp className="h-4 w-4 mr-2" />
                    After Reorder
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-lg font-semibold text-green-600">
                    {explanation.coverage.days_cover_after ? 
                      `${explanation.coverage.days_cover_after.toFixed(1)} days` : 
                      'N/A'
                    }
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Velocity Information */}
          {explanation.velocity && (
            <Card className="mb-6">
              <CardHeader>
                <CardTitle className="text-sm flex items-center">
                  <TrendingUp className="h-4 w-4 mr-2" />
                  Velocity Analysis
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="font-medium">
                      {explanation.velocity.chosen_velocity ? 
                        `${explanation.velocity.chosen_velocity.toFixed(2)} units/day` : 
                        'No velocity data'
                      }
                    </div>
                    <div className="text-sm text-muted-foreground">Selected Velocity</div>
                  </div>
                  <div>
                    <Badge variant="outline">{explanation.velocity.source}</Badge>
                    <div className="text-sm text-muted-foreground mt-1">Data Source</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Reasons and Adjustments */}
          <div className="grid grid-cols-1 gap-4 mb-6">
            {explanation.reasons.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Decision Reasons</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {explanation.reasons.map((reason, index) => (
                      <Badge key={index} variant="secondary">
                        {getReasonsLabel(reason)}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {explanation.adjustments.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Applied Adjustments</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {explanation.adjustments.map((adjustment, index) => (
                      <div key={index} className="text-sm p-2 bg-muted rounded">
                        {adjustment}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Detailed Calculation */}
          {explanation.explanation && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center">
                  <Calculator className="h-4 w-4 mr-2" />
                  Detailed Calculation
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="inputs">
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="inputs">Inputs</TabsTrigger>
                    <TabsTrigger value="calculations">Calculations</TabsTrigger>
                    <TabsTrigger value="logic">Logic Path</TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="inputs" className="mt-4">
                    <div className="space-y-3">
                      {Object.entries(explanation.explanation.inputs).map(([key, value]) => (
                        <div key={key} className="flex justify-between">
                          <span className="text-sm capitalize">
                            {key.replace(/_/g, ' ')}:
                          </span>
                          <span className="text-sm font-medium">
                            {typeof value === 'number' ? value.toLocaleString() : String(value)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="calculations" className="mt-4">
                    <div className="space-y-3">
                      {Object.entries(explanation.explanation.calculations).map(([key, value]) => (
                        <div key={key} className="flex justify-between">
                          <span className="text-sm capitalize">
                            {key.replace(/_/g, ' ')}:
                          </span>
                          <span className="text-sm font-medium">
                            {typeof value === 'number' ? value.toLocaleString() : String(value)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="logic" className="mt-4">
                    <div className="space-y-2">
                      {explanation.explanation.logic_path.map((step, index) => (
                        <div key={index} className="text-sm p-2 bg-muted rounded flex items-start">
                          <span className="bg-primary text-primary-foreground rounded-full w-5 h-5 flex items-center justify-center text-xs mr-2 mt-0.5">
                            {index + 1}
                          </span>
                          {step}
                        </div>
                      ))}
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}

// Helper function to get human-readable reason labels
function getReasonsLabel(reason: string): string {
  const labels: Record<string, string> = {
    'BELOW_REORDER_POINT': 'Below Reorder Point',
    'LEAD_TIME_RISK': 'Lead Time Risk',
    'MOQ_ENFORCED': 'MOQ Enforced',
    'PACK_ROUNDED': 'Pack Size Rounded',
    'CAPPED_BY_MAX_DAYS': 'Capped by Max Stock Days',
    'ZERO_VELOCITY_SKIPPED': 'Zero Velocity (Skipped)',
    'INCOMING_COVERAGE': 'Has Incoming Stock',
    'NO_VELOCITY': 'No Velocity Data',
  };
  
  return labels[reason] || reason;
}