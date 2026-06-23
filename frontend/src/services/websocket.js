class WebSocketService {
  constructor() {
    this.socket = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectInterval = 3000
    this.reconnectDelayMultiplier = 1.5
    this.eventCallbacks = {}
    this.baseURL = import.meta.env.VITE_WS_URL || 'ws://45.11.92.114:8000'
    this.isManuallyDisconnecting = false
    this.currentUserId = null // Храним текущего пользователя
    this.lastConnectTime = 0
    this.minConnectInterval = 5000 // Увеличенный минимальный интервал

    this._pendingConnectTimer = null
    this._reconnectTimer = null

    this.heartbeatIntervalMs = 25000
    this.pongTimeoutMs = 65000
    this._heartbeatTimer = null
    this._pongWatchTimer = null
    this._lastPongAt = 0
  }

  _clearTimers() {
    if (this._pendingConnectTimer) {
      clearTimeout(this._pendingConnectTimer)
      this._pendingConnectTimer = null
    }
    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer)
      this._reconnectTimer = null
    }
    if (this._heartbeatTimer) {
      clearInterval(this._heartbeatTimer)
      this._heartbeatTimer = null
    }
    if (this._pongWatchTimer) {
      clearInterval(this._pongWatchTimer)
      this._pongWatchTimer = null
    }
  }

  _startHeartbeat() {
    this._lastPongAt = Date.now()

    this._heartbeatTimer = setInterval(() => {
      // браузерные ping/pong фреймы недоступны, делаем app-level ping
      this.send('ping', { ts: Date.now() })
    }, this.heartbeatIntervalMs)

    this._pongWatchTimer = setInterval(() => {
      if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return
      const age = Date.now() - this._lastPongAt
      if (age > this.pongTimeoutMs) {
        console.warn('⚠️ WebSocket heartbeat timeout, closing socket', { age })
        try {
          this.socket.close(4001, 'Heartbeat timeout')
        } catch (e) {
          // ignore
        }
      }
    }, Math.max(5000, Math.floor(this.heartbeatIntervalMs / 2)))
  }


connect(userId) {
    if (!userId) {
      console.error(' User ID is required for WebSocket connection')
      return
    }

    const token = localStorage.getItem('token') ||
                  localStorage.getItem('access_token')

    if (!token) {
      console.error('❌ No token found for WebSocket connection')
      return
    }
    
    // ПРОВЕРКА: Если уже подключаемся для этого пользователя - выходим
    if (this.currentUserId === userId && 
      this.socket && 
      (this.socket.readyState === WebSocket.OPEN || 
       this.socket.readyState === WebSocket.CONNECTING)) {
      console.log(' WebSocket: Already connected/connecting for this user')
      return
    }
    
    const now = Date.now()
    const timeSinceLastConnect = now - this.lastConnectTime
    
    // Увеличиваем интервал и делаем проверку более строгой
    if (timeSinceLastConnect < this.minConnectInterval && this.lastConnectTime > 0) {
      const waitTime = this.minConnectInterval - timeSinceLastConnect
      console.log(` WebSocket: Too many connection attempts, waiting ${waitTime}ms...`)
      if (this._pendingConnectTimer) clearTimeout(this._pendingConnectTimer)
      this._pendingConnectTimer = setTimeout(() => this.connect(userId), waitTime)
      return
    }
    
    this.lastConnectTime = now
  
    // Сохраняем ID пользователя
    this.currentUserId = userId
    
    // Если уже подключаемся - выходим
    if (this.socket && this.socket.readyState === WebSocket.CONNECTING) {
      console.log('⏳ WebSocket is already connecting, skipping...')
      return
    }
    
    // Если уже подключены - проверяем, тот же ли пользователь
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      console.log('✅ WebSocket already connected')
      return
    }
    
    console.log('🔧 WebSocketService: Connecting for user', userId)
    
    try {
      this.isManuallyDisconnecting = false
      const ua = (typeof navigator !== 'undefined' && navigator.userAgent) ? navigator.userAgent : 'unknown'
      const wsUrl = `${this.baseURL}/ws?token=${encodeURIComponent(token)}&user_agent=${encodeURIComponent(ua)}`
      
      this.socket = new WebSocket(wsUrl)
      
      this.socket.onopen = () => {
        console.log('✅ WebSocket connected successfully for user', userId)
        this.reconnectAttempts = 0
        this.lastConnectTime = 0 // Сбрасываем время для будущих подключений
        this._clearTimers()
        this._startHeartbeat()
        this.emit('connected', { userId })
      }
      
      this.socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          console.log('📨 WebSocket received:', message)

          if (message?.event === 'pong') {
            this._lastPongAt = Date.now()
          }
          
          if (message.event) {
            this.emit(message.event, message.data || message)
          } else if (message.type) {
            this.emit(message.type, message)
          } else {
            this.emit('message', message)
          }
        } catch (error) {
          console.error('❌ Error parsing WebSocket message:', error)
        }
      }
      
      this.socket.onclose = (event) => {
        console.log('🔌 WebSocket closed:', {
          code: event.code,
          reason: event.reason,
          wasClean: event.wasClean,
          currentUserId: this.currentUserId
        })

        this._clearTimers()
        
        this.emit('disconnected', event)
        
        // Автоматическое переподключение
        if (!this.isManuallyDisconnecting && 
            this.reconnectAttempts < this.maxReconnectAttempts &&
            this.currentUserId) { // 🔥 Проверяем что пользователь еще существует
          
          this.reconnectAttempts++
          const delay = Math.min(
            this.reconnectInterval * Math.pow(this.reconnectDelayMultiplier, this.reconnectAttempts - 1),
            30000
          )
          
          console.log(`🔄 Reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`)
          
          if (this._reconnectTimer) clearTimeout(this._reconnectTimer)
          this._reconnectTimer = setTimeout(() => {
            this.connect(this.currentUserId) // 🔥 Используем сохраненного пользователя
          }, delay)
        }
      }
      
      this.socket.onerror = (error) => {
        console.error('❌ WebSocket error:', error)
        this.emit('error', error)
      }
      
    } catch (error) {
      console.error('❌ WebSocket connection failed:', error)
    }
  }

  handleReconnect(userId) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      
      // Exponential backoff
      const delay = Math.min(
        this.reconnectInterval * Math.pow(this.reconnectDelayMultiplier, this.reconnectAttempts - 1),
        30000 // Максимум 30 секунд
      )
      
      console.log(`🔄 Reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`)
      
      setTimeout(() => {
        this.connect(userId)
      }, delay)
    } else {
      console.error('❌ Max reconnection attempts reached')
      this.emit('reconnect_failed', { userId, attempts: this.reconnectAttempts })
    }
  }

  send(event, data) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      try {
        const message = JSON.stringify({ event, data })
        this.socket.send(message)
        return true
      } catch (error) {
        console.error('❌ Error sending WebSocket message:', error)
        return false
      }
    } else {
      console.warn('⚠️ WebSocket not ready. State:', this.socket?.readyState)
      return false
    }
  }

  startTyping(chatId) {
    return this.send('user_typing', { chat_id: chatId })
  }

  stopTyping(chatId) {
    return this.send('user_stop_typing', { chat_id: chatId })
  }

  markMessageAsRead(messageId, chatId) {
    return this.send('message_read', { message_id: messageId, chat_id: chatId })
  }

  markChatAsRead(chatId, messageIds = [], markAll = false) {
    return this.send('messages_read', {
      chat_id: chatId,
      messages_read: messageIds,
      mark_all: markAll
    })
  }

  getPresence(userId) {
    return this.send('get_presence', { user_id: userId })
  }

  // Управление событиями
  on(event, callback) {
    if (!this.eventCallbacks[event]) {
      this.eventCallbacks[event] = []
    }
    this.eventCallbacks[event].push(callback)
  }

  off(event, callback) {
    if (this.eventCallbacks[event]) {
      this.eventCallbacks[event] = this.eventCallbacks[event].filter(cb => cb !== callback)
    }
  }

  emit(event, data) {
    if (this.eventCallbacks[event]) {
      this.eventCallbacks[event].forEach(callback => callback(data))
    }
  }

  // Отключение
disconnect() {
    console.log(' WebSocketService: Manual disconnect requested')
    
    this.isManuallyDisconnecting = true
    this.currentUserId = null // Сбрасываем пользователя
    this.reconnectAttempts = 0
    this.lastConnectTime = 0 // Сбрасываем время подключения
    this._clearTimers()
    
    if (this.socket) {
      try {
        // Сохраняем ссылку на обработчик onclose
        const existingOnClose = this.socket.onclose
        
        // Устанавливаем временный обработчик
        this.socket.onclose = (event) => {
          console.log(' WebSocket closed during manual disconnect')
          if (existingOnClose) {
            existingOnClose.call(this.socket, event)
          }
        }
        
        // Закрываем соединение
        if (this.socket.readyState === WebSocket.OPEN) {
          this.socket.close(1000, 'Client disconnected')
        } else if (this.socket.readyState === WebSocket.CONNECTING) {
          this.socket.close()
        }
        
      } catch (error) {
        console.error(' Error during WebSocket disconnect:', error)
      } finally {
        // Даем время на закрытие перед очисткой
        setTimeout(() => {
          this.socket = null
          this.emit('disconnected', { manual: true })
        }, 100)
      }
    }
    
    // Очищаем все обработчики
    this.eventCallbacks = {}
  }
  isConnected() {
    return this.socket && this.socket.readyState === WebSocket.OPEN
  }
  
  getConnectionState() {
    return this.socket ? this.socket.readyState : WebSocket.CLOSED
  }

  subscribeToChatEvents() {
    return this.send('subscribe_to_chats', {})   
  }
}

// Singleton
export const websocketService = new WebSocketService()