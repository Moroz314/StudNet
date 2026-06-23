import React, { useEffect } from 'react'
import { GoComment, GoPlus } from 'react-icons/go'
import { useChat } from '../../hooks/useChat'
import { useWebSocket } from '../../hooks/useWebSocket'
import { Link } from 'react-router-dom'
import { channelAPI } from '../../services/api'

export default function ListsChats({ onChatSelect, initialTab }) {
  const { chats, currentChat, selectChat, loadChats, isLoading, error } = useChat()
  const { isConnected: isWsConnected } = useWebSocket()
  const [activeTab, setActiveTab] = React.useState(initialTab || 'chats')
  const [myChannels, setMyChannels] = React.useState([])
  const [myAdminChannels, setMyAdminChannels] = React.useState([])
  const [channelsLoading, setChannelsLoading] = React.useState(false)

  // 🔥 ИСПРАВЛЕННЫЙ useEffect: добавлена зависимость chats
  useEffect(() => {
    console.log('🔄 ListsChats: Component mounted or chats updated', {
      chatsCount: chats?.length || 0,
      currentChat: currentChat?.id,
      isLoading,
      error
    })
  }, [chats, currentChat, isLoading, error])

  // 🔥 ЗАГРУЗКА ЧАТОВ ПРИ МОНТИРОВАНИИ КОМПОНЕНТА
  useEffect(() => {
    console.log('📋 ListsChats: Loading chats...')
    loadChats()
  }, [loadChats]) // ✅ Добавлена зависимость

  const loadMyChannels = React.useCallback(async () => {
    setChannelsLoading(true)
    try {
      const response = await channelAPI.getMyChannels()
      setMyChannels(Array.isArray(response?.data) ? response.data : [])
    } finally {
      setChannelsLoading(false)
    }
  }, [])

  const loadMyAdminChannels = React.useCallback(async () => {
    setChannelsLoading(true)
    try {
      const response = await channelAPI.getMyAdminChannels()
      setMyAdminChannels(Array.isArray(response?.data) ? response.data : [])
    } finally {
      setChannelsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadMyChannels()
  }, [loadMyChannels])

  useEffect(() => {
    if (activeTab === 'channels') {
      loadMyChannels()
    }
    if (activeTab === 'admin_channels') {
      loadMyAdminChannels()
    }
  }, [activeTab, loadMyChannels, loadMyAdminChannels])

  // 🔥 ИСПРАВЛЕННАЯ ФУНКЦИЯ: преобразование id в строку для split
  const getAvatarColor = (chatId) => {
    if (!chatId) return 'bg-purple-600'
    
    const colors = [
      'bg-gradient-to-r from-purple-600 to-pink-600',
      'bg-gradient-to-r from-blue-600 to-teal-600',
      'bg-gradient-to-r from-green-600 to-emerald-600',
      'bg-gradient-to-r from-pink-600 to-rose-600',
      'bg-gradient-to-r from-orange-600 to-red-600',
      'bg-gradient-to-r from-teal-600 to-cyan-600',
      'bg-gradient-to-r from-indigo-600 to-blue-600',
      'bg-gradient-to-r from-red-600 to-orange-600'
    ]
    
    // ✅ Исправлено: гарантируем, что chatId - строка
    const idString = String(chatId)
    const hash = idString.split('').reduce((acc, char) => {
      return acc + char.charCodeAt(0)
    }, 0)
    
    return colors[hash % colors.length]
  }

  // 🔥 ИСПРАВЛЕННЫЙ ПЕРЕВОД ТИПОВ ЧАТА
  const getChatTypeLabel = (type) => {
    const types = {
      'private': 'Приватный',
      'group': 'Групповой',
      'channel': 'Канал',
      'direct': 'Личный',
      'public': 'Публичный',
      'string': 'Чат'
    }
    return types[type] || type || 'Неизвестный'
  }

  // 🔥 ИСПРАВЛЕННАЯ ФУНКЦИЯ ФОРМАТИРОВАНИЯ ВРЕМЕНИ
  const formatLastMessageTime = (timestamp) => {
    if (!timestamp) return 'Нет сообщений'
    
    try {
      const messageDate = new Date(timestamp)
      const now = new Date()
      const diffInMs = now - messageDate
      
      if (isNaN(diffInMs)) return 'Недавно'
      
      const diffInMinutes = Math.floor(diffInMs / (1000 * 60))
      const diffInHours = Math.floor(diffInMs / (1000 * 60 * 60))
      const diffInDays = Math.floor(diffInMs / (1000 * 60 * 60 * 24))
      
      if (diffInMinutes < 1) {
        return 'Только что'
      } else if (diffInMinutes < 60) {
        return `${diffInMinutes} мин. назад`
      } else if (diffInHours < 24) {
        return `${diffInHours} ч. назад`
      } else if (diffInDays === 1) {
        return 'Вчера'
      } else if (diffInDays < 7) {
        return `${diffInDays} дн. назад`
      } else {
        return messageDate.toLocaleDateString('ru-RU', {
          day: '2-digit',
          month: '2-digit'
        })
      }
    } catch (error) {
      console.error('Error formatting date:', error)
      return 'Недавно'
    }
  }

  // 🔥 УЛУЧШЕННЫЙ ОБРАБОТЧИК КЛИКА ПО ЧАТУ
  const handleChatClick = (chat) => {
    console.log('💬 Selecting chat:', chat.id, chat.name)
    if (chat.id !== currentChat?.id) {
      selectChat(chat)
      // Вызываем onChatSelect для мобильной навигации
      if (onChatSelect) {
        onChatSelect()
      }
    }
  }

  // 🔥 ОТОБРАЖЕНИЕ ОШИБКИ
  if (error) {
    return (
      <div className="bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-800 p-4 sm:p-6 h-full min-h-[300px] flex flex-col items-center justify-center">
        <div className="text-center max-w-md">
          <div className="w-20 h-20 rounded-full bg-gradient-to-br from-red-900/20 to-red-900/10 flex items-center justify-center mx-auto mb-6 border border-red-800/30">
            <svg className="w-10 h-10 text-red-500" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          </div>
          <h3 className="text-xl font-semibold text-white mb-2">Ошибка загрузки</h3>
          <p className="text-gray-400 mb-4">{error.message || 'Не удалось загрузить чаты'}</p>
          <button
            onClick={loadChats}
            className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white px-6 py-3 rounded-lg transition-all duration-200 hover:shadow-lg hover:shadow-purple-500/30"
          >
            Попробовать снова
          </button>
        </div>
      </div>
    )
  }

  // 🔥 ЗАГРУЗКА
  if (isLoading) {
    return (
      <div className="bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-800 p-4 sm:p-6 h-full min-h-[300px] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
          <p className="text-gray-400">Загрузка чатов...</p>
          <p className="text-gray-500 text-sm mt-2">Подождите немного</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-800 p-3 sm:p-4 lg:p-6 overflow-y-auto h-full min-h-0 hover:border-gray-700 transition-all duration-300 flex flex-col">
      {/* Заголовок и кнопка создания */}
      <div className="flex justify-between items-center mb-4 sm:mb-6 pb-3 sm:pb-4 border-b border-gray-800">
        <h2 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
          <GoComment className='text-purple-400 w-5 h-5 sm:w-auto sm:h-auto'/>
          <span className="hidden xs:inline">Мои чаты</span>
          <span className="xs:hidden">Чаты</span>
          {(activeTab === 'chats' ? chats.filter(c => c.type !== 'channel') : activeTab === 'channels' ? myChannels : myAdminChannels).length > 0 && (
            <span className="bg-gray-800 text-gray-300 text-xs sm:text-sm px-2 py-1 rounded-full ml-2">
              {(activeTab === 'chats' ? chats.filter(c => c.type !== 'channel') : activeTab === 'channels' ? myChannels : myAdminChannels).length}
            </span>
          )}
        </h2>
        <Link 
          to='/add_chat'
          className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white px-3 py-2 sm:px-4 rounded-lg flex items-center gap-2 transition-all duration-200 hover:shadow-lg hover:shadow-purple-500/20"
        >
          <GoPlus className="text-base sm:text-lg" />
          <span className="hidden xs:inline text-sm sm:text-base">Создать</span>
        </Link>
      </div>
      <div className="mb-4 p-1 bg-gray-900/60 border border-gray-800 rounded-xl flex gap-1">
        <button
          type="button"
          onClick={() => setActiveTab('chats')}
          className={`flex-1 py-2 rounded-lg text-sm ${activeTab === 'chats' ? 'bg-purple-600 text-white' : 'text-gray-400 hover:text-gray-200'}`}
        >
          Чаты
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('channels')}
          className={`flex-1 py-2 rounded-lg text-sm ${activeTab === 'channels' ? 'bg-purple-600 text-white' : 'text-gray-400 hover:text-gray-200'}`}
        >
          Подписки
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('admin_channels')}
          className={`flex-1 py-2 rounded-lg text-sm ${activeTab === 'admin_channels' ? 'bg-purple-600 text-white' : 'text-gray-400 hover:text-gray-200'}`}
        >
          Я админ
        </button>
      </div>
      {/* Список чатов */}
      <div className="overflow-y-auto flex-1 pr-2 scrollbar-thin scrollbar-thumb-purple-600/50 scrollbar-track-gray-800 scrollbar-thumb-rounded-full hover:scrollbar-thumb-purple-600 transition-colors">
        <div className="space-y-3">
          {activeTab === 'channels' || activeTab === 'admin_channels' ? (
            channelsLoading ? (
              <div className="text-center text-gray-400 py-10">Загрузка каналов...</div>
            ) : (activeTab === 'channels' ? myChannels : myAdminChannels).length > 0 ? (
              (activeTab === 'channels' ? myChannels : myAdminChannels).map((channel) => {
                const chat = {
                  ...channel,
                  type: 'channel',
                  name: channel.name,
                  last_message: channel.last_message_preview,
                  last_message_time: channel.last_message_at,
                  participants_count: channel.subscribers_count || 0,
                }
                const isActive = true
                const unreadCount = 0
                const lastMessage = chat.last_message || 'Нет сообщений'
                const lastMessageTime = chat.last_message_time || chat.updated_at || chat.created_at
                const participantsCount = chat.participants_count || 0
                return (
                  <div
                    onClick={() => handleChatClick(chat)}
                    key={chat.id}
                    className={`relative border rounded-xl p-2 sm:p-3 lg:p-4 hover:shadow-lg transition-all duration-300 group flex items-center gap-2 sm:gap-3 lg:gap-4 cursor-pointer transform hover:-translate-y-0.5 ${
                      currentChat?.id === chat.id
                        ? 'border-purple-600 bg-gradient-to-r from-purple-900/20 to-purple-900/5 shadow-lg shadow-purple-500/20'
                        : 'border-gray-700 hover:border-purple-500/50 hover:shadow-purple-500/10 hover:bg-gray-800/20'
                    }`}
                  >
                    <div className={`relative flex-shrink-0 w-10 h-10 sm:w-12 sm:h-12 rounded-full flex items-center justify-center text-white font-bold text-sm sm:text-lg border-2 shadow-lg ${getAvatarColor(chat.id)} ${
                      currentChat?.id === chat.id ? 'border-purple-400 shadow-purple-500/40' : 'border-white/10 shadow-black/30 group-hover:border-purple-300/50'
                    }`}>
                      {chat.name?.charAt(0)?.toUpperCase() || '#'}
                      {isActive && <div className="absolute -bottom-1 -right-1 w-2.5 h-2.5 sm:w-3.5 sm:h-3.5 bg-green-500 rounded-full border-2 border-gray-900 shadow"></div>}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between items-start mb-1 sm:mb-2">
                        <h3 className="text-sm sm:text-base lg:text-lg font-semibold text-white group-hover:text-purple-300 transition-colors truncate">{chat.name || 'Канал проекта'}</h3>
                        {lastMessageTime && <span className="text-gray-400 text-xs whitespace-nowrap">{formatLastMessageTime(lastMessageTime)}</span>}
                      </div>
                      <p className="text-gray-400 text-xs sm:text-sm group-hover:text-gray-300 transition-colors truncate mb-1 sm:mb-2">{lastMessage.length > 50 ? `${lastMessage.substring(0, 50)}...` : lastMessage}</p>
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-gray-500 bg-gray-900/50 px-1.5 sm:px-2 py-0.5 sm:py-1 rounded capitalize">Канал проекта</span>
                        <span className="flex items-center gap-1 text-xs text-gray-500">{participantsCount}</span>
                      </div>
                    </div>
                  </div>
                )
              })
            ) : (
              <div className="text-center py-8 text-gray-400">
                {activeTab === 'channels'
                  ? 'Вы пока не подписаны на каналы проектов.'
                  : 'У вас пока нет каналов, где вы админ/владелец.'}
              </div>
            )
          ) : chats && Array.isArray(chats) && chats.filter(c => c.type !== 'channel').length > 0 ? (
            chats.filter(c => c.type !== 'channel').map(chat => {
              const isActive = chat.is_active !== false
              const unreadCount = chat.unread_count || 0
              const lastMessage = chat.last_message || 'Нет сообщений'
              const lastMessageTime = chat.last_message_time || chat.updated_at || chat.created_at
              const participantsCount = chat.participants_count || 1
              
              return (
                <div 
                  onClick={() => handleChatClick(chat)}
                  key={chat.id} 
                  className={`relative border rounded-xl p-2 sm:p-3 lg:p-4 hover:shadow-lg transition-all duration-300 group flex items-center gap-2 sm:gap-3 lg:gap-4 cursor-pointer transform hover:-translate-y-0.5 ${
                    currentChat?.id === chat.id 
                      ? 'border-purple-600 bg-gradient-to-r from-purple-900/20 to-purple-900/5 shadow-lg shadow-purple-500/20' 
                      : 'border-gray-700 hover:border-purple-500/50 hover:shadow-purple-500/10 hover:bg-gray-800/20'
                  }`}
                >
                  {/* Индикатор непрочитанных сообщений */}
                  {unreadCount > 0 && (
                    <div className="absolute -top-2 -right-2 z-10">
                      <span className="bg-gradient-to-r from-purple-600 to-pink-600 text-white text-xs font-bold px-2 py-1 rounded-full min-w-6 h-6 flex items-center justify-center shadow-lg shadow-purple-500/30">
                        {unreadCount > 99 ? '99+' : unreadCount}
                      </span>
                    </div>
                  )}

                  {/* Аватар чата */}
                  <div className={`relative flex-shrink-0 w-10 h-10 sm:w-12 sm:h-12 rounded-full flex items-center justify-center text-white font-bold text-sm sm:text-lg border-2 shadow-lg ${getAvatarColor(chat.id)} ${
                    currentChat?.id === chat.id 
                      ? 'border-purple-400 shadow-purple-500/40' 
                      : 'border-white/10 shadow-black/30 group-hover:border-purple-300/50'
                  }`}>
                    {chat.name?.charAt(0)?.toUpperCase() || 'C'}
                    
                    {/* Индикатор активности */}
                    {isActive && (
                      <div className="absolute -bottom-1 -right-1 w-2.5 h-2.5 sm:w-3.5 sm:h-3.5 bg-green-500 rounded-full border-2 border-gray-900 shadow"></div>
                    )}
                  </div>
                  
                  {/* Информация о чате */}
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-start mb-1 sm:mb-2">
                      <h3 className="text-sm sm:text-base lg:text-lg font-semibold text-white group-hover:text-purple-300 transition-colors truncate">
                        {chat.name || 'Без названия'}
                      </h3>
                      <div className="flex flex-col items-end gap-1">
                        {lastMessageTime && (
                          <span className="text-gray-400 text-xs whitespace-nowrap">
                            {formatLastMessageTime(lastMessageTime)}
                          </span>
                        )}
                        {!isActive && (
                          <span className="text-red-400 text-xs bg-red-900/30 px-1 sm:px-1.5 py-0.5 rounded hidden sm:block">
                            Архив
                          </span>
                        )}
                      </div>
                    </div>
                    
                    {/* Последнее сообщение */}
                    <p className="text-gray-400 text-xs sm:text-sm group-hover:text-gray-300 transition-colors truncate mb-1 sm:mb-2">
                      {lastMessage.length > 30 ? `${lastMessage.substring(0, 30)}...` : lastMessage.length > 50 ? `${lastMessage.substring(0, 50)}...` : lastMessage}
                    </p>
                    
                    {/* Мета-информация */}
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-500 bg-gray-900/50 px-1.5 sm:px-2 py-0.5 sm:py-1 rounded capitalize hidden xs:block">
                          {getChatTypeLabel(chat.type)}
                        </span>
                        {chat.created_by && (
                          <span className="text-xs text-gray-500 truncate max-w-[60px] sm:max-w-[80px] hidden sm:block">
                            Создал: {String(chat.created_by).substring(0, 6)}...
                          </span>
                        )}
                      </div>
                       
                      <div className="flex items-center gap-1 sm:gap-2 text-xs text-gray-500">
                        <span className="flex items-center gap-1">
                          <svg className="w-2.5 h-2.5 sm:w-3 sm:h-3" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3 3 0 013.75-2.906z" />
                          </svg>
                          {participantsCount}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })
          ) : (
            /* Сообщение если чатов нет */
            <div className="text-center py-8 sm:py-12 px-4">
              <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-gradient-to-br from-gray-800 to-gray-900 flex items-center justify-center mx-auto mb-4 sm:mb-6 border border-gray-700">
                <GoComment className="text-2xl sm:text-3xl text-gray-500" />
              </div>
              <h3 className="text-lg sm:text-xl font-semibold text-white mb-2">Чатов пока нет</h3>
              <p className="text-gray-400 text-sm mb-6 sm:mb-8 max-w-xs sm:max-w-sm mx-auto">
                Создайте первый чат для общения с коллегами, друзьями или клиентами
              </p>
              <Link 
                to='/add_chat'
                className="inline-flex items-center gap-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white px-4 sm:px-6 py-2 sm:py-3 rounded-lg transition-all duration-200 hover:shadow-lg hover:shadow-purple-500/30 transform hover:-translate-y-0.5"
              >
                <GoPlus className="text-base sm:text-lg" />
                <span className="text-sm sm:text-base">Создать первый чат</span>
              </Link>
              
              {/* Подсказки */}
              <div className="mt-6 sm:mt-10 grid grid-cols-1 gap-3 sm:gap-4 text-left">
                <div className="bg-gray-800/30 p-3 sm:p-4 rounded-lg border border-gray-700">
                  <div className="text-purple-400 font-bold text-xs sm:text-sm mb-2">📱 Личные чаты</div>
                  <p className="text-gray-400 text-xs">Общайтесь один на один с коллегами</p>
                </div>
                <div className="bg-gray-800/30 p-3 sm:p-4 rounded-lg border border-gray-700">
                  <div className="text-blue-400 font-bold text-xs sm:text-sm mb-2">👥 Групповые чаты</div>
                  <p className="text-gray-400 text-xs">Создавайте группы для работы</p>
                </div>
                <div className="bg-gray-800/30 p-3 sm:p-4 rounded-lg border border-gray-700">
                  <div className="text-green-400 font-bold text-xs sm:text-sm mb-2">📢 Каналы</div>
                  <p className="text-gray-400 text-xs">Публичные каналы для новостей</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 🔥 ИСПРАВЛЕННАЯ ИНФОРМАЦИЯ О ВЫБРАННОМ ЧАТЕ */}
      {currentChat && chats && chats.length > 0 && (
        <div className="mt-6 pt-4 border-t border-gray-800">
          <div className="text-sm text-gray-400">
            <span className="text-gray-500">Выбран:</span>{' '}
            <span className="text-purple-300 font-medium">{currentChat.name || 'Без названия'}</span>
            <span className="mx-2">•</span>
            <span className="text-gray-500">{getChatTypeLabel(currentChat.type)}</span>
            <span className="mx-2">•</span>
            <span className="text-gray-500">
              {currentChat.participants_count || 1} участников
            </span>
          </div>
          <div className="text-xs text-gray-600 mt-1">
            ID: {currentChat.id}
          </div>
        </div>
      )}

      {/* 🔥 СТАТИСТИКА */}
      <div className="mt-4 pt-4 border-t border-gray-800">
        <div className="text-xs text-gray-500 sm:flex sm:justify-between">
          <div className="flex flex-col sm:flex-row sm:gap-2 mb-2 sm:mb-0">
            <span>Всего: {chats?.length || 0}</span>
            <span>Активных: {chats?.filter(c => c.is_active !== false).length || 0}</span>
            <span>Непрочитанных: {chats?.reduce((sum, c) => sum + (c.unread_count || 0), 0) || 0}</span>
          </div>
        </div>
      </div>
    </div>
  )
}