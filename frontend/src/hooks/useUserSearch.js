import { useState, useCallback } from 'react'
import { searchAPI } from '../services/api'
import debounce from 'lodash/debounce'

export const useUserSearch = (excludeUserId) => {
  const [searchQuery, setSearchQuery] = useState('')
  const [results, setResults] = useState([])
  const [isSearching, setIsSearching] = useState(false)
  const [error, setError] = useState('')
  const [totalCount, setTotalCount] = useState(0)

  const searchUsers = useCallback(
    debounce(async (query, page = 1) => {
      if (!query.trim() || query.length < 1) {
        setResults([])
        setError('')
        setTotalCount(0)
        return
      }

      setIsSearching(true)
      setError('')

      try {
        const response = await searchAPI.searchUsers(query, page, 10)
        const data = response.data
        
        // Фильтруем исключенного пользователя
        const filteredResults = data.profiles.filter(user => 
          user.user_id !== excludeUserId
        )
        
        setResults(filteredResults)
        setTotalCount(data.total_count)
        
        if (filteredResults.length === 0) {
          setError('Пользователи не найдены')
        }
        
      } catch (err) {
        console.error('Search error:', err)
        setResults([])
        setError('Ошибка при поиске пользователей')
        setTotalCount(0)
      } finally {
        setIsSearching(false)
      }
    }, 500),
    [excludeUserId]
  )

  const clearSearch = () => {
    setSearchQuery('')
    setResults([])
    setError('')
    setTotalCount(0)
  }

  return {
    searchQuery,
    setSearchQuery,
    results,
    isSearching,
    error,
    totalCount,
    searchUsers,
    clearSearch
  }
}