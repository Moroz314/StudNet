import React, { useEffect, useMemo, useState } from 'react'
import Header from '../../ui/Header'
import { useDispatch, useSelector } from 'react-redux'
import {
  fetchCategoryFeed,
  fetchCreatorFeed,
  fetchFeed,
  fetchFeedCategories,
  fetchFeedUsers,
  fetchLikedFeed,
  fetchRecommended,
  fetchTrending,
  toggleFeedProjectLike,
} from '../../store/slices/feed'
import { FiHeart, FiSearch, FiStar, FiTrendingUp, FiUsers } from 'react-icons/fi'
import { Link } from 'react-router-dom'

export default function ProjectsFeed() {
  const dispatch = useDispatch()
  const { items, categories, users, isLoading, usersLoading } = useSelector((s) => s.feed)

  const [tab, setTab] = useState('all')
  const [category, setCategory] = useState('')
  const [search, setSearch] = useState('')

  useEffect(() => {
    dispatch(fetchFeedCategories())
    dispatch(fetchFeed({ limit: 20, offset: 0 }))
  }, [dispatch])

  useEffect(() => {
    if (tab === 'all') dispatch(fetchFeed({ limit: 20, offset: 0, category: category || undefined }))
    if (tab === 'recommended') dispatch(fetchRecommended(20))
    if (tab === 'trending') dispatch(fetchTrending({ days: 7, limit: 20 }))
    if (tab === 'liked') dispatch(fetchLikedFeed({ limit: 20, offset: 0 }))
    if (tab === 'category' && category) dispatch(fetchCategoryFeed({ category, limit: 20, offset: 0 }))
  }, [dispatch, tab, category])

  useEffect(() => {
    if (search.trim().length < 2) return
    const timer = setTimeout(() => {
      dispatch(fetchFeedUsers({
        page: 1,
        page_size: 20,
        sort_by: 'username',
        sort_order: 'asc',
        filter: {
          name: search.trim(),
          lastname: search.trim(),
          username: search.trim(),
        },
      }))
    }, 350)
    return () => clearTimeout(timer)
  }, [dispatch, search])

  const filteredItems = useMemo(() => {
    if (!search.trim()) return items
    const q = search.toLowerCase()
    return (items || []).filter((p) => {
      const text = `${p.name || ''} ${p.description || ''} ${(p.tags || []).join(' ')}`.toLowerCase()
      return text.includes(q)
    })
  }, [items, search])
  console.log(filteredItems)

  const normalizedCategories = useMemo(() => {
    return (categories || [])
      .map((c) => {
        if (typeof c === 'string') {
          return { name: c, count: 0 }
        }
        if (c && typeof c === 'object') {
          return {
            name: c.name || c.category || '',
            count: Number(c.projects_count ?? c.count ?? 0),
          }
        }
        return { name: '', count: 0 }
      })
      .filter((c) => c.name)
  }, [categories])

  return (
    <Header>
      <div className="max-w-8xl mx-auto grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 space-y-4">
          <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-4">
            <div className="flex flex-col lg:flex-row gap-3 lg:items-center lg:justify-between">
              <div className="flex flex-wrap items-center gap-2 overflow-x-auto pb-1">
                {[
                  ['all', 'Все'],
                  ['recommended', 'Рекомендованные'],
                  ['trending', 'Тренды'],
                  ['liked', 'Понравившиеся'],
                  ['category', 'Категория'],
                ].map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setTab(key)}
                    className={`px-3 py-1.5 rounded-lg text-sm whitespace-nowrap flex-shrink-0 ${tab === key ? 'bg-purple-600 text-white' : 'bg-gray-800 text-gray-300'}`}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full lg:w-auto">
                <div className="flex-1 lg:w-80 flex items-center gap-2 bg-gray-800 rounded-xl px-3 py-2 border border-gray-700 min-w-0">
                  <FiSearch className="text-gray-400" />
                  <input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Поиск проекта или пользователя..."
                    className="bg-transparent outline-none text-white w-full text-sm"
                  />
                </div>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-xl text-white text-sm w-full sm:w-auto"
                >
                  <option value="">Все категории</option>
                  {normalizedCategories.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name} ({c.count})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {isLoading ? (
            <div className="text-gray-400">Загрузка ленты...</div>
          ) : (
            <div className="space-y-4">
              {filteredItems.map((project) => (
                <div key={project.id} className="bg-gray-900/80 border border-gray-800 rounded-2xl p-5">
                  <div className="flex flex-col sm:flex-row items-start sm:items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <h3 className="text-white text-lg sm:text-xl font-bold break-words">{project.name}</h3>
                      <p className="text-gray-300 mt-2 text-sm line-clamp-2">{project.description || 'Описание не заполнено'}</p>
                      <div className="mt-2 flex items-center gap-2 flex-wrap">
                        {(project.tags || []).map((tag) => (
                          <span key={tag} className="px-2 py-1 text-xs bg-purple-900/40 border border-purple-800 rounded-full text-purple-300">{tag}</span>
                        ))}
                      </div>
                      <p className="text-xs text-gray-500 mt-3">
                        Автор: {project.creator?.username || `${project.creator?.name || ''} ${project.creator?.lastname || ''}`.trim() || 'unknown'}
                      </p>
                      <p className="text-xs text-gray-500 mt-3">
                        Категоря: {project.category || ''}
                      </p>
                    </div>
                    <Link to={`/feed/projects/${project.project_id || project.id}`} className="px-3 py-2 rounded-lg bg-gray-800 text-gray-200 hover:bg-gray-700 text-sm whitespace-nowrap flex-shrink-0">
                      Подробнее
                    </Link>
                  </div>
                  <div className="mt-4 flex items-center gap-4">
                    <button
                      type="button"
                      onClick={() => dispatch(toggleFeedProjectLike({ projectId: project.id, shouldLike: !project.is_liked_by_user }))}
                      className="inline-flex items-center gap-2 text-sm text-gray-300 hover:text-pink-400"
                    >
                      <FiHeart /> {project.likes_count || 0}
                    </button>
                    <span className="text-xs text-gray-500">Откройте проект для полного просмотра</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-4">
          <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-4">
            <h3 className="text-white font-semibold mb-3 flex items-center gap-2"><FiUsers /> Пользователи</h3>
            {usersLoading ? <p className="text-gray-400 text-sm">Поиск...</p> : (
              <div className="space-y-2 max-h-56 overflow-y-auto">
                {users.map((u) => (
                  <button
                    key={u.user_id}
                    type="button"
                    onClick={() => dispatch(fetchCreatorFeed({ userId: u.user_id, limit: 20, offset: 0 }))}
                    className="w-full text-left p-2 rounded-lg hover:bg-gray-800"
                  >
                    <p className="text-gray-100 text-sm">{u.name} {u.lastname}</p>
                    <p className="text-gray-400 text-xs">@{u.username}</p>
                  </button>
                ))}
                {users.length === 0 && <p className="text-gray-500 text-sm">Введите минимум 2 символа.</p>}
              </div>
            )}
          </div>

          <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-4">
            <h3 className="text-white font-semibold mb-3 flex items-center gap-2"><FiTrendingUp /> Быстрые действия</h3>
            <div className="grid grid-cols-2 gap-2">
              <button type="button" onClick={() => setTab('trending')} className="px-2 py-2 rounded-lg bg-gray-800 text-gray-300 text-sm flex items-center justify-center gap-2"><FiTrendingUp /> Тренды</button>
              <button type="button" onClick={() => setTab('recommended')} className="px-2 py-2 rounded-lg bg-gray-800 text-gray-300 text-sm flex items-center justify-center gap-2"><FiStar /> Рекоменд.</button>
            </div>
          </div>

          <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-4 text-sm text-gray-400">
            Тут только карточки. Полная страница проекта открывается по кнопке "Подробнее".
          </div>
        </div>
      </div>
    </Header>
  )
}
