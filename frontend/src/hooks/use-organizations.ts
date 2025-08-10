import { useState, useEffect } from 'react'
import { organizationsApi } from '@/lib/api'
import { Organization } from '@/types'

export function useOrganizations() {
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchOrganizations = async () => {
      try {
        setLoading(true)
        setError(null)
        const orgs = await organizationsApi.getAll()
        setOrganizations(orgs)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch organizations')
      } finally {
        setLoading(false)
      }
    }

    fetchOrganizations()
  }, [])

  const currentOrg = organizations.length > 0 ? organizations[0] : null

  return { organizations, currentOrg, loading, error }
}