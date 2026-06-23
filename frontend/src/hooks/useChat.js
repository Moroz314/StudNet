// hooks/useChat.js - ПОЛНАЯ ВЕРСИЯ С КОНТЕКСТНЫМ МЕНЮ
import { useDispatch, useSelector } from 'react-redux';
import { useCallback, useMemo, useEffect, useRef } from 'react';
import { useWebSocket } from './useWebSocket'
import { chatAPI, channelAPI } from '../services/api'
import {
  fetchChats,
  fetchMessages,
  sendMessage as sendMessageAction,
  setCurrentChat,
  updateChatsFromWebSocket,
  messageEdited,
  messageDeleted,
  updateMessageReadStatus,
  setMessagesForChat,
} from '../store/slices/chatSlice'

export const useChat = () => {
  const dispatch = useDispatch()
  const chatState = useSelector(state => state.chat)
  const { profile, isLoading: profileLoading } = useSelector(state => state.profile)
  
  const loadedRef = useRef(false)
  const lastUserIdRef = useRef(null)
  const wsConnectionAttemptedRef = useRef(false)
  
  // 🔥 ВАЖНО: useWebSocket вызываем БЕЗ параметров
  const ws = useWebSocket()

  console.log('🔍 useChat: Current state', {
    hasProfile: !!profile,
    profileId: profile?.id || profile?.user_id,
    chatsCount: chatState.chats?.length || 0,
    currentChatId: chatState.currentChat?.id,
    profileLoading,
    wsConnected: ws.isConnected,
    lastUserId: lastUserIdRef.current
  })

  // 🔥 ФУНКЦИЯ ЗАГРУЗКИ ЧАТОВ
  const loadChats = useCallback(() => {
    const userId = profile?.id || profile?.user_id
    
    if (!userId) {
      console.log('⏭️ useChat: Skipping loadChats - no user ID')
      return
    }
    
    // Если уже загружали для этого пользователя - пропускаем
    if (loadedRef.current && lastUserIdRef.current === userId) {
      console.log('⏭️ useChat: Chats already loaded for this user')
      return
    }
    
    console.log('🔄 Loading chats for user:', userId)
    loadedRef.current = true
    lastUserIdRef.current = userId
    dispatch(fetchChats())
  }, [dispatch, profile?.id, profile?.user_id])

  // 🔥 ФУНКЦИЯ ЗАГРУЗКИ СООБЩЕНИЙ
  const loadMessages = useCallback(async (chatId, limit = 50, offset = 0, chatType = null) => {
    if (!chatId) {
      console.error('❌ Chat ID is required to load messages')
      return
    }
    console.log('📥 Loading messages for chat:', chatId, 'type:', chatType)
    if (chatType === 'channel') {
      const response = await channelAPI.getMessages(chatId, limit, offset)
      const payload = response?.data
      const channelMessages = Array.isArray(payload) ? payload : (payload?.messages || [])
      dispatch(setMessagesForChat({ chatId, messages: channelMessages }))
      return
    }
    dispatch(fetchMessages({ chatId, limit, offset }))
  }, [dispatch])

  // 🔥 ФУНКЦИЯ ОТПРАВКИ СООБЩЕНИЯ (HTTP + REST)
  const sendMessageToChat = useCallback((chatId, content, replyToMessageId = null, chatType = null) => {
    console.log('📤 sendMessageToChat called:', { chatId, content, replyToMessageId });
    
    const userId = profile?.id || profile?.user_id;
    
    if (!chatId || !content || !userId) {
      console.error('❌ Missing required data for sending message:', {
        chatId,
        content,
        userId
      });
      return Promise.reject(new Error('Missing required data for sending message'));
    }
    
    console.log('📤 Sending message to chat:', { chatId, content, userId, replyToMessageId });
    
    if (chatType === 'channel') {
      return channelAPI.sendTextMessage(chatId, content)
        .then((response) => {
          const sent = response?.data
          if (sent) {
            const prev = chatState.messages[String(chatId)] || []
            dispatch(setMessagesForChat({ chatId, messages: [...prev, sent] }))
          }
          return sent
        })
    }

    return dispatch(sendMessageAction({ 
      chatId, 
      content, 
      userId,
      replyToMessageId
    })).unwrap().then((optimisticMessage) => {
      console.log('✅ Message sent (optimistic):', optimisticMessage);
      return optimisticMessage;
    }).catch(error => {
      console.error('❌ Error sending message:', error);
      throw error;
    });
  }, [dispatch, profile, chatState.messages])

  // 🔥 ФУНКЦИЯ РЕДАКТИРОВАНИЯ СООБЩЕНИЯ
  const editMessage = useCallback((messageId, newContent) => {
    console.log('✏️ useChat: Editing message:', { messageId, newContent });
    
    if (!messageId || !newContent?.trim()) {
      console.error('❌ Missing data for editing message');
      return Promise.reject(new Error('Missing data for editing message'));
    }
    
    if (!ws.isConnected) {
      console.error('❌ WebSocket not connected for editing');
      return Promise.reject(new Error('WebSocket not connected'));
    }
    
    // Отправляем через WebSocket
    const success = ws.editMessage(messageId, newContent);
    
    if (!success) {
      return Promise.reject(new Error('Failed to send edit request'));
    }
    
    // Оптимистичное обновление в Redux
    const messageToEdit = Object.values(chatState.messages)
      .flat()
      .find(msg => msg.id === messageId);
    
    if (messageToEdit) {
      const optimisticMessage = {
        ...messageToEdit,
        content: newContent,
        is_edited: true,
        edited_at: new Date().toISOString()
      };
      
      dispatch(messageEdited(optimisticMessage));
    }
    
    return Promise.resolve({ 
      success: true, 
      messageId, 
      content: newContent 
    });
  }, [dispatch, ws, chatState.messages]);

  // 🔥 ФУНКЦИЯ УДАЛЕНИЯ СООБЩЕНИЯ
  const deleteMessage = useCallback((messageId) => {
    console.log('🗑️ useChat: Deleting message:', messageId);
    
    if (!messageId) {
      console.error('❌ Missing message ID for deletion');
      return Promise.reject(new Error('Missing message ID'));
    }
    
    if (!ws.isConnected) {
      console.error('❌ WebSocket not connected for deletion');
      return Promise.reject(new Error('WebSocket not connected'));
    }
    
    // Отправляем через WebSocket
    const success = ws.deleteMessage(messageId);
    
    if (!success) {
      return Promise.reject(new Error('Failed to send delete request'));
    }
    
    // Оптимистичное обновление в Redux
    let deletedMessageData = null;
    
    // Находим сообщение для удаления
    Object.entries(chatState.messages).forEach(([chatId, messages]) => {
      const messageIndex = messages.findIndex(msg => msg.id === messageId);
      if (messageIndex !== -1) {
        deletedMessageData = { 
          chatId, 
          message: messages[messageIndex] 
        };
      }
    });
    
    if (deletedMessageData) {
      dispatch(messageDeleted({
        message_id: messageId,
        chat_id: deletedMessageData.chatId
      }));
    }
    
    return Promise.resolve({ 
      success: true, 
      messageId 
    });
  }, [dispatch, ws, chatState.messages]);

  // 🔥 ФУНКЦИЯ ОТМЕТКИ СООБЩЕНИЯ КАК ПРОЧИТАННОГО (HTTP + WebSocket уведомления)
  const markMessageAsRead = useCallback(async (messageId) => {
    console.log('📖 Marking message as read:', messageId);
    
    if (!messageId) {
      console.error('❌ Message ID is required');
      return Promise.reject(new Error('Message ID is required'));
    }
    
    const currentUserId = profile?.id || profile?.user_id;
    const chatId = chatState.currentChat?.id
    
    try {
      // Сначала обновляем локально для мгновенного UI
      dispatch(updateMessageReadStatus({ messageId, isRead: true, userId: String(currentUserId) }));

      if (ws?.isConnected && chatId) {
        ws.markMessageAsRead(messageId, chatId)
      }

      await chatAPI.markMessageAsRead(messageId);
      console.log('✅ Message marked as read:', messageId);
      
      return { success: true, messageId };
    } catch (error) {
      console.error('❌ Error marking message as read:', error);
      // Откатываем локальные изменения при ошибке
      dispatch(updateMessageReadStatus({ messageId, isRead: false, userId: String(currentUserId) }));
      throw error;
    }
  }, [dispatch, profile, chatState.currentChat?.id, ws]);

  // 🔥 ФУНКЦИЯ ОТМЕТКИ ЧАТА КАК ПРОЧИТАННОГО (улучшенная)
  const markChatAsRead = useCallback(async (chatId) => {
    console.log('📖 Marking chat as read:', chatId);
    
    if (!chatId) {
      console.error('❌ Chat ID is required');
      return Promise.reject(new Error('Chat ID is required'));
    }
    
    try {
      // Отмечаем все непрочитанные сообщения в чате как прочитанные
      const chatMessages = chatState.messages[chatId] || [];
      const currentUserId = profile?.id || profile?.user_id
      const currentUserKey = currentUserId !== undefined && currentUserId !== null ? String(currentUserId) : null

      const unreadMessages = chatMessages.filter((msg) => {
        const isReadByFlag = !!msg.is_read
        const isReadByReadBy = !!(currentUserKey && msg?.read_by && msg.read_by[currentUserKey])
        const isRead = isReadByFlag || isReadByReadBy
        return !isRead && msg.user_id !== currentUserId
      })

      const unreadMessageIds = unreadMessages.map(msg => msg.id).filter(Boolean);
      
      // Оптимистично обновляем UI
      unreadMessages.forEach(msg => {
        dispatch(updateMessageReadStatus({ messageId: msg.id, isRead: true, userId: currentUserKey }));
      });
      
      // Отправляем запрос на сервер
      if (unreadMessageIds.length > 0) {
        if (ws?.isConnected) {
          ws.markChatAsRead(chatId, unreadMessageIds, false)
        }

        await chatAPI.markChatAsRead(chatId, unreadMessageIds, false);
      } else {
        // Если локально непрочитанных нет (например, мы еще не загрузили их)
        // отмечаем весь чат на сервере
        if (ws?.isConnected) {
          ws.markChatAsRead(chatId, [], true)
        }
        await chatAPI.markChatAsRead(chatId, [], true);
      }
      
      // Обновляем счетчик непрочитанных в списке чатов
      dispatch(updateChatsFromWebSocket({
        chatId,
        updatedChat: { unread_count: 0 }
      }));
      
      console.log('✅ Chat marked as read:', chatId, 'Messages:', unreadMessages.length);
      
      return { success: true, chatId, messagesCount: unreadMessages.length };
    } catch (error) {
      console.error('❌ Error marking chat as read:', error);
      throw error;
    }
  }, [dispatch, chatState.messages, profile, ws]);

  // 🔥 ФУНКЦИЯ ПЕРЕСЫЛКИ СООБЩЕНИЯ
  const forwardMessage = useCallback((targetChatId, messageContent, originalMessageId = null) => {
    console.log('🔄 useChat: Forwarding message:', { 
      targetChatId, 
      originalMessageId,
      contentLength: messageContent?.length 
    });
    
    const userId = profile?.id || profile?.user_id;
    
    if (!targetChatId || !messageContent || !userId) {
      console.error('❌ Missing data for forwarding');
      return Promise.reject(new Error('Missing data for forwarding'));
    }
    
    // Форматируем сообщение для пересылки
    const forwardedContent = originalMessageId 
      ? `🔁 Пересланное сообщение:\n${messageContent}`
      : messageContent;
    
    // Отправляем как обычное сообщение
    return sendMessageToChat(targetChatId, forwardedContent)
      .then(result => {
        console.log('✅ Message forwarded successfully:', result);
        return { 
          ...result, 
          originalMessageId,
          isForwarded: true 
        };
      })
      .catch(error => {
        console.error('❌ Error forwarding message:', error);
        throw error;
      });
  }, [sendMessageToChat, profile]);

  // 🔥 ФУНКЦИЯ ПОЛУЧЕНИЯ ИНФОРМАЦИИ О СООБЩЕНИИ
  const getMessageInfo = useCallback((messageId) => {
    const allMessages = Object.values(chatState.messages).flat();
    const message = allMessages.find(msg => msg.id === messageId);
    
    if (!message) {
      console.log('📭 Message not found:', messageId);
      return null;
    }
    
    return {
      ...message,
      isOwn: message.user_id === (profile?.id || profile?.user_id),
      chatInfo: chatState.chats.find(chat => chat.id === message.chat_id)
    };
  }, [chatState.messages, chatState.chats, profile]);

  // 🔥 ФУНКЦИЯ ВЫБОРА ЧАТА (улучшенная)
  const selectChat = useCallback(async (chat) => {
    if (!chat?.id) {
      console.error('❌ Invalid chat object')
      return
    }
    
    console.log('🎯 Selecting chat:', chat.id)
    dispatch(setCurrentChat(chat))
    loadMessages(chat.id, 50, 0, chat.type)
    
    // Отмечаем чат как прочитанный
    if (chat.type !== 'channel') {
      try {
        await markChatAsRead(chat.id)
      } catch (error) {
        console.warn('⚠️ Failed to mark chat as read:', error)
        // Не прерываем выбор чата при ошибке прочтения
      }
    }
  }, [dispatch, loadMessages, markChatAsRead])

  // 🔥 ИНДИКАТОР НАБОРА ТЕКСТА
  const handleTyping = useCallback((chatId, isTyping) => {
    if (!chatId || !ws.isConnected) return
    
    if (isTyping && ws.startTyping) {
      console.log('⌨️ Starting typing indicator for chat:', chatId)
      ws.startTyping(chatId)
      
      // Автоматически останавливаем через 2 секунды
      setTimeout(() => {
        if (ws.stopTyping && ws.isConnected) {
          console.log('⏹️ Stopping typing indicator for chat:', chatId)
          ws.stopTyping(chatId)
        }
      }, 2000)
    } else if (ws.stopTyping) {
      console.log('⏹️ Stopping typing indicator for chat:', chatId)
      ws.stopTyping(chatId)
    }
  }, [ws])

  // 🔥 ЭФФЕКТ: Подключаем WebSocket когда профиль загружен
  useEffect(() => {
    const userId = profile?.id || profile?.user_id
    
    if (!userId || profileLoading) {
      console.log('⏳ useChat: Waiting for profile...')
      return
    }
    
    console.log('🚀 useChat: Profile loaded, user ID:', userId)
    
    // Проверяем, сменился ли пользователь
    const userChanged = lastUserIdRef.current && lastUserIdRef.current !== userId
    
    if (userChanged) {
      console.log('🔄 User changed, resetting WebSocket state')
      loadedRef.current = false
      wsConnectionAttemptedRef.current = false
    }
    
    // Подключаем WebSocket если не подключен и еще не пытались подключиться
    if (!ws.isConnected && !wsConnectionAttemptedRef.current) {
      console.log('🔌 useChat: Connecting WebSocket...')
      wsConnectionAttemptedRef.current = true
      
      const connectTimeout = setTimeout(() => {
        if (ws.connect && !ws.isConnected) {
          ws.connect()
        }
      }, 1000)
      
      return () => {
        clearTimeout(connectTimeout)
        // Если подключение не удалось, сбрасываем флаг попытки
        if (!ws.isConnected) {
          wsConnectionAttemptedRef.current = false
        }
      }
    } else if (ws.isConnected) {
      console.log('✅ useChat: WebSocket already connected')
      wsConnectionAttemptedRef.current = true
    } else {
      console.log('⏭️ useChat: WebSocket connection already attempted')
    }
    
  }, [profile, profileLoading, ws])

  // 🔥 ЭФФЕКТ: Загружаем чаты когда профиль загружен
  useEffect(() => {
    const userId = profile?.id || profile?.user_id
    
    if (userId && !profileLoading) {
      console.log('📥 useChat: Profile loaded, loading chats...')
      loadChats()
    }
  }, [profile, profileLoading, loadChats])

  // 🔥 ЭФФЕКТ: Слушаем WebSocket события для обновления списка чатов
  useEffect(() => {
    const handleIncomingMessage = (message) => {
      if (!message || !message.chat_id) return
      
      console.log('🔄 useChat: Updating chat list from new message')
      
      dispatch(updateChatsFromWebSocket({
        chatId: message.chat_id,
        updatedChat: {
          last_message: message.content,
          last_message_time: message.created_at,
          unread_count: message.user_id !== (profile?.id || profile?.user_id) ? 1 : 0
        }
      }))
    }
    
    // Подписываемся на события WebSocket
    if (ws.isConnected) {
      console.log('👂 useChat: Listening to WebSocket events')
      // Можно добавить подписку на конкретные события если нужно
    }
    
  }, [dispatch, profile, ws.isConnected])

  // 🔥 ЭФФЕКТ: Очистка при размонтировании
  useEffect(() => {
    return () => {
      console.log('🧹 useChat: Component unmounting')
      loadedRef.current = false
      lastUserIdRef.current = null
    }
  }, [])

  // 🔥 ВОЗВРАЩАЕМ ВСЕ ФУНКЦИИ И СОСТОЯНИЯ
  return useMemo(() => ({
    // Состояние из Redux
    ...chatState,
    
    // Функции WebSocket
    ...ws,
    
    // Основные функции
    loadChats,
    loadMessages,
    sendMessage: sendMessageToChat,
    editMessage,
    deleteMessage,
    forwardMessage,
    getMessageInfo,
    selectChat,
    handleTyping,
    
    // 🔥 НОВЫЕ ФУНКЦИИ ПРОЧТЕНИЯ
    markMessageAsRead,
    markChatAsRead,
    
    // Данные профиля
    profile,
    
    // Дополнительные метрики
    isWebSocketConnected: ws.isConnected,
    hasProfile: !!profile,
    userId: profile?.id || profile?.user_id,
    
    // 🔥 УТИЛИТЫ ДЛЯ UI
    getCurrentUserId: () => profile?.id || profile?.user_id || 'unknown',
    isOwnMessage: (message) => {
      const currentUserId = profile?.id || profile?.user_id
      return message?.user_id === currentUserId || 
             message?.user_id?.toString() === currentUserId?.toString()
    }
    
  }), [
    chatState, 
    ws, 
    loadChats, 
    loadMessages, 
    sendMessageToChat, 
    editMessage,
    deleteMessage,
    forwardMessage,
    getMessageInfo,
    selectChat, 
    handleTyping,
    markMessageAsRead,
    markChatAsRead,
    profile, 
    profileLoading
  ])
}