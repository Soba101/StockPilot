'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/auth-context';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ArrowLeft, Plus, Trash2, Save } from 'lucide-react';
import { useProducts } from '@/hooks/use-products';
import { useLocations } from '@/hooks/use-locations';
import { useAdjustStock, type StockAdjustment } from '@/hooks/use-inventory';

interface AdjustmentItem extends StockAdjustment {
  id: string;
  productName?: string;
  locationName?: string;
}

export default function AdjustStockPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  
  const { products } = useProducts();
  const { locations } = useLocations();
  const adjustStockMutation = useAdjustStock();
  
  const [adjustments, setAdjustments] = useState<AdjustmentItem[]>([
    {
      id: '1',
      product_id: '',
      location_id: '',
      new_quantity: 0,
      reason: '',
      notes: '',
    },
  ]);
  
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  const addAdjustment = () => {
    const newId = (adjustments.length + 1).toString();
    setAdjustments([
      ...adjustments,
      {
        id: newId,
        product_id: '',
        location_id: '',
        new_quantity: 0,
        reason: '',
        notes: '',
      },
    ]);
  };

  const removeAdjustment = (id: string) => {
    if (adjustments.length > 1) {
      setAdjustments(adjustments.filter(adj => adj.id !== id));
    }
  };

  const updateAdjustment = (id: string, field: keyof AdjustmentItem, value: string | number) => {
    setAdjustments(adjustments.map(adj => {
      if (adj.id === id) {
        const updatedAdj = { ...adj, [field]: value };
        
        // Update display names
        if (field === 'product_id') {
          const product = products?.find(p => p.id === value);
          updatedAdj.productName = product ? `${product.name} (${product.sku})` : '';
        }
        if (field === 'location_id') {
          const location = locations?.find(l => l.id === value);
          updatedAdj.locationName = location?.name || '';
        }
        
        return updatedAdj;
      }
      return adj;
    }));
  };

  const handleSubmit = async () => {
    // Validate adjustments
    const validAdjustments = adjustments.filter(adj => 
      adj.product_id && adj.location_id && adj.reason.trim()
    );

    if (validAdjustments.length === 0) {
      alert('Please fill in at least one complete adjustment');
      return;
    }

    setIsSubmitting(true);
    try {
      await adjustStockMutation.mutateAsync({
        adjustments: validAdjustments.map(adj => ({
          product_id: adj.product_id,
          location_id: adj.location_id,
          new_quantity: adj.new_quantity,
          reason: adj.reason,
          notes: adj.notes,
        })),
      });

      alert(`Successfully adjusted stock for ${validAdjustments.length} items`);
      router.push('/inventory');
    } catch (error) {
      alert('Failed to adjust stock. Please try again.');
      console.error('Stock adjustment error:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" asChild>
            <Link href="/inventory">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Inventory
            </Link>
          </Button>
        </div>
        <h1 className="text-3xl font-bold mt-4">Adjust Stock</h1>
        <p className="text-gray-600 mt-2">Update inventory quantities with reason tracking</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Stock Adjustments</CardTitle>
          <CardDescription>
            Make inventory adjustments with proper audit trail
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {adjustments.map((adjustment, index) => (
            <div key={adjustment.id} className="p-4 border rounded-lg space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold">Adjustment #{index + 1}</h3>
                {adjustments.length > 1 && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => removeAdjustment(adjustment.id)}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                )}
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor={`product-${adjustment.id}`}>Product</Label>
                  <Select
                    value={adjustment.product_id}
                    onValueChange={(value) => updateAdjustment(adjustment.id, 'product_id', value)}
                  >
                    <SelectTrigger id={`product-${adjustment.id}`}>
                      <SelectValue placeholder="Select product" />
                    </SelectTrigger>
                    <SelectContent>
                      {products?.map((product) => (
                        <SelectItem key={product.id} value={product.id}>
                          {product.name} ({product.sku})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor={`location-${adjustment.id}`}>Location</Label>
                  <Select
                    value={adjustment.location_id}
                    onValueChange={(value) => updateAdjustment(adjustment.id, 'location_id', value)}
                  >
                    <SelectTrigger id={`location-${adjustment.id}`}>
                      <SelectValue placeholder="Select location" />
                    </SelectTrigger>
                    <SelectContent>
                      {locations?.map((location) => (
                        <SelectItem key={location.id} value={location.id}>
                          {location.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor={`quantity-${adjustment.id}`}>New Quantity</Label>
                  <Input
                    id={`quantity-${adjustment.id}`}
                    type="number"
                    min="0"
                    value={adjustment.new_quantity}
                    onChange={(e) => updateAdjustment(adjustment.id, 'new_quantity', parseInt(e.target.value) || 0)}
                    placeholder="Enter new quantity"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor={`reason-${adjustment.id}`}>Reason *</Label>
                  <Input
                    id={`reason-${adjustment.id}`}
                    value={adjustment.reason}
                    onChange={(e) => updateAdjustment(adjustment.id, 'reason', e.target.value)}
                    placeholder="e.g., Physical count, Damage, Expired"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor={`notes-${adjustment.id}`}>Notes</Label>
                  <Textarea
                    id={`notes-${adjustment.id}`}
                    value={adjustment.notes}
                    onChange={(e) => updateAdjustment(adjustment.id, 'notes', e.target.value)}
                    placeholder="Additional details..."
                    className="min-h-[80px]"
                  />
                </div>
              </div>
            </div>
          ))}

          <div className="flex justify-between">
            <Button variant="outline" onClick={addAdjustment}>
              <Plus className="w-4 h-4 mr-2" />
              Add Another Adjustment
            </Button>

            <div className="space-x-2">
              <Button variant="outline" onClick={() => router.push('/inventory')}>
                Cancel
              </Button>
              <Button onClick={handleSubmit} disabled={isSubmitting}>
                <Save className="w-4 h-4 mr-2" />
                {isSubmitting ? 'Saving...' : 'Save Adjustments'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}