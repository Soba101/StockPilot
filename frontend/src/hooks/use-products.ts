import { useState, useEffect } from 'react'
import { productsApi, organizationsApi } from '@/lib/api'
import { Product } from '@/types'

export function useProducts() {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchProducts = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Get first organization (demo setup)
      const orgsResponse = await organizationsApi.list()
      const orgs = orgsResponse.data
      if (orgs.length === 0) {
        throw new Error('No organization found')
      }
      
      const productsResponse = await productsApi.getByOrg(orgs[0].id)
      setProducts(productsResponse.data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch products')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProducts()
  }, [])

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