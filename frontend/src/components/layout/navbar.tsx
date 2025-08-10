'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { 
  BarChart3, 
  Package, 
  TrendingUp, 
  ShoppingCart, 
  MessageCircle, 
  Settings,
  Home
} from 'lucide-react'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: BarChart3 },
  { name: 'Products', href: '/products', icon: Package },
  { name: 'Analytics', href: '/analytics', icon: TrendingUp },
  { name: 'Purchasing', href: '/purchasing', icon: ShoppingCart },
  { name: 'Chat', href: '/chat', icon: MessageCircle },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export function Navbar() {
  const pathname = usePathname()

  return (
    <nav className="bg-background border-b">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-8">
            <Link href="/" className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-primary rounded-md flex items-center justify-center">
                <Home className="w-4 h-4 text-primary-foreground" />
              </div>
              <span className="text-xl font-bold">StockPilot</span>
            </Link>
            
            <div className="hidden md:flex space-x-1">
              {navigation.map((item) => {
                const Icon = item.icon
                const isActive = pathname.startsWith(item.href)
                
                return (
                  <Button
                    key={item.name}
                    variant={isActive ? 'default' : 'ghost'}
                    size="sm"
                    asChild
                  >
                    <Link href={item.href} className="flex items-center space-x-2">
                      <Icon className="w-4 h-4" />
                      <span>{item.name}</span>
                    </Link>
                  </Button>
                )
              })}
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="text-sm text-muted-foreground">
              Demo Company
            </div>
          </div>
        </div>
      </div>
    </nav>
  )
}