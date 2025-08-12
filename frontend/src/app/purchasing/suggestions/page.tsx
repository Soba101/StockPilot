'use client';

import React, { useState, useMemo } from 'react';
import { 
  useReorderSuggestions, 
  useCreateDraftPOs, 
  useReorderFilters,
  type ReorderSuggestion,
  type ReorderSuggestionsRequest 
} from '@/hooks/use-reorder-suggestions';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { 
  ShoppingCart, 
  AlertTriangle, 
  CheckCircle2, 
  Info, 
  Download,
  Filter,
  Package,
  TrendingUp,
  Clock
} from 'lucide-react';

export default function ReorderSuggestionsPage() {
  // Filter state
  const [filters, setFilters] = useState<ReorderSuggestionsRequest>({
    strategy: 'latest',
    include_zero_velocity: true,
  });
  
  // Selection state
  const [selectedProducts, setSelectedProducts] = useState<Set<string>>(new Set());
  
  // UI state
  const [activeTab, setActiveTab] = useState<'suggestions' | 'summary'>('suggestions');
  const [showFilters, setShowFilters] = useState(false);

  // Hooks
  const { suggestions, summary, loading, error, refetch } = useReorderSuggestions(filters);
  const createDraftPOs = useCreateDraftPOs();
  const { strategyOptions, reasonLabels, velocitySourceLabels } = useReorderFilters();

  // Computed values
  const selectedSuggestions = useMemo(() => {
    return suggestions.filter(s => selectedProducts.has(s.product_id));
  }, [suggestions, selectedProducts]);

  const totalSelectedQuantity = useMemo(() => {
    return selectedSuggestions.reduce((sum, s) => sum + s.recommended_quantity, 0);
  }, [selectedSuggestions]);

  const selectedSuppliers = useMemo(() => {
    return new Set(selectedSuggestions.map(s => s.supplier_name).filter(Boolean));
  }, [selectedSuggestions]);

  // Event handlers
  const handleFilterChange = (key: keyof ReorderSuggestionsRequest, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const handleSelectAll = () => {
    if (selectedProducts.size === suggestions.length) {
      setSelectedProducts(new Set());
    } else {
      setSelectedProducts(new Set(suggestions.map(s => s.product_id)));
    }
  };

  const handleSelectProduct = (productId: string) => {
    const newSelected = new Set(selectedProducts);
    if (newSelected.has(productId)) {
      newSelected.delete(productId);
    } else {
      newSelected.add(productId);
    }
    setSelectedProducts(newSelected);
  };

  const handleCreateDraftPOs = async () => {
    if (selectedProducts.size === 0) return;

    try {
      await createDraftPOs.mutateAsync({
        product_ids: Array.from(selectedProducts),
        strategy: filters.strategy,
        horizon_days_override: filters.horizon_days_override,
        auto_number: true,
      });
      
      // Clear selection after successful creation
      setSelectedProducts(new Set());
      
      // Show success message (you might want to add a toast here)
      alert('Draft purchase orders created successfully!');
    } catch (err) {
      console.error('Error creating draft POs:', err);
      alert('Error creating draft purchase orders. Please try again.');
    }
  };

  const handleExportCSV = () => {
    const csvHeaders = [
      'SKU',
      'Product Name',
      'Supplier',
      'On Hand',
      'Incoming',
      'Recommended Qty',
      'Days Cover Current',
      'Days Cover After',
      'Velocity Source',
      'Reasons',
      'Adjustments'
    ];

    const csvRows = suggestions.map(suggestion => [
      suggestion.sku,
      suggestion.name,
      suggestion.supplier_name || 'N/A',
      suggestion.on_hand.toString(),
      suggestion.incoming.toString(),
      suggestion.recommended_quantity.toString(),
      suggestion.days_cover_current?.toFixed(1) || 'N/A',
      suggestion.days_cover_after?.toFixed(1) || 'N/A',
      velocitySourceLabels[suggestion.velocity_source] || suggestion.velocity_source,
      suggestion.reasons.map(r => reasonLabels[r] || r).join('; '),
      suggestion.adjustments.join('; ')
    ]);

    const csvContent = [csvHeaders, ...csvRows]
      .map(row => row.map(cell => `"${cell}"`).join(','))
      .join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `reorder-suggestions-${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const getRiskBadgeColor = (daysCover?: number) => {
    if (!daysCover) return 'secondary';
    if (daysCover <= 7) return 'destructive';
    if (daysCover <= 14) return 'warning';
    if (daysCover <= 30) return 'secondary';
    return 'default';
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading reorder suggestions...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Error loading reorder suggestions: {error}
            <Button variant="outline" size="sm" onClick={() => refetch()} className="ml-2">
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Purchase Suggestions</h1>
          <p className="text-muted-foreground mt-1">
            AI-powered reorder recommendations based on velocity, lead times, and inventory levels
          </p>
        </div>
        
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
          >
            <Filter className="h-4 w-4 mr-2" />
            Filters
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportCSV}
            disabled={suggestions.length === 0}
          >
            <Download className="h-4 w-4 mr-2" />
            Export CSV
          </Button>
          <Button
            onClick={handleCreateDraftPOs}
            disabled={selectedProducts.size === 0 || createDraftPOs.isPending}
          >
            <ShoppingCart className="h-4 w-4 mr-2" />
            Create Draft POs ({selectedProducts.size})
          </Button>
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Filters</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label>Velocity Strategy</Label>
                <Select
                  value={filters.strategy || 'latest'}
                  onValueChange={(value: 'latest' | 'conservative') => 
                    handleFilterChange('strategy', value)
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {strategyOptions.map(option => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Horizon Override (days)</Label>
                <Input
                  type="number"
                  min="1"
                  max="365"
                  value={filters.horizon_days_override || ''}
                  onChange={(e) => 
                    handleFilterChange('horizon_days_override', 
                      e.target.value ? parseInt(e.target.value) : undefined
                    )
                  }
                  placeholder="Auto (lead + safety)"
                />
              </div>

              <div className="space-y-2">
                <Label>Min Days Cover</Label>
                <Input
                  type="number"
                  min="0"
                  value={filters.min_days_cover || ''}
                  onChange={(e) => 
                    handleFilterChange('min_days_cover', 
                      e.target.value ? parseInt(e.target.value) : undefined
                    )
                  }
                  placeholder="No minimum"
                />
              </div>

              <div className="space-y-2">
                <Label>Max Days Cover</Label>
                <Input
                  type="number"
                  min="0"
                  value={filters.max_days_cover || ''}
                  onChange={(e) => 
                    handleFilterChange('max_days_cover', 
                      e.target.value ? parseInt(e.target.value) : undefined
                    )
                  }
                  placeholder="No maximum"
                />
              </div>

              <div className="flex items-center space-x-2 pt-6">
                <Checkbox
                  id="include-zero-velocity"
                  checked={filters.include_zero_velocity}
                  onCheckedChange={(checked) => 
                    handleFilterChange('include_zero_velocity', checked)
                  }
                />
                <Label htmlFor="include-zero-velocity">Include zero velocity</Label>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Summary Stats */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Suggestions</CardTitle>
              <Package className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summary.total_suggestions}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Quantity</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summary.total_recommended_quantity.toLocaleString()}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Suppliers Involved</CardTitle>
              <Info className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summary.suppliers_involved}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Selected</CardTitle>
              <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {selectedProducts.size}
                <span className="text-sm text-muted-foreground ml-1">
                  ({totalSelectedQuantity.toLocaleString()} units)
                </span>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Content */}
      <Tabs value={activeTab} onValueChange={(value: 'suggestions' | 'summary') => setActiveTab(value)}>
        <TabsList>
          <TabsTrigger value="suggestions">Suggestions ({suggestions.length})</TabsTrigger>
          <TabsTrigger value="summary">Summary</TabsTrigger>
        </TabsList>

        <TabsContent value="suggestions" className="space-y-4">
          {suggestions.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Package className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">No Suggestions Found</h3>
                <p className="text-muted-foreground text-center">
                  No products require reordering based on current filters. 
                  Try adjusting the filters or check your inventory data.
                </p>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Reorder Suggestions</CardTitle>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      checked={selectedProducts.size === suggestions.length}
                      onCheckedChange={handleSelectAll}
                    />
                    <Label>Select All</Label>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12">Select</TableHead>
                      <TableHead>Product</TableHead>
                      <TableHead>Supplier</TableHead>
                      <TableHead>On Hand</TableHead>
                      <TableHead>Incoming</TableHead>
                      <TableHead>Recommended</TableHead>
                      <TableHead>Current Cover</TableHead>
                      <TableHead>After Cover</TableHead>
                      <TableHead>Velocity</TableHead>
                      <TableHead>Reasons</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {suggestions.map((suggestion) => (
                      <TableRow key={suggestion.product_id}>
                        <TableCell>
                          <Checkbox
                            checked={selectedProducts.has(suggestion.product_id)}
                            onCheckedChange={() => handleSelectProduct(suggestion.product_id)}
                          />
                        </TableCell>
                        <TableCell>
                          <div>
                            <div className="font-medium">{suggestion.name}</div>
                            <div className="text-sm text-muted-foreground">{suggestion.sku}</div>
                          </div>
                        </TableCell>
                        <TableCell>
                          {suggestion.supplier_name || (
                            <Badge variant="secondary">No Supplier</Badge>
                          )}
                        </TableCell>
                        <TableCell>{suggestion.on_hand.toLocaleString()}</TableCell>
                        <TableCell>{suggestion.incoming.toLocaleString()}</TableCell>
                        <TableCell>
                          <div className="font-medium">{suggestion.recommended_quantity.toLocaleString()}</div>
                        </TableCell>
                        <TableCell>
                          {suggestion.days_cover_current ? (
                            <Badge variant={getRiskBadgeColor(suggestion.days_cover_current)}>
                              {suggestion.days_cover_current.toFixed(1)}d
                            </Badge>
                          ) : (
                            <span className="text-muted-foreground">N/A</span>
                          )}
                        </TableCell>
                        <TableCell>
                          {suggestion.days_cover_after ? (
                            <Badge variant="outline">
                              {suggestion.days_cover_after.toFixed(1)}d
                            </Badge>
                          ) : (
                            <span className="text-muted-foreground">N/A</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <div className="text-sm">
                            <div>{velocitySourceLabels[suggestion.velocity_source] || suggestion.velocity_source}</div>
                            {suggestion.chosen_velocity && (
                              <div className="text-muted-foreground">
                                {suggestion.chosen_velocity.toFixed(2)}/day
                              </div>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="space-y-1">
                            {suggestion.reasons.map((reason, index) => (
                              <Badge key={index} variant="outline" className="text-xs">
                                {reasonLabels[reason] || reason}
                              </Badge>
                            ))}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="summary" className="space-y-4">
          {summary && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Reason Breakdown</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {Object.entries(summary.reason_breakdown).map(([reason, count]) => (
                      <div key={reason} className="flex justify-between items-center">
                        <span className="text-sm">{reasonLabels[reason] || reason}</span>
                        <Badge variant="secondary">{count}</Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Selected Products Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span>Products Selected:</span>
                      <span className="font-medium">{selectedProducts.size}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Total Quantity:</span>
                      <span className="font-medium">{totalSelectedQuantity.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Unique Suppliers:</span>
                      <span className="font-medium">{selectedSuppliers.size}</span>
                    </div>
                    {selectedSuppliers.size > 0 && (
                      <div>
                        <span className="text-sm text-muted-foreground">Suppliers:</span>
                        <div className="mt-1 space-y-1">
                          {Array.from(selectedSuppliers).map(supplier => (
                            <Badge key={supplier} variant="outline" className="mr-1">
                              {supplier}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}