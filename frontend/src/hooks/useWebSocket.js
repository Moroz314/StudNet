import { useEffect, useRef, useState, useCallback } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { websocketService } from '../services/websocket'
import { chatAPI } from '../services/api'
import {
  messageReceived,
  messageEdited,
  messageDeleted,
  userTyping,
  userStopTyping,
  userPresence,
  chatMarkedAsRead,
  updateMessageReadStatus,
  markAllMessagesAsReadInChat,
  updateChatsFromWebSocket
} from '../store/slices/chatSlice'

export const useWebSocket = () => {
  const dispatch = useDispatch()
  const [isConnected, setIsConnected] = useState(false)
  const eventHandlersRef = useRef(new Map())
  const userIdRef = useRef(null)
  const tokenRef = useRef(null)
  const prevUserIdRef = useRef(null)
  
  const { profile } = useSelector(state => state.profile)
  const { currentChat } = useSelector(state => state.chat)
  
  const token = localStorage.getItem('token') || localStorage.getItem('access_token')
  const userId = profile?.id || profile?.user_id

  useEffect(() => {
    userIdRef.current = userId || null
    tokenRef.current = token || null
  }, [userId, token])
  
  // Функция очистки обработчиков
  const cleanupEventHandlers = useCallback(() => {
    console.log('🧹 useWebSocket: Cleaning up event handlers')
    eventHandlersRef.current.forEach((handler, event) => {
      websocketService.off(event, handler)
    })
    eventHandlersRef.current.clear()
  }, [])

  // Ставим обработчики ОДИН РАЗ на жизненный цикл хука.
  // Внутри handlers используем refs, чтобы не отписываться/подписываться на каждый ререндер.
  useEffect(() => {
    console.log('🔧 useWebSocket: Installing event handlers (once)')

    if (eventHandlersRef.current.size > 0) {
      cleanupEventHandlers()
    }

    const handlers = {
      connected: () => {
        console.log('✅ useWebSocket: Connected')
        setIsConnected(true)
      },
      disconnected: () => {
        console.log('🔌 useWebSocket: Disconnected')
        setIsConnected(false)
      },
      error: (error) => {
        console.error('❌ useWebSocket: WebSocket error', error)
      },
      pong: () => {
        // heartbeat ack, состояние не меняем
      },
      // уведомление о новом сообщении от бэкенда
      new_message: (data) => {
        console.log('📨 useWebSocket: New message received', data)
        dispatch(messageReceived(data))

        const myUserId = userIdRef.current
        dispatch(updateChatsFromWebSocket({
          chatId: data.chat_id,
          updatedChat: {
            last_message: data.content,
            last_message_time: data.created_at,
            unread_count: data.user_id !== myUserId ? 1 : 0
          }
        }))
      },
      message_edited: (data) => {
        console.log('✏️ useWebSocket: Message edited', data)
        dispatch(messageEdited(data))
      },
      message_deleted: (data) => {
        console.log('🗑️ useWebSocket: Message deleted', data)
        dispatch(messageDeleted(data))
      },
      user_typing: (data) => {
        console.log('⌨️ useWebSocket: User typing', data)
        dispatch(userTyping(data))
      },
      user_stop_typing: (data) => {
        console.log('⏹️ useWebSocket: User stopped typing', data)
        dispatch(userStopTyping(data))
      },
      user_presence: (data) => {
        console.log('👤 useWebSocket: User presence', data)
        dispatch(userPresence(data))
      },
      message_read: (data) => {
        console.log('✓ useWebSocket: Message read', data)
        if (!data?.message_id || !data?.user_id) return
        dispatch(updateMessageReadStatus({
          messageId: data.message_id,
          isRead: true,
          userId: String(data.user_id)
        }))
      },
      messages_read: (data) => {
        console.log('✓✓ useWebSocket: Messages read', data)
        if (!data?.chat_id || !data?.user_id) return

        const readMessages = data.read_messages

        if (readMessages === 'all') {
          dispatch(markAllMessagesAsReadInChat({
            chatId: data.chat_id,
            userId: String(data.user_id)
          }))
          return
        }

        if (Array.isArray(readMessages)) {
          readMessages.forEach((messageId) => {
            if (!messageId) return
            dispatch(updateMessageReadStatus({
              messageId,
              isRead: true,
              userId: String(data.user_id)
            }))
          })
        }
      },
      chat_marked_as_read: (data) => {
        console.log('✓ useWebSocket: Chat marked as read', data)
        dispatch(chatMarkedAsRead(data))
      },
      chat_created: (data) => {
        console.log('🆕 useWebSocket: Chat created', data)
        dispatch(updateChatsFromWebSocket({
          chatId: data.id,
          updatedChat: data
        }))
      }
    }

    Object.entries(handlers).forEach(([event, handler]) => {
      websocketService.on(event, handler)
      eventHandlersRef.current.set(event, handler)
    })

    return () => {
      cleanupEventHandlers()
    }
  }, [dispatch, cleanupEventHandlers])
  
  // Функция подключения
  const connect = useCallback(() => {
    const t = tokenRef.current
    const u = userIdRef.current
    if (!t || !u) {
      console.log('⏳ useWebSocket: Waiting for token or userId...')
      return false
    }
    
    console.log('🚀 useWebSocket: Connecting WebSocket...')

    // Подключаемся (обработчики уже стоят)
    websocketService.connect(u)
    
    return true
  }, [])
  
  // Функция отключения
  const disconnect = useCallback(() => {
    console.log('🧹 useWebSocket: Cleaning up WebSocket')
    
    // Удаляем все обработчики
    cleanupEventHandlers()
    
    // Отключаем WebSocket
    websocketService.disconnect()
    setIsConnected(false)
  }, [cleanupEventHandlers])
  
  // 🔥 Управление подключением: подключаемся, когда есть token + userId
  useEffect(() => {
    console.log('🔄 useWebSocket: Connection effect', { userId, hasToken: !!token })

    if (!token || !userId) return

    // если пользователь сменился — делаем чистое переподключение
    if (prevUserIdRef.current && prevUserIdRef.current !== userId) {
      websocketService.disconnect()
      setIsConnected(false)
    }
    prevUserIdRef.current = userId

    // не откладываем, чтобы после reload быстро поднималось
    connect()
  }, [token, userId, connect])

  // Reconnect-триггеры: возвращение онлайн / фокус таба
  useEffect(() => {
    const tryReconnect = () => {
      const u = userIdRef.current
      const t = tokenRef.current
      if (!u || !t) return
      if (websocketService.isConnected()) return
      websocketService.connect(u)
    }

    const onOnline = () => {
      console.log('🌐 useWebSocket: browser online -> reconnect')
      tryReconnect()
    }

    const onVisibility = () => {
      if (document.visibilityState === 'visible') {
        console.log('👁️ useWebSocket: tab visible -> reconnect')
        tryReconnect()
      }
    }

    window.addEventListener('online', onOnline)
    document.addEventListener('visibilitychange', onVisibility)

    return () => {
      window.removeEventListener('online', onOnline)
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [])
  
  useEffect(() => {
    if (currentChat?.id && isConnected) {
      console.log('useWebSocket: Auto marking chat as read:', currentChat.id)

      websocketService.markChatAsRead(currentChat.id, [], true)

      chatAPI.markChatAsRead(currentChat.id, [], true).catch((error) => {
        console.warn('Failed to mark chat as read (REST):', error)
      })
    }
  }, [currentChat, isConnected])
  
  return {
    isConnected,
    userId,
    startTyping: (chatId) => websocketService.startTyping(chatId),
    stopTyping: (chatId) => websocketService.stopTyping(chatId),
    markMessageAsRead: (messageId, chatId) => websocketService.markMessageAsRead(messageId, chatId),
    markChatAsRead: (chatId, messageIds = [], markAll = false) => websocketService.markChatAsRead(chatId, messageIds, markAll),
    connect, // 🔥 Экспортируем функцию подключения
    disconnect
  }
}