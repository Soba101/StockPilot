import { useState, useEffect } from 'react'
import { productsApi } from '@/lib/api'
import { Product } from '@/types'
import { useAuth } from '@/contexts/auth-context'

export function useProducts() {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { user, isAuthenticated } = useAuth()

  const fetchProducts = async () => {
    try {
      setLoading(true)
      setError(null)
      
      if (!isAuthenticated || !user) {
        throw new Error('User not authenticated')
      }
      
      // Use the user's org_id from auth context
      const productsResponse = await productsApi.getByOrg(user.org_id)
      setProducts(productsResponse.data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch products')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isAuthenticated && user) {
      fetchProducts()
    }
  }, [isAuthenticated, user])

  const refetch = () => {
    fetchProducts()
  }

  return { products, loading, error, refetch }
}

export function useProduct(id: string) {
  const [product, setProduct] = useState<Product | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchProduct = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await productsApi.get(id)
        setProduct(response.data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch product')
      } finally {
        setLoading(false)
      }
    }

    if (id) {
      fetchProduct()
    }
  }, [id])

  return { product, loading, error }
}