'use client'

import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { MessageCircle, ArrowLeft } from 'lucide-react'
import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { useInventory } from '@/hooks/use-inventory'
import { useProducts } from '@/hooks/use-products'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Hi! Ask me about inventory, sales, or purchasing.' },
  ])
  const [input, setInput] = useState('')
  const { summary: inventorySummary } = useInventory()
  const { products } = useProducts()

  const generateResponse = (userInput: string): string => {
    const query = userInput.toLowerCase()
    
    if (!inventorySummary) {
      return "I'm still loading inventory data. Please try again in a moment."
    }

    // Stock level queries
    if (query.includes('stock') || query.includes('inventory')) {
      const lowStockItems = inventorySummary.locations
        ?.flatMap(loc => loc.products.filter(p => p.is_low_stock))
        .slice(0, 3) || []
      
      if (lowStockItems.length > 0) {
        const itemNames = lowStockItems.map(item => item.product_name).join(', ')
        return `📦 Current inventory status: ${inventorySummary.total_products} products across ${inventorySummary.total_locations} locations. Low stock alert: ${itemNames} need restocking.`
      } else {
        return `📦 Current inventory status: ${inventorySummary.total_products} products across ${inventorySummary.total_locations} locations. All stock levels look good!`
      }
    }

    // Low stock queries
    if (query.includes('low stock') || query.includes('reorder')) {
      if (inventorySummary.low_stock_count > 0) {
        const lowStockItems = inventorySummary.locations
          ?.flatMap(loc => loc.products.filter(p => p.is_low_stock))
          .slice(0, 5) || []
        const itemList = lowStockItems.map(item => 
          `${item.product_name} (${item.available_quantity} remaining)`
        ).join(', ')
        return `⚠️ ${inventorySummary.low_stock_count} items need restocking: ${itemList}`
      } else {
        return `✅ All products are well-stocked! No reorder alerts at this time.`
      }
    }

    // Value queries
    if (query.includes('value') || query.includes('worth')) {
      const totalValue = inventorySummary.total_stock_value
      return `💰 Total inventory value: $${totalValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    }

    // Product count queries
    if (query.includes('products') || query.includes('items')) {
      const categories = new Set(products?.map(p => p.category).filter(Boolean) || [])
      return `📊 You have ${inventorySummary.total_products} products across ${categories.size} categories in your inventory.`
    }

    // Location queries
    if (query.includes('location') || query.includes('warehouse')) {
      const locationSummary = inventorySummary.locations?.map(loc => 
        `${loc.location_name}: ${loc.total_products} products`
      ).join(', ') || ''
      return `🏢 Inventory locations: ${locationSummary}`
    }

    // Default response with general insights
    const insights = []
    if (inventorySummary.low_stock_count > 0) {
      insights.push(`${inventorySummary.low_stock_count} items need restocking`)
    }
    if (inventorySummary.out_of_stock_count > 0) {
      insights.push(`${inventorySummary.out_of_stock_count} items are out of stock`)
    }
    if (insights.length === 0) {
      insights.push('All inventory levels look healthy')
    }

    return `I can help with inventory questions! Current status: ${insights.join(', ')}. Try asking about "low stock", "inventory value", or "product count".`
  }

  const send = async () => {
    if (!input.trim()) return
    const userMsg: Message = { role: 'user', content: input.trim() }
    setMessages((m) => [...m, userMsg])
    setInput('')
    
    // Generate response based on real inventory data
    setTimeout(() => {
      const response = generateResponse(userMsg.content)
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: response },
      ])
    }, 400)
  }

  const onKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Chat Assistant</h1>
        <p className="text-muted-foreground">Ask questions about inventory and sales</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageCircle className="h-5 w-5" />
            Assistant
          </CardTitle>
          <CardDescription>Lightweight demo chat</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-72 overflow-y-auto border rounded-md p-3 mb-4 bg-muted/30">
            <div className="space-y-3">
              {messages.map((m, i) => (
                <div key={i} className={`${m.role === 'user' ? 'text-right' : 'text-left'}`}>
                  <div className={`inline-block rounded-md px-3 py-2 text-sm ${
                    m.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-background border'
                  }`}>
                    {m.content}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="flex gap-2">
            <Input
              placeholder="Ask about products, stockouts, etc."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKey}
            />
            <Button onClick={send}>Send</Button>
          </div>
        </CardContent>
      </Card>

      <div className="mt-8">
        <Button variant="ghost" asChild>
          <Link href="/">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Home
          </Link>
        </Button>
      </div>
    </div>
  )
}


