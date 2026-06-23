import React, { useEffect, useMemo, useState } from 'react'
import Header from '../ui/Header'
import { useSelector } from 'react-redux'
import { useUserSearch } from '../hooks/useUserSearch'
import { normalizeAssetUrl, relationshipsAPI } from '../services/api'
import { FaSearch, FaTimes, FaUserPlus, FaUserMinus } from 'react-icons/fa'
import { Link } from 'react-router-dom'

function safeParseJSON(value, fallback) {
  try {
    const parsed = JSON.parse(value)
    return parsed ?? fallback
  } catch {
    return fallback
  }
}

function getDisplayName(user) {
  const name = [user?.name, user?.surname].filter(Boolean).join(' ').trim()
  if (name) return name
  return user?.username ? `@${user.username}` : `ID ${user?.user_id ?? ''}`.trim()
}

function getInitials(user) {
  const first = (user?.name || user?.username || '').trim()
  const last = (user?.surname || '').trim()
  const a = first ? first[0] : ''
  const b = last ? last[0] : ''
  const res = (a + b).toUpperCase()
  return res || 'U'
}

function normalizeFriend(user) {
  return {
    user_id: user?.user_id,
    username: user?.username || '',
    name: user?.name || '',
    surname: user?.surname || '',
    avatar_path: normalizeAssetUrl(user?.avatar_url || user?.avatar_path || ''),
    university: user?.university || '',
    faculty: user?.faculty || '',
    course: user?.course || '',
  }
}

export default function Friends() {
  const profile = useSelector((state) => state.profile.profile)
  const currentUserId = profile?.user_id
  console.log('Current user ID:', profile?.user_id)

  const [tab, setTab] = useState('friends') // friends | search
  const [friends, setFriends] = useState([])
  const [pending, setPending] = useState({ incoming: [], outgoing: [] })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const {
    searchQuery,
    setSearchQuery,
    results,
    isSearching,
    error: searchError,
    totalCount,
    searchUsers,
    clearSearch,
  } = useUserSearch(currentUserId)

  // Загрузка друзей и заявок с backend
useEffect(() => {
  const loadAll = async () => {
    if (!currentUserId) {
      console.warn('No currentUserId, skipping load')
      return
    }
    
    try {
      setIsLoading(true)
      setError('')
      
      console.log('Loading relationships for user:', currentUserId)
      
      const [friendsRes, pendingRes] = await Promise.all([
        relationshipsAPI.getFriends(),
        relationshipsAPI.getPendingRequests(),
      ])
      
      console.log('=== RAW API RESPONSES ===')
      console.log('Friends response:', friendsRes)
      console.log('Pending response:', pendingRes)
      
      // Парсим друзей
      let friendsData = []
      if (friendsRes.data) {
        if (Array.isArray(friendsRes.data)) {
          friendsData = friendsRes.data
        } else if (friendsRes.data.friends && Array.isArray(friendsRes.data.friends)) {
          friendsData = friendsRes.data.friends
        } else if (friendsRes.data.items && Array.isArray(friendsRes.data.items)) {
          friendsData = friendsRes.data.items
        } else if (friendsRes.data.profiles && Array.isArray(friendsRes.data.profiles)) {
          friendsData = friendsRes.data.profiles
        } else if (friendsRes.data.results && Array.isArray(friendsRes.data.results)) {
          friendsData = friendsRes.data.results
        } else {
          // Если пришел объект, возможно это один пользователь
          if (friendsRes.data.user_id) {
            friendsData = [friendsRes.data]
          }
        }
      }
      
      // Парсим заявки
      let incoming = []
      let outgoing = []
      if (pendingRes.data) {
        if (pendingRes.data.incoming && Array.isArray(pendingRes.data.incoming)) {
          incoming = pendingRes.data.incoming
        }
        if (pendingRes.data.outgoing && Array.isArray(pendingRes.data.outgoing)) {
          outgoing = pendingRes.data.outgoing
        }
      }
      
      console.log('Parsed friends data:', friendsData)
      console.log('Parsed incoming:', incoming)
      console.log('Parsed outgoing:', outgoing)
      
      setFriends(friendsData.map(normalizeFriend))
      setPending({ incoming, outgoing })
      
      if (friendsData.length === 0) {
        console.log('No friends found')
      }
      
    } catch (e) {
      console.error('Error loading relationships:', e)
      console.error('Error details:', e.response?.data || e.message)
      setError(`Не удалось загрузить список друзей и заявок: ${e.message}`)
    } finally {
      setIsLoading(false)
    }
  }
  
  loadAll()
}, [currentUserId])

  useEffect(() => {
    if (searchQuery) searchUsers(searchQuery)
  }, [searchQuery, searchUsers])

  const friendIds = useMemo(() => new Set(friends.map((f) => f.user_id)), [friends])

  const filteredResults = useMemo(() => {
    if (!Array.isArray(results)) return []
    return results.filter((u) => u?.user_id != null)
  }, [results])

const addFriend = async (user) => {
  if (!user?.user_id) return;

  try {
    const response = await relationshipsAPI.sendFriendRequest(user.user_id);
    const message = response?.data?.message || '';

    if (message === 'Friend request accepted') {
      setPending((prev) => ({
        ...prev,
        incoming: prev.incoming.filter((r) => String(r.user_id) !== String(user.user_id)),
        outgoing: prev.outgoing.filter((r) => String(r.user_id) !== String(user.user_id)),
      }));
      setFriends((prev) => {
        if (prev.some((f) => String(f.user_id) === String(user.user_id))) return prev;
        return [normalizeFriend(user), ...prev];
      });
      return;
    }

    setPending((prev) => ({
      ...prev,
      outgoing: [
        ...prev.outgoing.filter((r) => String(r.user_id) !== String(user.user_id)),
        normalizeFriend(user),
      ],
    }));
  } catch (e) {
    console.error('Error sending friend request:', e);
    const detail = e.response?.data?.detail;

    if (detail === 'Friend request already exists' || detail === 'Friend request already sent') {
      setPending((prev) => ({
        ...prev,
        outgoing: [
          ...prev.outgoing.filter((r) => String(r.user_id) !== String(user.user_id)),
          normalizeFriend(user),
        ],
      }));
      return;
    }

    alert('Не удалось отправить заявку в друзья');
  }
};

  const removeFriend = async (userId) => {
    try {
      await relationshipsAPI.removeFriend(userId)
      setFriends((prev) => prev.filter((f) => String(f.user_id) !== String(userId)))
    } catch (e) {
      console.error('Error removing friend:', e)
      alert('Не удалось удалить из друзей')
    }
  }

  const acceptRequest = async (userId) => {
    try {
      await relationshipsAPI.acceptFriendRequest(userId)
      // переносим из incoming в friends
      setPending((prev) => ({
        ...prev,
        incoming: prev.incoming.filter((u) => String(u.user_id) !== String(userId)),
      }))
      setFriends((prev) => {
        const fromReq = pending.incoming.find((u) => String(u.user_id) === String(userId))
        if (!fromReq) return prev
        if (prev.some((f) => String(f.user_id) === String(userId))) return prev
        return [normalizeFriend(fromReq), ...prev]
      })
    } catch (e) {
      console.error('Error accepting request:', e)
      alert('Не удалось принять заявку')
    }
  }

  const rejectRequest = async (userId) => {
    try {
      await relationshipsAPI.rejectFriendRequest(userId)
      setPending((prev) => ({
        ...prev,
        incoming: prev.incoming.filter((u) => String(u.user_id) !== String(userId)),
      }))
    } catch (e) {
      console.error('Error rejecting request:', e)
      alert('Не удалось отклонить заявку')
    }
  }

  const cancelRequest = async (userId) => {
    try {
      await relationshipsAPI.cancelFriendRequest(userId)
      setPending((prev) => ({
        ...prev,
        outgoing: prev.outgoing.filter((u) => String(u.user_id) !== String(userId)),
      }))
    } catch (e) {
      console.error('Error cancelling request:', e)
      alert('Не удалось отменить заявку')
    }
  }

  return (
    <Header>
      <div className="bg-white dark:bg-black p-3 sm:p-4 md:p-6 page-viewport">
        <div className="max-w-6xl mx-auto h-full flex flex-col min-h-0">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4 mb-4 sm:mb-6">
            <div>
              <h1 className="text-2xl font-bold text-black dark:text-white">Друзья</h1>
              
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => setTab('friends')}
                className={[
                  'px-4 py-2 rounded-xl border transition-colors',
                  tab === 'friends'
                    ? 'bg-purple-600 text-white border-purple-600'
                    : 'bg-transparent text-black dark:text-white border-gray-300 dark:border-gray-800 hover:border-purple-500',
                ].join(' ')}
              >
                Мои друзья ({friends.length})
              </button>
              <button
                onClick={() => setTab('search')}
                className={[
                  'px-4 py-2 rounded-xl border transition-colors',
                  tab === 'search'
                    ? 'bg-purple-600 text-white border-purple-600'
                    : 'bg-transparent text-black dark:text-white border-gray-300 dark:border-gray-800 hover:border-purple-500',
                ].join(' ')}
              >
                Поиск людей
              </button>
            </div>
          </div>

          {tab === 'friends' && (
            <div className="flex-1 min-h-0 bg-gray-900/80 rounded-2xl border border-gray-800 p-4 sm:p-6 overflow-y-auto">
              {isLoading && (
                <div className="py-10 text-center text-gray-400">Загрузка списка друзей...</div>
              )}
              {error && !isLoading && (
                <div className="py-4 text-center text-red-400 text-sm">{error}</div>
              )}
              {!isLoading && friends.length === 0 && !error ? (
                <div className="text-center py-16">
                  <div className="text-gray-300 text-lg font-semibold mb-2">Пока друзей нет</div>
                  <div className="text-gray-500 text-sm mb-6">Перейдите во вкладку “Поиск людей” и добавьте друзей.</div>
                  <button
                    onClick={() => setTab('search')}
                    className="px-5 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-xl transition-colors"
                  >
                    Найти людей
                  </button>
                </div>
              ) : !isLoading && friends.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {friends.map((f) => (
                    <div
                      key={f.user_id}
                      className="bg-gray-800/30 border border-gray-700 rounded-xl p-5 hover:border-purple-600/50 transition-all duration-300"
                    >
                      <div className="flex items-center gap-4">
                        <Link to={`/user_profile/${f.user_id}`} className="flex items-center gap-4 flex-1 min-w-0">
                          <div className="relative w-12 h-12 rounded-full overflow-hidden border border-gray-700 flex items-center justify-center bg-gradient-to-r from-purple-700 to-indigo-700 text-white font-bold">
                            {normalizeAssetUrl(f.avatar_url || f.avatar_path) ? (
                              <img
                                src={normalizeAssetUrl(f.avatar_url || f.avatar_path)}
                                alt={f.username || String(f.user_id)}
                                className="w-full h-full object-cover"
                                onError={(e) => {
                                  e.currentTarget.style.display = 'none'
                                }}
                              />
                            ) : (
                              <span>{getInitials(f)}</span>
                            )}
                          </div>

                          <div className="flex-1 min-w-0">
                            <div className="text-white font-semibold truncate">{getDisplayName(f)}</div>
                            <div className="text-gray-400 text-sm truncate">{f.username ? `@${f.username}` : ''}</div>
                            <div className="text-gray-500 text-xs truncate">
                              {[f.university, f.faculty, f.course ? `${f.course} курс` : ''].filter(Boolean).join(' • ')}
                            </div>
                          </div>
                        </Link>

                        <div className="flex flex-col items-end gap-2">
                          <button
                            type="button"
                            onClick={() => removeFriend(f.user_id)}
                            className="px-3 py-2 rounded-xl bg-red-900/30 text-red-300 border border-red-800/50 hover:bg-red-900/40 transition-colors flex items-center gap-2"
                            title="Удалить из друзей"
                          >
                            <FaUserMinus />
                            <span className="hidden sm:inline">Удалить</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          )}

          {tab === 'search' && (
            <div className="flex-1 bg-gray-900/80 rounded-2xl border border-gray-800 p-6 overflow-hidden flex flex-col">
              <div className="mb-4">
                <div className="relative">
                  <FaSearch className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-12 pr-10 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300"
                    placeholder="Введите имя, фамилию, никнейм, университет..."
                    minLength={1}
                    maxLength={100}
                  />
                  {searchQuery && (
                    <button
                      type="button"
                      onClick={() => clearSearch()}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
                      title="Очистить"
                    >
                      <FaTimes />
                    </button>
                  )}
                </div>

                <div className="mt-2 text-xs text-gray-500">
                  {searchQuery ? (
                    <>
                      Найдено: <span className="text-gray-300">{totalCount}</span>
                    </>
                  ) : (
                    'Начните вводить запрос — поиск пойдёт по всему приложению.'
                  )}
                </div>
              </div>

              {isSearching && (
                <div className="py-6 text-center text-gray-400">
                  <div className="inline-flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
                    Идёт поиск...
                  </div>
                </div>
              )}

              {!isSearching && searchQuery && searchError && (
                <div className="py-4 text-center text-red-400 text-sm">{searchError}</div>
              )}

              {!isSearching && searchQuery && !searchError && (
                <div className="flex-1 overflow-y-auto pr-1">
                  {filteredResults.length === 0 ? (
                    <div className="py-10 text-center text-gray-500">Ничего не найдено</div>
                  ) : (
                    <div className="space-y-3">
                      {filteredResults.map((u) => {
                        const isFriend = friendIds.has(u.user_id)
                        const hasOutgoing = pending.outgoing.some((r) => String(r.user_id) === String(u.user_id))
                        const hasIncoming = pending.incoming.some((r) => String(r.user_id) === String(u.user_id))
                        return (
                          <div
                            key={u.user_id}
                            className="bg-gray-800/30 border border-gray-700 rounded-xl p-4 hover:border-purple-600/40 transition-colors"
                          >
                            <div className="flex items-center gap-4">
                              <Link to={`/user_profile/${u.user_id}`} className="flex items-center gap-4 flex-1 min-w-0">
                                <div className="relative w-12 h-12 rounded-full overflow-hidden border border-gray-700 flex items-center justify-center bg-gradient-to-r from-blue-600 to-teal-600 text-white font-bold">
                                  {normalizeAssetUrl(u.avatar_url || u.avatar_path) ? (
                                    <img
                                      src={normalizeAssetUrl(u.avatar_url || u.avatar_path)}
                                      alt={u.username || String(u.user_id)}
                                      className="w-full h-full object-cover"
                                      onError={(e) => {
                                        e.currentTarget.style.display = 'none'
                                      }}
                                    />
                                  ) : (
                                    <span>{getInitials(u)}</span>
                                  )}
                                </div>

                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2">
                                    <div className="text-white font-semibold truncate">{getDisplayName(u)}</div>
                                    {u.course && (
                                      <span className="text-xs bg-purple-900/30 text-purple-300 px-2 py-0.5 rounded">
                                        {u.course} курс
                                      </span>
                                    )}
                                  </div>
                                  <div className="text-gray-400 text-sm truncate">{u.username ? `@${u.username}` : ''}</div>
                                  <div className="text-gray-500 text-xs truncate">
                                    {[u.university, u.faculty].filter(Boolean).join(' • ')}
                                  </div>
                                </div>
                              </Link>

                              {isFriend ? (
                                <button
                                  type="button"
                                  disabled
                                  className="px-3 py-2 rounded-xl bg-gray-800 text-gray-500 border border-gray-700 cursor-not-allowed flex items-center gap-2"
                                >
                                  <FaUserPlus />
                                  <span className="hidden sm:inline">Уже в друзьях</span>
                                </button>
                              ) : hasIncoming ? (
                                <button
                                  type="button"
                                  onClick={() => acceptRequest(u.user_id)}
                                  className="px-3 py-2 rounded-xl bg-green-700 hover:bg-green-600 text-white border border-green-600 flex items-center gap-2"
                                >
                                  <FaUserPlus />
                                  <span className="hidden sm:inline">Принять</span>
                                </button>
                              ) : hasOutgoing ? (
                                <button
                                  type="button"
                                  onClick={() => cancelRequest(u.user_id)}
                                  className="px-3 py-2 rounded-xl bg-gray-800 text-gray-300 border border-gray-700 hover:bg-gray-700 flex items-center gap-2"
                                >
                                  <FaTimes />
                                  <span className="hidden sm:inline">Отменить заявку</span>
                                </button>
                              ) : (
                                <button
                                  type="button"
                                  onClick={() => addFriend(u)}
                                  className="px-3 py-2 rounded-xl bg-purple-600 hover:bg-purple-700 text-white border border-purple-600 flex items-center gap-2"
                                >
                                  <FaUserPlus />
                                  <span className="hidden sm:inline">В друзья</span>
                                </button>
                              )}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </Header>
  )
}

