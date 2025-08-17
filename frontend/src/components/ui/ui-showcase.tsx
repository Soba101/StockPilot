"use client"

import * as React from "react"
import { ColumnDef } from "@tanstack/react-table"
import {
  Button,
  Badge,
  Input,
  Card,
  StatusBadge,
  StockStatusBadge,
  OrderStatusBadge,
  StockLevelBar,
  DataTable,
  LoadingSkeleton,
  FileUpload,
  useToast,
} from "./index"
import { 
  Search, 
  Download, 
  Edit, 
  Trash2, 
  Plus,
  Package,
  TrendingUp
} from "lucide-react"

// Sample data for demonstration
interface Product {
  id: string
  sku: string
  name: string
  category: string
  stock: number
  reorderPoint: number
  status: "in_stock" | "low_stock" | "out_of_stock"
  price: number
}

const sampleProducts: Product[] = [
  {
    id: "1",
    sku: "LAP-001",
    name: "Dell Latitude 7420 14\" Business Laptop",
    category: "Laptops",
    stock: 25,
    reorderPoint: 10,
    status: "in_stock",
    price: 1299.99,
  },
  {
    id: "2",
    sku: "LAP-002",
    name: "HP EliteBook 850 G8 15\" Laptop",
    category: "Laptops",
    stock: 5,
    reorderPoint: 10,
    status: "low_stock",
    price: 1199.99,
  },
  {
    id: "3",
    sku: "MON-001",
    name: "Dell UltraSharp 24\" 1440p Monitor",
    category: "Monitors",
    stock: 0,
    reorderPoint: 15,
    status: "out_of_stock",
    price: 379.99,
  },
]

const columns: ColumnDef<Product>[] = [
  {
    accessorKey: "sku",
    header: "SKU",
  },
  {
    accessorKey: "name",
    header: "Product Name",
    cell: ({ row }) => (
      <div className="max-w-[200px] truncate font-medium">
        {row.getValue("name")}
      </div>
    ),
  },
  {
    accessorKey: "category",
    header: "Category",
    cell: ({ row }) => (
      <Badge variant="outline">{row.getValue("category")}</Badge>
    ),
  },
  {
    accessorKey: "stock",
    header: "Stock Level",
    cell: ({ row }) => {
      const stock = row.getValue("stock") as number
      const reorderPoint = row.original.reorderPoint
      return (
        <div className="w-[120px]">
          <StockLevelBar
            current={stock}
            maximum={50}
            reorderPoint={reorderPoint}
            showLabels={false}
            showPercentage={true}
            size="sm"
          />
        </div>
      )
    },
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => (
      <StockStatusBadge
        status={row.getValue("status")}
        size="sm"
      />
    ),
  },
  {
    accessorKey: "price",
    header: "Price",
    cell: ({ row }) => {
      const amount = parseFloat(row.getValue("price"))
      const formatted = new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
      }).format(amount)
      return <div className="font-medium">{formatted}</div>
    },
  },
  {
    id: "actions",
    cell: ({ row }) => (
      <div className="flex items-center space-x-1">
        <Button variant="ghost" size="icon-sm">
          <Edit className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon-sm">
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    ),
  },
]

export function UIShowcase() {
  const { toastSuccess, toastError, toastWarning, toastStockAlert } = useToast()
  const [loading, setLoading] = React.useState(false)

  const handleFileUpload = async (files: File[]) => {
    toastSuccess("Files uploaded", `Successfully uploaded ${files.length} file(s)`)
  }

  const bulkActions = [
    {
      id: "delete",
      label: "Delete",
      icon: Trash2,
      variant: "destructive" as const,
      action: async (selectedRows: Product[]) => {
        toastSuccess("Products deleted", `Deleted ${selectedRows.length} products`)
      },
    },
    {
      id: "export",
      label: "Export",
      icon: Download,
      variant: "outline" as const,
      action: async (selectedRows: Product[]) => {
        toastSuccess("Export started", `Exporting ${selectedRows.length} products`)
      },
    },
  ]

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">StockPilot UI Components</h1>
        <p className="text-muted-foreground">
          Enhanced inventory management components built on your existing design system
        </p>
      </div>

      {/* Buttons Section */}
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">Enhanced Buttons</h2>
        <div className="flex flex-wrap gap-4">
          <Button variant="default">Default</Button>
          <Button variant="success" icon={Package}>Success</Button>
          <Button variant="warning" icon={TrendingUp}>Warning</Button>
          <Button variant="info">Info</Button>
          <Button variant="destructive">Destructive</Button>
          <Button variant="outline" loading>Loading...</Button>
          <Button size="sm">Small</Button>
          <Button size="lg">Large</Button>
          <Button size="xl">Extra Large</Button>
        </div>
      </Card>

      {/* Status Badges Section */}
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">Status Badges</h2>
        <div className="space-y-4">
          <div>
            <h3 className="text-sm font-medium mb-2">Stock Status</h3>
            <div className="flex flex-wrap gap-2">
              <StockStatusBadge status="in_stock" />
              <StockStatusBadge status="low_stock" />
              <StockStatusBadge status="out_of_stock" />
              <StockStatusBadge status="reordering" />
            </div>
          </div>
          <div>
            <h3 className="text-sm font-medium mb-2">Order Status</h3>
            <div className="flex flex-wrap gap-2">
              <OrderStatusBadge status="pending" />
              <OrderStatusBadge status="approved" />
              <OrderStatusBadge status="shipped" />
              <OrderStatusBadge status="delivered" />
              <OrderStatusBadge status="cancelled" />
            </div>
          </div>
        </div>
      </Card>

      {/* Stock Level Bars Section */}
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">Stock Level Indicators</h2>
        <div className="space-y-6">
          <div>
            <h3 className="text-sm font-medium mb-2">High Stock</h3>
            <StockLevelBar
              current={45}
              maximum={50}
              reorderPoint={15}
              showLabels={true}
              showPercentage={true}
              showTrend={true}
              trend="up"
            />
          </div>
          <div>
            <h3 className="text-sm font-medium mb-2">Low Stock</h3>
            <StockLevelBar
              current={8}
              maximum={50}
              reorderPoint={15}
              showLabels={true}
              showPercentage={true}
              showTrend={true}
              trend="down"
            />
          </div>
          <div>
            <h3 className="text-sm font-medium mb-2">Out of Stock</h3>
            <StockLevelBar
              current={0}
              maximum={50}
              reorderPoint={15}
              showLabels={true}
              showPercentage={true}
              showTrend={true}
              trend="down"
            />
          </div>
        </div>
      </Card>

      {/* Enhanced Inputs Section */}
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">Enhanced Inputs</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Input
            label="Product Name"
            placeholder="Enter product name"
            helper="This will be displayed to customers"
          />
          <Input
            label="Search Products"
            placeholder="Search..."
            leftIcon={Search}
            variant="default"
          />
          <Input
            label="Price"
            placeholder="0.00"
            error="Price must be greater than 0"
            variant="error"
          />
          <Input
            label="SKU"
            placeholder="Generating..."
            loading={true}
          />
        </div>
      </Card>

      {/* Data Table Section */}
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">Enhanced Data Table</h2>
        <DataTable
          data={sampleProducts}
          columns={columns}
          enableSelection={true}
          enableSorting={true}
          enableFiltering={true}
          enableColumnVisibility={true}
          bulkActions={bulkActions}
          searchPlaceholder="Search products..."
          refreshable={true}
          onRefresh={async () => {
            setLoading(true)
            await new Promise(resolve => setTimeout(resolve, 1000))
            setLoading(false)
          }}
          exportable={true}
          onExport={async (format) => {
            toastSuccess("Export started", `Exporting data as ${format.toUpperCase()}`)
          }}
          loading={loading}
        />
      </Card>

      {/* File Upload Section */}
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">File Upload</h2>
        <FileUpload
          accept={{
            "text/csv": [".csv"],
            "application/vnd.ms-excel": [".xls", ".xlsx"],
          }}
          multiple={true}
          maxFiles={5}
          onUpload={handleFileUpload}
          dropzoneText="Drop CSV or Excel files here"
          buttonText="Select Files"
          showPreview={true}
        />
      </Card>

      {/* Loading States Section */}
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">Loading States</h2>
        <div className="space-y-6">
          <div>
            <h3 className="text-sm font-medium mb-2">Text Skeleton</h3>
            <LoadingSkeleton variant="text" lines={3} />
          </div>
          <div>
            <h3 className="text-sm font-medium mb-2">Card Skeleton</h3>
            <LoadingSkeleton variant="card" />
          </div>
          <div>
            <h3 className="text-sm font-medium mb-2">Table Skeleton</h3>
            <LoadingSkeleton variant="table" />
          </div>
        </div>
      </Card>

      {/* Toast Demo Section */}
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">Toast Notifications</h2>
        <div className="flex flex-wrap gap-4">
          <Button
            variant="success"
            onClick={() => toastSuccess("Success!", "Operation completed successfully")}
          >
            Success Toast
          </Button>
          <Button
            variant="destructive"
            onClick={() => toastError("Error!", "Something went wrong")}
          >
            Error Toast
          </Button>
          <Button
            variant="warning"
            onClick={() => toastWarning("Warning!", "Please check your input")}
          >
            Warning Toast
          </Button>
          <Button
            variant="info"
            onClick={() => toastStockAlert("Dell Laptop", 5, 10)}
          >
            Stock Alert
          </Button>
        </div>
      </Card>
    </div>
  )
}