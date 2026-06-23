import React, { useEffect, useMemo, useState } from 'react'
import Header from '../ui/Header'
import { GoBell, GoCheck, GoClock, GoProject, GoPerson, GoAlert } from 'react-icons/go'
import { projectsAPI, relationshipsAPI } from '../services/api'

function formatRuDateTime(value) {
  try {
    return new Date(value).toLocaleString('ru-RU')
  } catch {
    return ''
  }
}

const typeMeta = {
  project: {
    label: 'Проекты',
    icon: GoProject,
    color: 'text-blue-400',
    bg: 'bg-blue-900/30',
  },
  task: {
    label: 'Задачи',
    icon: GoCheck,
    color: 'text-emerald-400',
    bg: 'bg-emerald-900/30',
  },
  friend: {
    label: 'Друзья',
    icon: GoPerson,
    color: 'text-purple-400',
    bg: 'bg-purple-900/30',
  },
  system: {
    label: 'Система',
    icon: GoAlert,
    color: 'text-amber-400',
    bg: 'bg-amber-900/30',
  },
}

export default function Notifications() {
  const [filter, setFilter] = useState('all') // all | unread | project | task | friend | system
  const [invitations, setInvitations] = useState([])
  const [friendRequests, setFriendRequests] = useState({ incoming: [], outgoing: [] })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [responding, setResponding] = useState({}) // { [invId]: true }

  const loadInvitations = async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await projectsAPI.getMyProjectInvitations('pending')
      setInvitations(Array.isArray(data) ? data : [])
    } catch (e) {
      setError(e?.data || e?.message || 'Ошибка загрузки приглашений')
      setInvitations([])
    } finally {
      setLoading(false)
    }
  }

  const loadFriendRequests = async () => {
    try {
      const { data } = await relationshipsAPI.getPendingRequests()
      const incoming = data?.incoming || []
      const outgoing = data?.outgoing || []
      setFriendRequests({ incoming, outgoing })
    } catch (e) {
      console.error('Error loading friend requests:', e)
    }
  }

  useEffect(() => {
    loadInvitations()
    loadFriendRequests()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleRespond = async (invitationId, action) => {
    setResponding((prev) => ({ ...prev, [invitationId]: true }))
    try {
      await projectsAPI.respondToProjectInvitation(invitationId, action)
      setInvitations((prev) => prev.filter((i) => i.id !== invitationId))
    } catch (e) {
      setError(e?.data || e?.message || 'Не удалось отправить ответ на приглашение')
    } finally {
      setResponding((prev) => {
        const next = { ...prev }
        delete next[invitationId]
        return next
      })
    }
  }

  const handleFriendRespond = async (userId, action) => {
    try {
      if (action === 'accept') {
        await relationshipsAPI.acceptFriendRequest(userId)
      } else if (action === 'reject') {
        await relationshipsAPI.rejectFriendRequest(userId)
      }
      // обновляем список заявок
      await loadFriendRequests()
    } catch (e) {
      console.error('Error responding to friend request:', e)
    }
  }

  const notifications = useMemo(() => {
    const projectInvites = invitations.map((inv) => {
      const inviterName = [inv?.inviter?.name, inv?.inviter?.lastname].filter(Boolean).join(' ').trim()
      const inviterUser = inv?.inviter?.username ? `@${inv.inviter.username}` : ''
      const msg = inv?.message ? `\nСообщение: ${inv.message}` : ''

      return {
        id: `inv-${inv.id}`,
        type: 'project',
        title: 'Приглашение в проект',
        description: `${inviterName || 'Пользователь'} ${inviterUser} приглашает вас в проект.${msg}`.trim(),
        time: formatRuDateTime(inv?.invited_at),
        isRead: false,
        invitation: inv,
      }
    })

    const friendNotifs = friendRequests.incoming.map((req) => {
      const fromName = [req?.user?.name, req?.user?.lastname].filter(Boolean).join(' ').trim()
      const fromUser = req?.user?.username ? `@${req.user.username}` : ''

      return {
        id: `friend-${req.user_id}`,
        type: 'friend',
        title: 'Заявка в друзья',
        description: `${fromName || 'Пользователь'} ${fromUser} хочет добавить вас в друзья`.trim(),
        time: formatRuDateTime(req?.created_at || req?.sent_at || new Date().toISOString()),
        isRead: false,
        friendRequest: req,
      }
    })

    return [...projectInvites, ...friendNotifs]
  }, [invitations, friendRequests])

  const unreadCount = useMemo(
    () => notifications.filter((n) => !n.isRead).length,
    [notifications]
  )

  const filtered = useMemo(() => {
    return notifications.filter((n) => {
      if (filter === 'all') return true
      if (filter === 'unread') return !n.isRead
      return n.type === filter
    })
  }, [filter, notifications])

  return (
    <Header>
      <div className="bg-white dark:bg-black p-3 sm:p-4 md:p-6 page-viewport">
        <div className="max-w-5xl mx-auto h-full flex flex-col min-h-0">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4 mb-4 sm:mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-purple-600/10 border border-purple-500/40 flex items-center justify-center">
                <GoBell className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-black dark:text-white">
                  Уведомления
                </h1>
                
              </div>
            </div>

            <div className="text-right">
              <div className="text-xs uppercase tracking-wide text-gray-500 mb-1">
                Непрочитанные
              </div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-900/20 border border-purple-700/60">
                <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
                <span className="text-sm text-purple-200 font-medium">
                  {unreadCount}
                </span>
              </div>
            </div>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-xl border border-red-700 bg-red-900/20 text-red-200 text-sm flex items-center justify-between gap-3">
              <span className="min-w-0 truncate">
                {typeof error === 'string' ? error : error?.detail || 'Ошибка'}
              </span>
              <button
                onClick={loadInvitations}
                className="px-3 py-1.5 rounded-lg bg-red-700/40 hover:bg-red-700/60 border border-red-600/60 text-xs text-white"
              >
                Обновить
              </button>
            </div>
          )}

          <div className="mb-4 flex flex-wrap gap-2">
            <button
              onClick={() => setFilter('all')}
              className={[
                'px-3 py-1.5 rounded-full text-xs font-medium border transition-colors',
                filter === 'all'
                  ? 'bg-purple-600 text-white border-purple-600'
                  : 'bg-gray-900/40 text-gray-300 border-gray-700 hover:border-purple-500/60',
              ].join(' ')}
            >
              Все
            </button>
            <button
              onClick={() => setFilter('unread')}
              className={[
                'px-3 py-1.5 rounded-full text-xs font-medium border transition-colors',
                filter === 'unread'
                  ? 'bg-purple-600 text-white border-purple-600'
                  : 'bg-gray-900/40 text-gray-300 border-gray-700 hover:border-purple-500/60',
              ].join(' ')}
            >
              Непрочитанные
            </button>
            {['project', 'task', 'friend', 'system'].map((key) => {
              const meta = typeMeta[key]
              const Icon = meta.icon
              return (
                <button
                  key={key}
                  onClick={() => setFilter(key)}
                  className={[
                    'px-3 py-1.5 rounded-full text-xs font-medium border transition-colors inline-flex items-center gap-1.5',
                    filter === key
                      ? 'bg-purple-600 text-white border-purple-600'
                      : 'bg-gray-900/40 text-gray-300 border-gray-700 hover:border-purple-500/60',
                  ].join(' ')}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {meta.label}
                </button>
              )
            })}
          </div>

          <div className="flex-1 overflow-y-auto pr-1">
            {loading ? (
              <div className="h-full flex flex-col items-center justify-center text-center text-gray-500">
                <div className="text-sm">Загрузка приглашений…</div>
              </div>
            ) : filtered.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center text-gray-500">
                <div className="mb-3">
                  <GoCheck className="w-10 h-10 mx-auto text-emerald-400" />
                </div>
                <div className="text-lg font-semibold mb-1 text-gray-200">
                  Все спокойно
                </div>
                <div className="text-sm max-w-sm">
                  Для выбранного фильтра нет уведомлений. Приглашения в проекты появятся здесь, чтобы их можно было принять.
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {filtered.map((n) => {
                  const meta = typeMeta[n.type]
                  const Icon = meta.icon
                  const inv = n.invitation
                  const fr = n.friendRequest
                  const canRespondProject = Boolean(inv?.id)
                  const canRespondFriend = Boolean(fr?.user_id)
                  const isBusy = Boolean(inv?.id && responding[inv.id])

                  return (
                    <div
                      key={n.id}
                      className={[
                        'relative rounded-2xl border px-4 py-3 bg-gray-900/70 hover:border-purple-500/60 transition-all duration-200',
                        n.isRead ? 'border-gray-800' : 'border-purple-600/70',
                      ].join(' ')}
                    >
                      {!n.isRead && (
                        <span className="absolute -left-1 -top-1 w-3 h-3 rounded-full bg-purple-500 shadow-[0_0_10px_rgba(168,85,247,0.8)]" />
                      )}

                      <div className="flex items-start gap-3">
                        <div
                          className={[
                            'mt-1 w-9 h-9 rounded-xl flex items-center justify-center border',
                            meta.bg,
                            n.isRead ? 'border-gray-700' : 'border-purple-600/70',
                          ].join(' ')}
                        >
                          <Icon className={`w-4 h-4 ${meta.color}`} />
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-2 mb-1">
                            <h3 className="text-sm font-semibold text-white truncate">
                              {n.title}
                            </h3>
                            <div className="flex items-center gap-1 text-xs text-gray-400 flex-shrink-0">
                              <GoClock className="w-3 h-3" />
                              <span>{n.time}</span>
                            </div>
                          </div>
                          <p className="text-sm text-gray-300 break-words">
                            {n.description}
                          </p>

                          {canRespondProject && (
                            <div className="mt-3 flex flex-wrap gap-2">
                              <button
                                onClick={() => handleRespond(inv.id, 'accept')}
                                disabled={isBusy}
                                className="px-3 py-1.5 rounded-lg bg-emerald-700/40 hover:bg-emerald-700/60 border border-emerald-600/60 text-xs text-white disabled:opacity-50"
                              >
                                Принять
                              </button>
                              <button
                                onClick={() => handleRespond(inv.id, 'reject')}
                                disabled={isBusy}
                                className="px-3 py-1.5 rounded-lg bg-gray-700/50 hover:bg-gray-700/70 border border-gray-600/60 text-xs text-white disabled:opacity-50"
                              >
                                Отклонить
                              </button>
                            </div>
                          )}

                          {canRespondFriend && (
                            <div className="mt-3 flex flex-wrap gap-2">
                              <button
                                onClick={() => handleFriendRespond(fr.user_id, 'accept')}
                                className="px-3 py-1.5 rounded-lg bg-emerald-700/40 hover:bg-emerald-700/60 border border-emerald-600/60 text-xs text-white"
                              >
                                Принять
                              </button>
                              <button
                                onClick={() => handleFriendRespond(fr.user_id, 'reject')}
                                className="px-3 py-1.5 rounded-lg bg-gray-700/50 hover:bg-gray-700/70 border border-gray-600/60 text-xs text-white"
                              >
                                Отклонить
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </Header>
  )
}

