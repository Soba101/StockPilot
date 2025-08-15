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
import { ArrowLeft, ArrowRightLeft, Save } from 'lucide-react';
import { useProducts } from '@/hooks/use-products';
import { useLocations } from '@/hooks/use-locations';
import { useTransferStock } from '@/hooks/use-inventory';

interface TransferItem {
  product_id: string;
  from_location_id: string;
  to_location_id: string;
  quantity: number;
  notes?: string;
  productName?: string;
  fromLocationName?: string;
  toLocationName?: string;
}

export default function TransferStockPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  
  const { data: products } = useProducts();
  const { data: locations } = useLocations();
  const transferStockMutation = useTransferStock();
  
  const [transfer, setTransfer] = useState<TransferItem>({
    product_id: '',
    from_location_id: '',
    to_location_id: '',
    quantity: 0,
    notes: '',
  });
  
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  const handleTransferChange = (field: keyof TransferItem, value: string | number) => {
    setTransfer(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSubmit = async () => {
    if (!transfer.product_id || !transfer.from_location_id || !transfer.to_location_id || transfer.quantity <= 0) {
      alert('Please fill in all required fields with valid values');
      return;
    }

    if (transfer.from_location_id === transfer.to_location_id) {
      alert('From and To locations must be different');
      return;
    }

    setIsSubmitting(true);
    
    try {
      await transferStockMutation.mutateAsync({
        product_id: transfer.product_id,
        from_location_id: transfer.from_location_id,
        to_location_id: transfer.to_location_id,
        quantity: transfer.quantity,
        notes: transfer.notes,
      });
      
      alert('Stock transfer completed successfully!');
      router.push('/inventory');
    } catch (error) {
      console.error('Transfer failed:', error);
      alert('Failed to transfer stock. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const selectedProduct = products?.find(p => p.id === transfer.product_id);
  const fromLocation = locations?.find(l => l.id === transfer.from_location_id);
  const toLocation = locations?.find(l => l.id === transfer.to_location_id);

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8 flex items-center gap-4">
        <Button variant="ghost" asChild>
          <Link href="/inventory">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Inventory
          </Link>
        </Button>
        <div>
          <h1 className="text-3xl font-bold">Transfer Stock</h1>
          <p className="text-muted-foreground">Move inventory between locations</p>
        </div>
      </div>

      <div className="max-w-2xl">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ArrowRightLeft className="h-5 w-5" />
              Stock Transfer
            </CardTitle>
            <CardDescription>
              Transfer inventory from one location to another
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="product">Product *</Label>
                <Select value={transfer.product_id} onValueChange={(value) => handleTransferChange('product_id', value)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select product" />
                  </SelectTrigger>
                  <SelectContent>
                    {products?.map((product) => (
                      <SelectItem key={product.id} value={product.id}>
                        {product.sku} - {product.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="quantity">Quantity *</Label>
                <Input
                  id="quantity"
                  type="number"
                  value={transfer.quantity}
                  onChange={(e) => handleTransferChange('quantity', Number(e.target.value))}
                  placeholder="Enter quantity"
                  min="1"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="from_location">From Location *</Label>
                <Select value={transfer.from_location_id} onValueChange={(value) => handleTransferChange('from_location_id', value)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select source location" />
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
                <Label htmlFor="to_location">To Location *</Label>
                <Select value={transfer.to_location_id} onValueChange={(value) => handleTransferChange('to_location_id', value)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select destination location" />
                  </SelectTrigger>
                  <SelectContent>
                    {locations?.map((location) => (
                      <SelectItem key={location.id} value={location.id} disabled={location.id === transfer.from_location_id}>
                        {location.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="notes">Notes</Label>
              <Textarea
                id="notes"
                value={transfer.notes}
                onChange={(e) => handleTransferChange('notes', e.target.value)}
                placeholder="Optional transfer notes..."
                rows={3}
              />
            </div>

            {selectedProduct && fromLocation && toLocation && transfer.quantity > 0 && (
              <div className="p-4 bg-muted rounded-lg">
                <h3 className="font-medium mb-2">Transfer Summary</h3>
                <div className="text-sm text-muted-foreground space-y-1">
                  <p><strong>Product:</strong> {selectedProduct.sku} - {selectedProduct.name}</p>
                  <p><strong>Quantity:</strong> {transfer.quantity} {selectedProduct.uom}</p>
                  <p><strong>From:</strong> {fromLocation.name}</p>
                  <p><strong>To:</strong> {toLocation.name}</p>
                </div>
              </div>
            )}

            <div className="flex gap-3 pt-4">
              <Button
                onClick={handleSubmit}
                disabled={isSubmitting || !transfer.product_id || !transfer.from_location_id || !transfer.to_location_id || transfer.quantity <= 0 || transfer.from_location_id === transfer.to_location_id}
                className="flex-1"
              >
                <Save className="mr-2 h-4 w-4" />
                {isSubmitting ? 'Processing Transfer...' : 'Transfer Stock'}
              </Button>
              <Button variant="outline" asChild>
                <Link href="/inventory">Cancel</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}