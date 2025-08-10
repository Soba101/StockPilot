import { useState, useEffect } from 'react'
import { Organization } from '@/types'
import { useAuth } from '@/contexts/auth-context'

export function useOrganizations() {
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { user, isAuthenticated } = useAuth()

  useEffect(() => {
    const fetchOrganizations = async () => {
      try {
        setLoading(true)
        setError(null)
        
        if (!isAuthenticated || !user) {
          throw new Error('User not authenticated')
        }
        
        // For now, we'll just use the user's org from auth context
        // In the future, if we need to fetch org details, we can do that here
        const currentOrg: Organization = {
          id: user.org_id,
          name: 'Demo Company', // This could be fetched from API if needed
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        }
        setOrganizations([currentOrg])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch organizations')
      } finally {
        setLoading(false)
      }
    }

    if (isAuthenticated && user) {
      fetchOrganizations()
    }
  }, [isAuthenticated, user])

  const currentOrg = organizations.length > 0 ? organizations[0] : null

  return { organizations, currentOrg, loading, error }
}