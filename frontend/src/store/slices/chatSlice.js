import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { chatAPI } from '../../services/api'

// Async thunks
export const fetchChats = createAsyncThunk(
  'chat/fetchChats',
  async () => {
    const response = await chatAPI.getChats()
    return response.data
  }
)

export const fetchMessages = createAsyncThunk(
  'chat/fetchMessages',
  async ({ chatId, limit = 50, offset = 0 }) => {
    const response = await chatAPI.getMessages(chatId, limit, offset)
    return { chatId: String(chatId), messages: response.data }
  }
)

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async ({ chatId, content, userId, replyToMessageId = null }, { rejectWithValue }) => {
    console.log('Thunk received (REST):', { chatId, content, userId, replyToMessageId })

    if (!userId) {
      return rejectWithValue(new Error('User ID is required to send message'))
    }

    try {
      const response = await chatAPI.sendTextMessage(chatId, {
        content,
        reply_to_message_id: replyToMessageId,
        message_type: 'text'
      })

      return response.data
    } catch (error) {
      console.error('❌ Error sending message via REST:', {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message
      })
      return rejectWithValue(error)
    }
  }
)

export const createChat = createAsyncThunk(
  'chat/createChat',
  async (chatData, { rejectWithValue, getState }) => {
    try {
      console.log(' Thunk получил данные:', chatData);
      console.log(' Проверяем структуру:', {
        hasData: 'data' in chatData,
        dataType: typeof chatData.data,
        dataKeys: chatData.data ? Object.keys(chatData.data) : 'no data',
        hasMembers: 'members' in chatData,
        membersType: chatData.members ? typeof chatData.members : 'no members'
      });
      
      // ВАЖНО: Проверяем формат данных перед отправкой
      const requestData = {
        data: {
          name: chatData.data.name.trim(),
          type: chatData.data.type, 
        }
      };
      
      // Добавляем members только если они есть и не пустые
      if (chatData.members && Array.isArray(chatData.members) && chatData.members.length > 0) {
        requestData.members = chatData.members;
      }
      
      console.log(' Отправляю на сервер:', JSON.stringify(requestData, null, 2));
      
      const response = await chatAPI.createChat(requestData);
      console.log(' Ответ сервера:', response.data);
      return response.data;
      
    } catch (error) {
      console.error(' Ошибка в thunk:', {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message
      });
      
      // Возвращаем более подробную ошибку
      return rejectWithValue({
        message: error.response?.data?.detail?.[0]?.msg || 
                error.response?.data?.message || 
                'Ошибка создания чата',
        details: error.response?.data?.detail,
        status: error.response?.status,
        code: error.code || 'NETWORK_ERROR'
      });
    }
  }
);

const chatSlice = createSlice({
  name: 'chat',
  initialState: {
    chats: [],
    currentChat: null,
    messages: {},
    typingUsers: {},
    onlineUsers: {},
    loading: false,
    error: null
  },
  reducers: {
    
    setCurrentChat: (state, action) => {
      state.currentChat = action.payload
    },
updateChatsFromWebSocket: (state, action) => {
  const { chatId, updatedChat } = action.payload
  
  // Находим индекс чата
  const chatIndex = state.chats.findIndex(chat => chat.id === chatId)
  
  if (chatIndex !== -1) {
    // ОБНОВЛЯЕМ СУЩЕСТВУЮЩИЙ ЧАТ
    const existingChat = state.chats[chatIndex]
    
    // Сохраняем unread_count если он не передан
    const newUnreadCount = updatedChat.unread_count !== undefined 
      ? updatedChat.unread_count 
      : existingChat.unread_count
    
    // Обновляем чат
    state.chats[chatIndex] = {
      ...existingChat,
      ...updatedChat,
      unread_count: newUnreadCount
    }
    
    // СОРТИРУЕМ: чаты с последними сообщениями - вверху
    state.chats.sort((a, b) => {
      const timeA = new Date(a.last_message_time || a.created_at || 0).getTime()
      const timeB = new Date(b.last_message_time || b.created_at || 0).getTime()
      return timeB - timeA // Новые сверху
    })
    
  } else if (updatedChat) {
    // ДОБАВЛЯЕМ НОВЫЙ ЧАТ если его нет в списке
    console.log(' Adding new chat to list:', updatedChat)
    state.chats.unshift({
      ...updatedChat,
      unread_count: updatedChat.unread_count || 0
    })
  }
  
  // ОБНОВЛЯЕМ ТЕКУЩИЙ ЧАТ если нужно
  if (state.currentChat?.id === chatId) {
    state.currentChat = {
      ...state.currentChat,
      ...updatedChat
    }
  }
},
    
    // WebSocket events
    messageReceived: (state, action) => {
      const message = action.payload
      const chatKey = String(message.chat_id)
      
      // 🔥 Проверяем на дубликаты по ID сообщения
      if (state.messages[chatKey]) {
        const existingMessage = state.messages[chatKey].find(msg => msg.id === message.id)
        if (existingMessage) {
          console.log('⚠️ Duplicate message detected, skipping:', message.id)
          return // Пропускаем дубликат
        }
        
        // Удаляем оптимистичное сообщение если есть
        state.messages[chatKey] = state.messages[chatKey].filter(
          msg => !msg.isPending || msg.content !== message.content
        )
      }
      
      // Добавляем сообщение
      if (!state.messages[chatKey]) {
        state.messages[chatKey] = []
      }
      
      state.messages[chatKey].push(message)
      console.log('новое сообщение')
      // Обновляем last_message в чате
      const chat = state.chats.find(c => c.id === message.chat_id)
      if (chat) {
        chat.last_message = message.content
        chat.last_message_time = message.created_at
        chat.unread_count = (chat.unread_count || 0) + 1
      }
    },
    
    messageEdited: (state, action) => {
      const message = action.payload
      const chatMessages = state.messages[String(message.chat_id)]
      
      if (chatMessages) {
        const index = chatMessages.findIndex(m => m.id === message.id)
        if (index !== -1) {
          chatMessages[index] = message
        }
      }
    },
    
    messageDeleted: (state, action) => {
      const { message_id, chat_id } = action.payload
      const chatMessages = state.messages[String(chat_id)]
      
      if (chatMessages) {
        state.messages[String(chat_id)] = chatMessages.filter(m => m.id !== message_id)
      }
    },
    userTyping: (state, action) => {
      const { user_id, chat_id } = action.payload
      
      if (!state.typingUsers[String(chat_id)]) {
        // ИСПОЛЬЗУЕМ ОБЫЧНЫЙ МАССИВ
        state.typingUsers[String(chat_id)] = []
      }
      
      // Добавляем пользователя если его еще нет
      if (!state.typingUsers[String(chat_id)].includes(user_id)) {
        state.typingUsers[String(chat_id)].push(user_id)
      }
    },
    
    // ИСПРАВЛЕННЫЙ userStopTyping
    userStopTyping: (state, action) => {
      const { user_id, chat_id } = action.payload
      
      if (state.typingUsers[String(chat_id)]) {
        // УДАЛЯЕМ ПОЛЬЗОВАТЕЛЯ ИЗ МАССИВА
        state.typingUsers[String(chat_id)] = state.typingUsers[String(chat_id)]
          .filter(id => id !== user_id)
        
        // Удаляем пустой массив
        if (state.typingUsers[String(chat_id)].length === 0) {
          delete state.typingUsers[String(chat_id)]
        }
      }
    },
    
    userPresence: (state, action) => {
      const { user_id, status } = action.payload
      state.onlineUsers[user_id] = status
    },
    
    chatMarkedAsRead: (state, action) => {
      const { chat_id, user_id } = action.payload
      const chat = state.chats.find(c => c.id === chat_id)
      
      if (chat) {
        chat.unread_count = 0
      }
    },
    
    // 
    updateMessageReadStatus: (state, action) => {
      const { messageId, isRead, userId } = action.payload
      
      // 
      Object.entries(state.messages).forEach(([chatId, messages]) => {
        const messageIndex = messages.findIndex(m => m.id === messageId)
        if (messageIndex !== -1) {
          messages[messageIndex].is_read = isRead
          messages[messageIndex].read_at = isRead ? new Date().toISOString() : null
          
          // Обновляем read_by для немедленной реакции UI
          if (!messages[messageIndex].read_by) {
            messages[messageIndex].read_by = {}
          }
          messages[messageIndex].read_by[userId] = isRead
        }
      })
    },
    
    markMessageAsRead: (state, action) => {
      const { messageId, userId } = action.payload
      
      // 
      Object.entries(state.messages).forEach(([chatId, messages]) => {
        const messageIndex = messages.findIndex(m => m.id === messageId)
        if (messageIndex !== -1) {
          if (!messages[messageIndex].read_by) {
            messages[messageIndex].read_by = {}
          }
          messages[messageIndex].read_by[userId] = true
          messages[messageIndex].is_read = true
          messages[messageIndex].read_at = new Date().toISOString()
        }
      })
    },
    
    markAllMessagesAsReadInChat: (state, action) => {
      const { chatId, userId } = action.payload
      const chatKey = String(chatId)
      const messages = state.messages[chatKey]
      if (!messages) return

      messages.forEach((m) => {
        if (!m.read_by) {
          m.read_by = {}
        }
        m.read_by[String(userId)] = true
        m.is_read = true
        m.read_at = new Date().toISOString()
      })
    },
    
    clearError: (state) => {
      state.error = null
    },
    
    clearChatMessages: (state, action) => {
      const chatId = String(action.payload)
      if (state.messages[chatId]) {
        state.messages[chatId] = []
      }
    },
    setMessagesForChat: (state, action) => {
      const { chatId, messages } = action.payload
      state.messages[String(chatId)] = Array.isArray(messages) ? messages : []
    },
    updateMessageLikeState: (state, action) => {
      const { chatId, messageId, isLiked } = action.payload
      const key = String(chatId)
      const list = state.messages[key]
      if (!Array.isArray(list)) return
      const idx = list.findIndex((m) => String(m.id) === String(messageId))
      if (idx === -1) return
      const msg = list[idx]
      const prevLiked = !!msg.is_liked_by_user
      let likesCount = Number(msg.likes_count || 0)
      if (isLiked && !prevLiked) likesCount += 1
      if (!isLiked && prevLiked) likesCount = Math.max(0, likesCount - 1)
      list[idx] = {
        ...msg,
        is_liked_by_user: isLiked,
        likes_count: likesCount,
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch Chats
      .addCase(fetchChats.pending, (state) => {
        state.loading = true
      })
// В extraReducers для fetchChats.fulfilled
      .addCase(fetchChats.fulfilled, (state, action) => {
        state.loading = false
        // Обрабатываем названия приватных чатов
        const chatsWithNames = action.payload.map(chat => {
          if (chat.type === 'private') {
            // Название уже должно быть установлено на бэкенде
            // но можно дополнительно обработать здесь
            return {
              ...chat,
              displayName: chat.name || `Приватный чат`
            }
          }
          return chat
        })
        state.chats = chatsWithNames
        state.error = null
      })
      .addCase(fetchChats.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message
      })
      
      // Fetch Messages
      .addCase(fetchMessages.fulfilled, (state, action) => {
        const { chatId, messages } = action.payload
        state.messages[String(chatId)] = messages
      })
      
      // Send Message (optimistic update)
      .addCase(sendMessage.fulfilled, (state, action) => {
        const message = action.payload
        const chatKey = String(message.chat_id)
        if (!state.messages[chatKey]) {
          state.messages[chatKey] = []
        }
        state.messages[chatKey].push(message)
      })
  }
})

export const {
  setCurrentChat,
  messageReceived,
  messageEdited,
  messageDeleted,
  userTyping,
  userStopTyping,
  userPresence,
  updateChatsFromWebSocket,
  chatMarkedAsRead,
  markMessageAsRead,
  markAllMessagesAsReadInChat,
  updateMessageReadStatus,
  clearError,
  clearChatMessages,
  setMessagesForChat,
  updateMessageLikeState
} = chatSlice.actions

export default chatSlice.reducer