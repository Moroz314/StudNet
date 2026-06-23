// components/Chats/ScreenChat.jsx
import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { useDispatch } from 'react-redux'
import { GoComment, GoArrowLeft, GoArrowUp, GoPaperclip, GoPlus, GoX } from 'react-icons/go'
import { useChat } from '../../hooks/useChat'
import { chatAPI, normalizeAssetUrl, searchAPI } from '../../services/api'
import { clearChatMessages, setMessagesForChat } from '../../store/slices/chatSlice'
import { IoCheckmarkDoneOutline } from "react-icons/io5";
import * as ContextMenu from '@radix-ui/react-context-menu';
import { FaPen, FaReply, FaReplyAll, FaRegTrashAlt, FaCopy, FaCheckCircle, FaTrash, FaUserFriends } from "react-icons/fa";
import { TbPinFilled } from "react-icons/tb";
import { FiCopy, FiCheck } from "react-icons/fi";
import { FaHeart, FaRegHeart } from "react-icons/fa";
import { FiFileText, FiArchive, FiFile, FiMusic, FiCode, FiFileMinus } from "react-icons/fi";
import { updateMessageLikeState } from '../../store/slices/chatSlice'
import { channelAPI, projectsAPI } from '../../services/api'

export default function ScreenChat({ onBack }) {
  const dispatch = useDispatch()

  const {
    currentChat,
    messages,
    profile,
    typingUsers,
    loadMessages,
    sendMessage,
    handleTyping,
    editMessage,
    deleteMessage,
    isLoading,
    forwardMessage,
    chats,
    isWebSocketConnected,
    markMessageAsRead,
    markChatAsRead,
    getCurrentUserId,
  } = useChat();

  const messagesForCurrentChat = currentChat?.id 
    ? (messages[String(currentChat.id)] || [])
    : [];
  
  const [messageInput, setMessageInput] = useState('')
  const [attachedFiles, setAttachedFiles] = useState([])
  const [isSendingMedia, setIsSendingMedia] = useState(false)
  const typingStopTimerRef = useRef(null)
  const lastTypingSignalAtRef = useRef(0)
  const [isSending, setIsSending] = useState(false)
  const messagesEndRef = useRef(null)
  const messagesContainerRef = useRef(null)
  const inputRef = useRef(null)
  
  // Состояния для контекстного меню
  const [selectedMessage, setSelectedMessage] = useState(null)
  const [isEditing, setIsEditing] = useState(false)
  const [editContent, setEditContent] = useState('')
  const [replyToMessage, setReplyToMessage] = useState(null)
  const [forwardMessages, setForwardMessages] = useState([])
  const [copiedMessageId, setCopiedMessageId] = useState(null)
  const [pinnedMessages, setPinnedMessages] = useState([])
  const [selectedMessages, setSelectedMessages] = useState([])
  const [showForwardModal, setShowForwardModal] = useState(false)
  const [selectedChatsForForward, setSelectedChatsForForward] = useState([])
  const [pdfPreview, setPdfPreview] = useState({ isOpen: false, url: '', title: '' })

  // Участники чата
  const [participants, setParticipants] = useState([])
  const [participantsLoading, setParticipantsLoading] = useState(false)
  const [participantsError, setParticipantsError] = useState('')
  const [showParticipantsPanel, setShowParticipantsPanel] = useState(false)

  // Канал: право писать только у участников проекта
  const [canWriteInChannel, setCanWriteInChannel] = useState(true)
  const [channelWriteCheckLoading, setChannelWriteCheckLoading] = useState(false)

  // Поиск пользователей для добавления в чат
  const [userSearchQuery, setUserSearchQuery] = useState('')
  const [userSearchResults, setUserSearchResults] = useState([])
  const [userSearchLoading, setUserSearchLoading] = useState(false)
  const [userSearchError, setUserSearchError] = useState('')

  // ПРОВЕРКА СВОЕГО СООБЩЕНИЯ
  const isOwnMessage = useCallback((message) => {
    const currentUserId = getCurrentUserId();
    if (!currentUserId) return false;

    return String(message.sender_id) === String(currentUserId) || 
           String(message.user_id) === String(currentUserId);
  }, [getCurrentUserId]);

  // Определяем роль текущего пользователя в чате
  const currentUserId = getCurrentUserId();

  const currentUserRole = useMemo(() => {
    if (!currentUserId || !participants || participants.length === 0) return null
    const me = participants.find(p => String(p.user_id) === String(currentUserId))
    return me?.role || null
  }, [participants, currentUserId])

  const canManageParticipants = useMemo(() => {
    if (!currentChat || currentChat.type === 'private') return false
    if (!currentUserRole) return false
    const role = String(currentUserRole).toLowerCase()
    return role === 'owner' || role === 'admin'
  }, [currentChat, currentUserRole])

  // Проверка, прочитано ли сообщение
  const isMessageRead = useCallback((message) => {
    const currentUserId = getCurrentUserId();
    if (!currentUserId) return false;

    const isOwn = isOwnMessage(message);
    if (message?.is_read) return true;

    let readBy = message?.read_by;
    if (typeof readBy === 'string') {
      try {
        readBy = JSON.parse(readBy);
      } catch {
        readBy = null;
      }
    }

    if (!readBy || typeof readBy !== 'object') return false;

    if (isOwn) {
      const otherReaders = Object.keys(readBy).filter(key => key !== String(currentUserId));
      return otherReaders.length > 0;
    }

    return !!readBy[String(currentUserId)];
  }, [getCurrentUserId, isOwnMessage]);

  // 🔥 ПРОКРУТКА К ПОСЛЕДНЕМУ СООБЩЕНИЮ
  useEffect(() => {
    if (messagesContainerRef.current && messagesForCurrentChat.length > 0) {
      setTimeout(() => {
        messagesContainerRef.current?.scrollTo({
          top: messagesContainerRef.current.scrollHeight,
          behavior: 'smooth'
        });
      }, 100);
    }
  }, [messagesForCurrentChat]);

  // Сброс состояния при смене чата
  useEffect(() => {
    if (currentChat?.id) {
      loadMessages(currentChat.id, 50, 0, currentChat.type);
      setReplyToMessage(null);
      setSelectedMessage(null);
      setIsEditing(false);
      setEditContent('');
      setSelectedMessages([]);
      setParticipants([]);
      setParticipantsError('');
      setUserSearchQuery('');
      setUserSearchResults([]);
      setCanWriteInChannel(true);

      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    }
  }, [currentChat?.id, currentChat?.type, loadMessages]);

  // Канал: проверка, является ли пользователь участником проекта (может писать)
  useEffect(() => {
    if (currentChat?.type !== 'channel' || !currentChat?.project_id) {
      setCanWriteInChannel(true);
      return;
    }
    const projectId = currentChat.project_id;
    setChannelWriteCheckLoading(true);
    projectsAPI
      .getProject(projectId)
      .then(() => setCanWriteInChannel(true))
      .catch((err) => {
        const status = err?.response?.status ?? err?.status;
        setCanWriteInChannel(status === 403 || status === 404 ? false : true);
      })
      .finally(() => setChannelWriteCheckLoading(false));
  }, [currentChat?.id, currentChat?.type, currentChat?.project_id]);

  // Загрузка участников чата
  const loadParticipants = useCallback(async () => {
    if (!currentChat?.id || currentChat.type === 'private') return
    try {
      setParticipantsLoading(true)
      setParticipantsError('')
      const response = await chatAPI.getChatParticipants(currentChat.id)
      const data = response.data
      // backend возвращает ChatWithParticipantsDTO или просто список в зависимости от реализации
      const list = Array.isArray(data) ? data : (data.participants || [])
      setParticipants(list)
    } catch (error) {
      console.error('❌ Ошибка загрузки участников чата:', error)
      setParticipantsError(error.message || 'Не удалось загрузить участников')
    } finally {
      setParticipantsLoading(false)
    }
  }, [currentChat?.id, currentChat?.type])

  // Участники нужны для ролей (добавление / удаление) и счётчика — грузим сразу для групп и каналов
  useEffect(() => {
    if (currentChat?.id && currentChat.type !== 'private') {
      loadParticipants()
    }
  }, [currentChat?.id, currentChat?.type, loadParticipants])

  // 🔥 ФУНКЦИИ КОНТЕКСТНОГО МЕНЮ
  const handleReply = useCallback((message) => {
    setReplyToMessage(message);
    inputRef.current?.focus();
  }, []);

  const handleEdit = (message) => {
    setSelectedMessage(message);
    setIsEditing(true);
    setEditContent(message.content);
    inputRef.current?.focus();
  };
  
  const saveEdit = async () => {
    if (!selectedMessage || !editContent.trim()) return;
    
    try {
      await editMessage(selectedMessage.id, editContent);
      setIsEditing(false);
      setSelectedMessage(null);
      setEditContent('');
    } catch (error) {
      console.error('❌ Error editing message:', error);
      alert('Не удалось изменить сообщение');
    }
  };
  
  const handlePin = (message) => {
    setPinnedMessages(prev => {
      const isAlreadyPinned = prev.some(m => m.id === message.id);
      if (isAlreadyPinned) {
        return prev.filter(m => m.id !== message.id);
      } else {
        return [...prev, message];
      }
    });
  };
  
  const handleCopy = async (message) => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopiedMessageId(message.id);
      setTimeout(() => setCopiedMessageId(null), 2000);
    } catch (error) {
      console.error('❌ Ошибка копирования:', error);
      alert('Не удалось скопировать текст');
    }
  };
  
  const handleForward = (message) => {
    setForwardMessages([message]);
    setShowForwardModal(true);
  };
  
  const handleDelete = async (message) => {
    if (!window.confirm('Вы уверены, что хотите удалить это сообщение?')) return;
    
    try {
      await deleteMessage(message.id);
    } catch (error) {
      console.error('❌ Error deleting message:', error);
      alert('Не удалось удалить сообщение');
    }
  };

  const handleToggleLike = async (message) => {
    if (!currentChat?.id || !message?.id) return
    const isLikedNow = !!message.is_liked_by_user
    const nextLikeState = !isLikedNow
    dispatch(updateMessageLikeState({
      chatId: currentChat.id,
      messageId: message.id,
      isLiked: nextLikeState,
    }))
    try {
      if (currentChat.type === 'channel') {
        if (nextLikeState) {
          await channelAPI.likeMessage(currentChat.id, message.id)
        } else {
          await channelAPI.unlikeMessage(currentChat.id, message.id)
        }
      } else {
        if (nextLikeState) {
          await chatAPI.likeMessage(currentChat.id, message.id)
        } else {
          await chatAPI.unlikeMessage(currentChat.id, message.id)
        }
      }
    } catch (error) {
      dispatch(updateMessageLikeState({
        chatId: currentChat.id,
        messageId: message.id,
        isLiked: isLikedNow,
      }))
      console.error('❌ Ошибка лайка сообщения:', error)
      alert('Не удалось поставить лайк')
    }
  }

  const handleSelect = (message) => {
    setSelectedMessages(prev => {
      const isSelected = prev.some(m => m.id === message.id);
      if (isSelected) {
        return prev.filter(m => m.id !== message.id);
      } else {
        return [...prev, message];
      }
    });
  };

  // Добавление пользователя в чат
  const handleAddUserToChat = async (user) => {
    if (!currentChat?.id || !user?.user_id) return

    try {
      await chatAPI.addUsersToChat(currentChat.id, [user.user_id])
      // Обновляем участников и фильтруем результаты
      await loadParticipants()
      setUserSearchResults(prev => prev.filter(u => u.user_id !== user.user_id))
    } catch (error) {
      console.error('❌ Ошибка добавления пользователя в чат:', error)
      const d = error?.data?.detail
      const message =
        (typeof d === 'object' && d !== null && d.message) ||
        (typeof d === 'string' ? d : null) ||
        error.message
      alert(message || 'Не удалось добавить пользователя в чат')
    }
  }

  // Удаление участника из чата
  const handleRemoveUserFromChat = async (participant) => {
    if (!currentChat?.id || !participant?.user_id) return

    if (!window.confirm(`Удалить пользователя ${participant.username || participant.user_id} из чата?`)) {
      return
    }

    try {
      await chatAPI.removeUserFromChat(currentChat.id, participant.user_id)
      await loadParticipants()
    } catch (error) {
      console.error('❌ Ошибка удаления пользователя из чата:', error)
      const message = error?.data?.detail?.message || error?.data?.detail || error.message
      alert(message || 'Не удалось удалить пользователя из чата')
    }
  }

  // Поиск пользователей для добавления в чат
  const handleSearchUsers = async (e) => {
    e.preventDefault()
    if (!userSearchQuery.trim() || !currentChat?.id) return

    try {
      setUserSearchLoading(true)
      setUserSearchError('')
      const response = await searchAPI.searchUsers(userSearchQuery.trim(), 1, 10)
      const data = response.data
      const results = data.profiles || []

      // Фильтруем уже добавленных участников и текущего пользователя
      const participantIds = new Set(participants.map((p) => Number(p.user_id)))
      const filtered = results.filter((user) => {
        if (!user?.user_id) return false
        if (participantIds.has(Number(user.user_id))) return false
        if (currentUserId && String(user.user_id) === String(currentUserId)) return false
        return true
      })

      setUserSearchResults(filtered)

      if (filtered.length === 0) {
        setUserSearchError('Подходящие пользователи не найдены')
      }
    } catch (error) {
      console.error('❌ Ошибка поиска пользователей для добавления в чат:', error)
      setUserSearchError('Ошибка при поиске пользователей')
      setUserSearchResults([])
    } finally {
      setUserSearchLoading(false)
    }
  }

  // 🔥 ОЧИСТКА ИСТОРИИ ЧАТА
  const handleClearChatHistory = async () => {
    if (!currentChat?.id) return;
    
    const confirmMessage = `Вы уверены, что хотите удалить всю историю чата "${currentChat.name || 'Без названия'}"?`;
    
    if (!window.confirm(confirmMessage)) return;
    
    try {
      await chatAPI.clearChatHistory(currentChat.id);
      dispatch(clearChatMessages(currentChat.id));
      await loadMessages(currentChat.id);
      alert('История чата успешно удалена');
    } catch (error) {
      console.error('❌ Ошибка при удалении истории чата:', error);
      alert('Не удалось удалить историю чата');
    }
  };

  // 🔥 ОБРАБОТКА ВЫБОРА ФАЙЛОВ
  const handleFileChange = (e) => {
    const files = Array.from(e.target.files || [])
    setAttachedFiles(files)
  }

  // 🔥 ОТПРАВКА СООБЩЕНИЯ (текст + медиа)
  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!currentChat?.id) return

    const hasText = !!messageInput.trim()
    const hasFiles = attachedFiles.length > 0

    if (!hasText && !hasFiles) return

    try {
      // Сначала текстовое сообщение (REST)
      if (hasText) {
        setIsSending(true)
        await sendMessage(currentChat.id, messageInput.trim(), replyToMessage?.id, currentChat.type)
      }

      // Затем медиа (если есть файлы)
      if (hasFiles) {
        setIsSendingMedia(true)
        const formData = new FormData()
        attachedFiles.forEach((file) => formData.append('files', file))
        const caption = hasText ? null : messageInput.trim()
        let mediaResponse = null
        if (currentChat.type === 'channel') {
          mediaResponse = await channelAPI.sendMediaMessage(currentChat.id, formData, { caption })
        } else {
          mediaResponse = await chatAPI.sendMediaMessage(currentChat.id, formData, {
            caption,
            reply_to_message_id: replyToMessage?.id || null,
          })
        }

        const sentMediaMessage = mediaResponse?.data
        if (sentMediaMessage?.id) {
          const chatKey = String(currentChat.id)
          const prev = messages[chatKey] || []
          const exists = prev.some((m) => String(m.id) === String(sentMediaMessage.id))
          if (!exists) {
            dispatch(setMessagesForChat({ chatId: currentChat.id, messages: [...prev, sentMediaMessage] }))
          }
        }
      }

      setMessageInput('')
      setReplyToMessage(null)
      setAttachedFiles([])

      setTimeout(() => {
        inputRef.current?.focus()
      }, 100)
    } catch (error) {
      console.error('❌ Error sending message/media:', error)
      alert('Не удалось отправить сообщение')
    } finally {
      setIsSending(false)
      setIsSendingMedia(false)
    }
  };

  // 🔥 ФОРМАТИРОВАНИЕ ВРЕМЕНИ И ДАТЫ
  const formatMessageTime = (timestamp) => {
    if (!timestamp) return '';
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('ru-RU', {
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return '';
    }
  };

  const formatMessageDate = (timestamp) => {
    if (!timestamp) return '';
    try {
      const date = new Date(timestamp);
      const now = new Date();
      const yesterday = new Date(now);
      yesterday.setDate(yesterday.getDate() - 1);
      
      if (date.toDateString() === now.toDateString()) return 'Сегодня';
      if (date.toDateString() === yesterday.toDateString()) return 'Вчера';
      
      return date.toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      });
    } catch {
      return '';
    }
  };

  const formatFileSize = (size) => {
    const bytes = Number(size)
    if (!Number.isFinite(bytes) || bytes <= 0) return null
    const units = ['B', 'KB', 'MB', 'GB']
    let value = bytes
    let unitIndex = 0
    while (value >= 1024 && unitIndex < units.length - 1) {
      value /= 1024
      unitIndex += 1
    }
    return `${value.toFixed(value >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`
  }

  const getMediaUrl = (media) => normalizeAssetUrl(media?.url || media?.file_url || media?.path || null)

  const getMediaFilename = (media, url) => {
    if (media?.filename) return media.filename
    if (!url) return 'file'
    try {
      const pathname = new URL(url).pathname
      const rawName = pathname.split('/').pop() || 'file'
      return decodeURIComponent(rawName)
    } catch {
      return 'file'
    }
  }

  const getMediaKind = (media, url) => {
    const type = String(media?.type || media?.content_type || '').toLowerCase()
    const filename = String(media?.filename || '').toLowerCase()
    const target = `${url || ''} ${filename}`.toLowerCase()
    const isImage = type.startsWith('image/') || /\.(png|jpe?g|gif|webp|bmp|svg|heic|avif)(\?|$)/i.test(target)
    if (isImage) return 'image'
    const isVideo = type.startsWith('video/') || /\.(mp4|webm|ogg|mov|m4v|avi|mkv)(\?|$)/i.test(target)
    if (isVideo) return 'video'
    return 'file'
  }

  const getFileCategory = (media, url) => {
    const type = String(media?.type || media?.content_type || '').toLowerCase()
    const filename = String(media?.filename || '').toLowerCase()
    const target = `${url || ''} ${filename}`.toLowerCase()

    if (type.includes('pdf') || /\.pdf(\?|$)/i.test(target)) {
      return { kind: 'pdf', label: 'PDF', icon: FiFileText }
    }
    if (
      type.includes('msword') ||
      type.includes('officedocument.wordprocessingml') ||
      /\.(doc|docx)(\?|$)/i.test(target)
    ) {
      return { kind: 'word', label: 'Word', icon: FiFileText }
    }
    if (
      type.includes('zip') ||
      type.includes('rar') ||
      type.includes('7z') ||
      type.includes('tar') ||
      /\.(zip|rar|7z|tar|gz|bz2|xz)(\?|$)/i.test(target)
    ) {
      return { kind: 'archive', label: 'Архив', icon: FiArchive }
    }
    if (type.startsWith('audio/') || /\.(mp3|wav|ogg|m4a|flac|aac)(\?|$)/i.test(target)) {
      return { kind: 'audio', label: 'Аудио', icon: FiMusic }
    }
    if (
      type.includes('json') ||
      type.includes('javascript') ||
      type.includes('xml') ||
      type.includes('yaml') ||
      /\.(json|js|ts|xml|yml|yaml|md|txt|csv)(\?|$)/i.test(target)
    ) {
      return { kind: 'code', label: 'Документ', icon: FiCode }
    }
    if (type.startsWith('application/')) {
      return { kind: 'app', label: 'Файл', icon: FiFileMinus }
    }
    return { kind: 'file', label: 'Файл', icon: FiFile }
  }

  // 🔥 ГРУППИРОВКА СООБЩЕНИЙ ПО ДАТАМ
  const groupMessagesByDate = useMemo(() => {
    if (!messagesForCurrentChat?.length) return [];
    
    const sortedMessages = [...messagesForCurrentChat].sort((a, b) => {
      return new Date(a.created_at || a.timestamp) - new Date(b.created_at || b.timestamp);
    });
    
    const groups = [];
    let currentDate = null;
    
    sortedMessages.forEach((message, index) => {
      const messageDate = formatMessageDate(message.timestamp || message.created_at);
      
      if (messageDate !== currentDate) {
        groups.push({
          type: 'date',
          date: messageDate,
          key: `date-${messageDate}-${index}`
        });
        currentDate = messageDate;
      }
      
      groups.push({
        type: 'message',
        data: message,
        key: `${message.id}-${message.created_at}-${index}`
      });
    });
    
    return groups;
  }, [messagesForCurrentChat]);

  // 🔥 КОМПОНЕНТ ОТВЕТА НА СООБЩЕНИЕ
  const ReplyPreview = () => {
    if (!replyToMessage) return null;
    
    const scrollToMessage = () => {
      const messageElement = document.querySelector(`[data-message-id="${replyToMessage.id}"]`);
      if (messageElement) {
        messageElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    };
    
    return (
      <div className="mb-3 p-3 bg-gray-800/50 rounded-lg border-l-3 border-purple-500">
        <div className="flex justify-between items-start">
          <div 
            className="flex-1 cursor-pointer"
            onClick={scrollToMessage}
          >
            <div className="flex items-center gap-2 mb-1">
              <FaReply className="w-3 h-3 text-purple-300" />
              <div className="text-sm text-purple-300">
                Ответ на сообщение
              </div>
            </div>
            <div className="text-gray-300 text-sm line-clamp-1">
              {replyToMessage.content}
            </div>
          </div>
          <button
            onClick={() => setReplyToMessage(null)}
            className="ml-2 p-1.5 rounded hover:bg-gray-700 text-gray-400"
          >
            <GoX className="w-4 h-4" />
          </button>
        </div>
      </div>
    );
  };

  // 🔥 КОМПОНЕНТ РЕДАКТИРОВАНИЯ СООБЩЕНИЯ
  const EditMessageForm = () => {
    if (!isEditing || !selectedMessage) return null;
    
    return (
      <div className="mb-2 p-3 bg-gray-800/50 rounded-lg border-l-3 border-blue-500">
        <div className="flex justify-between items-start mb-2">
          <div className="text-sm text-blue-300">
            Редактирование сообщения
          </div>
          <button
            onClick={() => {
              setIsEditing(false);
              setSelectedMessage(null);
              setEditContent('');
            }}
            className="text-gray-400 hover:text-white p-1"
          >
            <GoX className="w-4 h-4" />
          </button>
        </div>
        <textarea
          value={editContent}
          onChange={(e) => setEditContent(e.target.value)}
          className="w-full bg-gray-900 border border-gray-700 rounded p-2 text-white text-sm mb-2"
          rows="2"
          autoFocus
        />
        <div className="flex gap-2">
          <button
            onClick={() => {
              setIsEditing(false);
              setSelectedMessage(null);
              setEditContent('');
            }}
            className="px-3 py-1 bg-gray-700 rounded text-gray-300 hover:bg-gray-600 text-sm"
          >
            Отмена
          </button>
          <button
            onClick={saveEdit}
            disabled={!editContent.trim()}
            className="px-3 py-1 bg-blue-600 rounded text-white hover:bg-blue-700 disabled:opacity-50 text-sm"
          >
            Сохранить
          </button>
        </div>
      </div>
    );
  };

  // 🔥 КОМПОНЕНТ ИНДИКАТОРА ПЕЧАТИ
  const TypingIndicatorComponent = ({ chatId }) => {
    const typingUsersArray = typingUsers[chatId] || [];
    if (typingUsersArray.length === 0) return null;
    
    return (
      <div className="flex items-center gap-2">
        <div className="flex space-x-1">
          <div className="w-1 h-1 bg-[#e53bff] rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
          <div className="w-1 h-1 bg-[#e53bff] rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
          <div className="w-1 h-1 bg-[#e53bff] rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
        </div>
        <span className="text-sm text-gray-400">
          Печатает...
        </span>
      </div>
    );
  };

  // 🔥 КОМПОНЕНТ КОНТЕКСТНОГО МЕНЮ
  const MessageContextMenu = ({ message, children }) => {
    const isOwn = isOwnMessage(message);
    const isPinned = pinnedMessages.some(m => m.id === message.id);
    const isSelected = selectedMessages.some(m => m.id === message.id);
    const isCopied = copiedMessageId === message.id;

    return (
      <ContextMenu.Root>
        <ContextMenu.Trigger asChild>
          {children}
        </ContextMenu.Trigger>
        <ContextMenu.Portal>
          <ContextMenu.Content className="bg-gray-900 border border-gray-700 rounded-lg p-2 min-w-[180px] z-50">
            <ContextMenu.Item 
              className="flex items-center gap-2 px-3 py-2 rounded hover:bg-gray-800 cursor-pointer text-sm text-gray-300"
              onSelect={() => handleReply(message)}
            >
              <FaReply className="w-4 h-4" />
              <span>Ответить</span>
            </ContextMenu.Item>
            
            {isOwn && (
              <ContextMenu.Item 
                className="flex items-center gap-2 px-3 py-2 rounded hover:bg-gray-800 cursor-pointer text-sm text-gray-300"
                onSelect={() => handleEdit(message)}
              >
                <FaPen className="w-4 h-4" />
                <span>Изменить</span>
              </ContextMenu.Item>
            )}
            
            <ContextMenu.Item 
              className="flex items-center gap-2 px-3 py-2 rounded hover:bg-gray-800 cursor-pointer text-sm text-gray-300"
              onSelect={() => handleCopy(message)}
            >
              {isCopied ? (
                <>
                  <FiCheck className="w-4 h-4 text-green-500" />
                  <span className="text-green-500">Скопировано</span>
                </>
              ) : (
                <>
                  <FaCopy className="w-4 h-4" />
                  <span>Копировать</span>
                </>
              )}
            </ContextMenu.Item>
            
            <ContextMenu.Item 
              className="flex items-center gap-2 px-3 py-2 rounded hover:bg-gray-800 cursor-pointer text-sm text-gray-300"
              onSelect={() => handleForward(message)}
            >
              <FaReplyAll className="w-4 h-4" />
              <span>Переслать</span>
            </ContextMenu.Item>
            
            {isOwn && (
              <ContextMenu.Item 
                className="flex items-center gap-2 px-3 py-2 rounded hover:bg-red-900/20 cursor-pointer text-sm text-red-400"
                onSelect={() => handleDelete(message)}
              >
                <FaRegTrashAlt className="w-4 h-4" />
                <span>Удалить</span>
              </ContextMenu.Item>
            )}
          </ContextMenu.Content>
        </ContextMenu.Portal>
      </ContextMenu.Root>
    );
  };

  // 🔥 КОМПОНЕНТ МОДАЛКИ ПЕРЕСЫЛКИ
  const ForwardModal = () => {
    if (!showForwardModal) return null;
    
    const handleForwardToChats = async () => {
      if (!selectedChatsForForward.length || !forwardMessages.length) {
        alert('Выберите чаты для пересылки');
        return;
      }
      
      try {
        for (const targetChatId of selectedChatsForForward) {
          for (const message of forwardMessages) {
            await forwardMessage(targetChatId, message.content, message.id);
          }
        }
        
        alert('Сообщения успешно пересланы!');
        setShowForwardModal(false);
        setForwardMessages([]);
        setSelectedChatsForForward([]);
        
      } catch (error) {
        console.error('❌ Ошибка при пересылке:', error);
        alert('Ошибка при пересылке сообщений');
      }
    };
    
    return (
      <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
        <div className="bg-gray-900 rounded-lg border border-gray-800 w-full max-w-md p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-white">
              Переслать сообщения
            </h3>
            <button
              onClick={() => {
                setShowForwardModal(false);
                setForwardMessages([]);
                setSelectedChatsForForward([]);
              }}
              className="p-2 rounded hover:bg-gray-800 text-gray-400"
            >
              <GoX className="w-5 h-5" />
            </button>
          </div>
          
          <div className="mb-4">
            <p className="text-gray-300 mb-2">
              Пересылается {forwardMessages.length} сообщение(й)
            </p>
          </div>
          
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Выберите чаты для пересылки
            </label>
            <div className="space-y-2 max-h-32 overflow-y-auto">
              {chats
                .filter(chat => chat.id !== currentChat?.id)
                .map(chat => (
                <label key={chat.id} className="flex items-center gap-2 p-2 hover:bg-gray-800 rounded cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedChatsForForward.includes(chat.id)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedChatsForForward(prev => [...prev, chat.id]);
                      } else {
                        setSelectedChatsForForward(prev => prev.filter(id => id !== chat.id));
                      }
                    }}
                    className="rounded border-gray-700 bg-gray-800 text-purple-600"
                  />
                  <span className="text-gray-300 text-sm">{chat.name}</span>
                </label>
              ))}
            </div>
          </div>
          
          <div className="flex gap-2">
            <button
              onClick={() => {
                setShowForwardModal(false);
                setForwardMessages([]);
                setSelectedChatsForForward([]);
              }}
              className="flex-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded text-gray-300 hover:bg-gray-700 text-sm"
            >
              Отмена
            </button>
            <button
              onClick={handleForwardToChats}
              disabled={!selectedChatsForForward.length}
              className="flex-1 px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50 text-sm"
            >
              Переслать
            </button>
          </div>
        </div>
      </div>
    );
  };

  // 🔥 ИНФОРМАЦИЯ О ВЫБРАННЫХ СООБЩЕНИЯХ
  const SelectedMessagesInfo = () => {
    if (selectedMessages.length === 0) return null;
    
    return (
      <div className="fixed bottom-20 left-1/2 transform -translate-x-1/2 bg-gray-900 border border-gray-700 rounded-lg p-3 shadow-lg z-40">
        <div className="flex items-center gap-3">
          <div className="text-white text-sm">
            Выбрано: {selectedMessages.length}
          </div>
          <button
            onClick={() => {
              setForwardMessages(selectedMessages);
              setShowForwardModal(true);
            }}
            className="px-3 py-1 bg-gray-800 rounded text-gray-300 hover:bg-gray-700 text-xs"
          >
            Переслать
          </button>
          <button
            onClick={() => setSelectedMessages([])}
            className="px-3 py-1 bg-gray-800 rounded text-gray-300 hover:bg-gray-700 text-xs"
          >
            Отменить
          </button>
        </div>
      </div>
    );
  };

  // 🔥 ЗАГРУЗЧИК
  if (isLoading) {
    return (
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-4 h-full flex flex-col">
        <div className="flex items-center gap-4 p-4 border-b border-gray-800">
          <div className="animate-pulse bg-gray-700 rounded-full w-10 h-10"></div>
          <div className="flex-1">
            <div className="animate-pulse bg-gray-700 rounded h-4 w-32 mb-2"></div>
            <div className="animate-pulse bg-gray-800 rounded h-3 w-24"></div>
          </div>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-purple-600 mx-auto mb-3"></div>
            <p className="text-gray-400 text-sm">Загрузка сообщений...</p>
          </div>
        </div>
      </div>
    );
  }

  // 🔥 ПУСТОЙ ЧАТ
  if (!currentChat) {
    return (
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-6 h-full flex flex-col items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 rounded-full bg-gray-800 flex items-center justify-center mx-auto mb-4">
            <GoComment className="text-3xl text-gray-500" />
          </div>
          <h3 className="text-xl font-bold text-white mb-2">Выберите чат</h3>
          <p className="text-gray-400 text-sm">
            Выберите чат из списка, чтобы начать общение
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="bg-gray-900 rounded-lg border border-gray-800 h-full flex flex-col overflow-hidden min-h-0">
        {/* Шапка чата */}
        <div className="sticky top-[70px] z-10 bg-gray-900 border-b border-gray-800 lg:static lg:z-auto">
          <div className="p-3 sm:p-4 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
            {onBack && (
            <button 
              onClick={onBack}
              className="p-2 rounded hover:bg-gray-800 text-gray-400 flex-shrink-0 lg:hidden"
              title="Назад"
            >
              <GoArrowLeft className="w-5 h-5" />
            </button>
            )}
            
            <div className="flex items-center gap-2 min-w-0 flex-1">
              <div className="relative flex-shrink-0">
                <div className="w-10 h-10 rounded-full bg-gradient-to-r from-purple-600 to-pink-600 flex items-center justify-center text-white font-bold">
                  {currentChat.name?.charAt(0).toUpperCase() || 'C'}
                </div>
                {currentChat.is_active && (
                  <div className="absolute -bottom-1 -right-1 w-2.5 h-2.5 bg-green-500 rounded-full border border-gray-900"></div>
                )}
              </div>
              
              <div className="min-w-0">
                <h3 className="text-base font-semibold text-white truncate">
                  {currentChat.name || 'Без названия'}
                </h3>
                <div className="text-xs text-gray-400">
     
                  {typingUsers[currentChat.id]?.length > 0 ? (
                    <TypingIndicatorComponent chatId={currentChat.id} />
       
                    
                  ) : (
                    <span>{currentChat.participants_count || 1} участников</span>
                  )}
                </div>

              </div>
            </div>
 
          </div>
          
          <div className="flex items-center gap-1 flex-shrink-0">
            {currentChat.type !== 'private' && (
              <button
                type="button"
                onClick={() => setShowParticipantsPanel(true)}
                className="p-2 rounded hover:bg-gray-800 text-purple-300"
                title="Участники: поиск и добавление в группу"
              >
                <FaUserFriends className="w-4 h-4" />
              </button>
            )}
            <button 
              onClick={handleClearChatHistory}
              className="p-2 rounded hover:bg-red-900/20 text-red-400"
              title="Очистить историю"
            >
              <FaTrash className="w-4 h-4" />
            </button>
          </div>

          </div>
          <div className="px-3 sm:px-4 pb-2">
        {/* ПРЕВЬЮ ОТВЕТА */}
        <ReplyPreview />
        
        {/* ФОРМА РЕДАКТИРОВАНИЯ */}
        <EditMessageForm />  
          </div>
        </div>
                                    
        {/* Панель участников для групп и каналов */}
        {currentChat.type !== 'private' && (
          <div className="border-b border-gray-800 px-4 py-2 flex items-center justify-between text-xs text-gray-400">
            <button
              type="button"
              onClick={() => setShowParticipantsPanel(prev => !prev)}
              className="flex items-center gap-2 text-gray-300 hover:text-white"
            >
              <span className="font-medium">
                Участники: {currentChat.participants_count ?? participants.length ?? 0}
              </span>
              <span className="text-[10px] uppercase tracking-wide">
                {showParticipantsPanel ? 'скрыть' : 'показать'}
              </span>
            </button>
            {canManageParticipants && currentUserRole && (
              <span className="text-[10px] uppercase tracking-wide text-purple-300">
                Ваша роль: {String(currentUserRole).toLowerCase() === 'owner' ? 'владелец' : 'администратор'}
              </span>
            )}
          </div>
        )}

        {showParticipantsPanel && currentChat.type !== 'private' && (
          <div className="px-4 py-3 border-b border-gray-800 bg-gray-900/70">
            <div className="flex flex-col gap-3">
              {/* Список участников */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-gray-400">Список участников</span>
                  {participantsLoading && (
                    <span className="text-[10px] text-gray-500">Загрузка...</span>
                  )}
                </div>
                {participantsError && (
                  <div className="text-xs text-red-400 mb-2">{participantsError}</div>
                )}
                <div className="max-h-40 overflow-y-auto space-y-1 pr-1 text-xs">
                  {participants.length === 0 && !participantsLoading && (
                    <div className="text-gray-500">Пока нет данных об участниках.</div>
                  )}
                  {participants.map((p) => {
                    const isMe = currentUserId && String(p.user_id) === String(currentUserId)
                    const roleLabel = String(p.role || '').toLowerCase() === 'owner'
                      ? 'Владелец'
                      : String(p.role || '').toLowerCase() === 'admin'
                        ? 'Админ'
                        : 'Участник'

                    const canRemoveThisUser =
                      canManageParticipants &&
                      !isMe &&
                      String(p.role || '').toLowerCase() !== 'owner'

                    return (
                      <div
                        key={p.id || p.user_id}
                        className="flex items-center justify-between py-1 border-b border-gray-800/60 last:border-b-0"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <div className="w-6 h-6 rounded-full bg-gradient-to-r from-blue-600 to-teal-600 flex items-center justify-center text-[10px] text-white">
                            {(p.username || p.user_id)?.toString().charAt(0).toUpperCase() || 'U'}
                          </div>
                          <div className="flex flex-col min-w-0">
                            <span className="text-gray-200 truncate">
                              {p.username || `user #${p.user_id}`}{isMe ? ' (вы)' : ''}
                            </span>
                            <span className="text-[10px] text-gray-500">{roleLabel}</span>
                          </div>
                        </div>
                        {canRemoveThisUser && (
                          <button
                            type="button"
                            onClick={() => handleRemoveUserFromChat(p)}
                            className="text-[11px] text-red-400 hover:text-red-300 px-2 py-1 rounded hover:bg-red-900/20"
                          >
                            Удалить
                          </button>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Поиск и добавление новых участников (только владелец / админ; бэкенд POST /chats/{id}/users) */}
              {canManageParticipants && (
                <form onSubmit={handleSearchUsers} className="space-y-2">
                  <span className="text-xs text-gray-400">Добавить участников</span>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={userSearchQuery}
                      onChange={(e) => setUserSearchQuery(e.target.value)}
                      className="flex-1 px-3 py-1.5 bg-gray-800 border border-gray-700 rounded text-xs text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
                      placeholder="Найти пользователя по имени или нику"
                    />
                    <button
                      type="submit"
                      disabled={!userSearchQuery.trim() || userSearchLoading}
                      className="px-3 py-1.5 bg-purple-600 text-white text-xs rounded hover:bg-purple-700 disabled:opacity-50"
                    >
                      {userSearchLoading ? 'Поиск...' : 'Найти'}
                    </button>
                  </div>
                  {userSearchError && (
                    <div className="text-[11px] text-red-400">{userSearchError}</div>
                  )}
                  {userSearchResults.length > 0 && (
                    <div className="max-h-32 overflow-y-auto border border-gray-800 rounded p-2 space-y-1 text-xs bg-gray-900/80">
                      {userSearchResults.map((user) => (
                        <button
                          key={user.user_id}
                          type="button"
                          onClick={() => handleAddUserToChat(user)}
                          className="w-full flex items-center justify-between py-1 px-2 rounded hover:bg-gray-800 text-left"
                        >
                          <span className="truncate text-gray-200">
                            {user.username || `${user.name || ''} ${user.lastname || ''}`.trim() || `user #${user.user_id}`}
                          </span>
                          <span className="text-[10px] text-purple-300 ml-2">
                            Добавить
                          </span>
                        </button>
                      ))}
                    </div>
                  )}
                </form>
              )}
            </div>
          </div>
        )}

       

        {/* Область сообщений */}
        <div 
          ref={messagesContainerRef}
          className="flex-1 min-h-0 p-2 overflow-y-auto bg-gray-900/50"
        >
          {groupMessagesByDate.length > 0 ? (
            <div className="space-y-4">
              {groupMessagesByDate.map((item) => {
                if (item.type === 'date') {
                  return (
                    <div key={item.key} className="flex justify-center my-3">
                      <div className="bg-gray-800 text-gray-400 text-xs px-3 py-1 rounded-full">
                        {item.date}
                      </div>
                    </div>
                  );
                }
                
                const message = item.data;
                const isOwn = isOwnMessage(message);
                const isPinned = pinnedMessages.some(m => m.id === message.id);
                const isSelected = selectedMessages.some(m => m.id === message.id);
                
                return (
                  <MessageContextMenu key={item.key} message={message}>
                    <div className={`relative ${isSelected ? 'ring-1 ring-blue-500 rounded-lg' : ''}`}>
                      {isPinned && (
                        <div className="absolute -top-1 -right-1 bg-yellow-500 text-white text-xs px-2 py-0.5 rounded-full flex items-center">
                          <TbPinFilled className="w-3 h-3" />
                        </div>
                      )}
                      
                      <div className={`flex ${isOwn ? 'justify-end' : 'justify-start'} items-end gap-2`}>
                        {!isOwn && (
                          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-r from-blue-600 to-teal-600 flex items-center justify-center text-white text-xs overflow-hidden">
                            {normalizeAssetUrl(message.avatar_url) ? (
                              <img
                                src={normalizeAssetUrl(message.avatar_url)}
                                alt={message.sender_name || message.username || 'User'}
                                className="w-full h-full object-cover"
                              />
                            ) : (
                              message.sender_name?.charAt(0) || message.username?.charAt(0) || 'U'
                            )}
                          </div>
                        )}
                        
                        <div className={`max-w-[80%] rounded-lg p-3 ${
                          isOwn 
                            ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white' 
                            : 'bg-gray-800 text-gray-200'
                        }`} data-message-id={message.id}>
                          
                          {!isOwn && (
                            <div className="font-semibold text-xs mb-1 text-blue-300">
                            {message.sender_name || message.username || [message.name, message.lastname].filter(Boolean).join(' ') || 'Пользователь'}
                            </div>
                          )}

                          {/* Превью сообщения, на которое отвечаем (если есть) */}
                          {message.reply_to && (
                            <div className={`mb-2 p-2 rounded text-xs ${
                              isOwn ? 'bg-purple-700/40 text-purple-50' : 'bg-gray-700/60 text-gray-100'
                            }`}>
                              <div className="flex items-center gap-1 mb-1 text-[10px] uppercase tracking-wide opacity-80">
                                <FaReply className="w-3 h-3" />
                                <span>Ответ на сообщение</span>
                              </div>
                              <div className="line-clamp-2 whitespace-pre-wrap">
                                {message.reply_to.content}
                              </div>
                            </div>
                          )}
                          
                          <div className="mb-2 whitespace-pre-wrap text-sm">
                            {message.content}
                          </div>
                          {Array.isArray(message.media_urls) && message.media_urls.length > 0 && (
                            <div className="mb-2 space-y-2">
                              {message.media_urls.map((media, idx) => {
                                const url = getMediaUrl(media)
                                if (!url) return null
                                const kind = getMediaKind(media, url)
                                const filename = getMediaFilename(media, url)
                                const fileSize = formatFileSize(media?.size)

                                if (kind === 'video') {
                                  return (
                                    <video
                                      key={idx}
                                      src={url}
                                      controls
                                      preload="metadata"
                                      className="max-h-56 rounded-lg border border-gray-700"
                                    />
                                  )
                                }

                                if (kind === 'image') {
                                  return (
                                    <a key={idx} href={url} target="_blank" rel="noreferrer" className="inline-block">
                                      <img src={url} alt={filename} className="max-h-56 rounded-lg border border-gray-700" />
                                    </a>
                                  )
                                }

                                return (
                                  <div key={idx} className={`rounded-lg border px-3 py-2 ${isOwn ? 'border-purple-300/40 bg-black/10' : 'border-gray-700 bg-gray-900/40'}`}>
                                    {(() => {
                                      const fileCategory = getFileCategory(media, url)
                                      const FileIcon = fileCategory.icon
                                      const isPdf = fileCategory.kind === 'pdf'
                                      return (
                                        <>
                                          <div className="flex items-center gap-2 mb-2">
                                            <FileIcon className="w-4 h-4 opacity-80" />
                                            <div className="text-xs truncate flex-1" title={filename}>{filename}</div>
                                          </div>
                                          <div className="text-[11px] opacity-80 mb-2">
                                            {fileCategory.label}
                                            {fileSize ? ` · ${fileSize}` : ''}
                                          </div>
                                          <div className="flex items-center gap-2">
                                            {isPdf && (
                                              <button
                                                type="button"
                                                onClick={() => setPdfPreview({ isOpen: true, url, title: filename })}
                                                className="inline-flex items-center rounded px-2 py-1 text-xs bg-purple-700/70 hover:bg-purple-700"
                                              >
                                                Открыть PDF
                                              </button>
                                            )}
                                            <a
                                              href={url}
                                              target="_blank"
                                              rel="noreferrer"
                                              download={filename}
                                              className="inline-flex items-center rounded px-2 py-1 text-xs bg-gray-800 hover:bg-gray-700"
                                            >
                                              Скачать файл
                                            </a>
                                          </div>
                                        </>
                                      )
                                    })()}
                                  </div>
                                )
                              })}
                            </div>
                          )}
                          
                          <div className={`text-xs flex items-center justify-between ${
                            isOwn ? 'text-purple-200' : 'text-gray-400'
                          }`}>
                            <div className="flex items-center gap-2">
                              <button
                                type="button"
                                onClick={() => handleToggleLike(message)}
                                className="inline-flex items-center gap-1 hover:opacity-80"
                                title="Лайк"
                              >
                                {message.is_liked_by_user ? <FaHeart className="w-3 h-3 text-pink-400" /> : <FaRegHeart className="w-3 h-3" />}
                                <span>{message.likes_count || 0}</span>
                              </button>
                              <span>{formatMessageTime(message.timestamp || message.created_at)}</span>
                            </div>
                            
                            {isOwn && (
                              <div className="ml-2">
                                {isMessageRead(message) ? (
                                  <IoCheckmarkDoneOutline className='w-4 h-4' />
                                ) : (
                                  <svg className="w-3 h-3 opacity-60" fill="currentColor" viewBox="0 0 20 20">
                                    <path d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"/>
                                  </svg>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                        
                        {isOwn && (
                          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-r from-purple-600 to-pink-600 flex items-center justify-center text-white text-xs">
                            {message.sender_name?.charAt(0) || 'Y'}
                          </div>
                        )}
                      </div>
                    </div>
                  </MessageContextMenu>
                );
              })}
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center p-6">
              <div className="w-16 h-16 rounded-full bg-gray-800 flex items-center justify-center mx-auto mb-4">
                <GoComment className="text-3xl text-gray-500" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2">Нет сообщений</h3>
              <p className="text-gray-400 text-sm text-center">
                Отправьте первое сообщение в этот чат!
              </p>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Форма ввода сообщения + медиа */}
        <div className="p-3 border-t border-gray-800">
          {currentChat?.type === 'channel' && !canWriteInChannel ? (
            <div className="py-4 px-3 bg-gray-800/50 rounded-lg border border-gray-700 text-center">
              {channelWriteCheckLoading ? (
                <p className="text-gray-400 text-sm">Проверка доступа...</p>
              ) : (
                <p className="text-gray-400 text-sm">
                  Писать в канал могут только участники проекта. Вы подписаны на канал и можете читать сообщения.
                </p>
              )}
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-2">
              {attachedFiles.length > 0 && (
                <div className="flex flex-wrap gap-2 text-xs text-gray-300">
                  {attachedFiles.map((file, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-1 bg-gray-800 rounded border border-gray-700 max-w-[200px] truncate"
                      title={file.name}
                    >
                      {file.name}
                    </span>
                  ))}
                </div>
              )}
              <div className="flex items-center gap-2">
                <label className="p-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 cursor-pointer hover:bg-gray-700">
                  <GoPaperclip className="w-5 h-5" />
                  <input
                    type="file"
                    multiple
                    className="hidden"
                    onChange={handleFileChange}
                  />
                </label>
                <input 
                  ref={inputRef}
                  type="text"
                  value={messageInput}
                  onChange={(e) => {
                    const nextValue = e.target.value
                    setMessageInput(nextValue)

                    if (!currentChat?.id) return

                    // отправляем "печатает" не чаще, чем раз в 700мс
                    const now = Date.now()
                    if (nextValue.trim().length > 0 && now - lastTypingSignalAtRef.current > 700) {
                      lastTypingSignalAtRef.current = now
                      handleTyping(currentChat.id, true)
                    }

                    // дебаунс "перестал печатать"
                    if (typingStopTimerRef.current) {
                      clearTimeout(typingStopTimerRef.current)
                    }
                    typingStopTimerRef.current = setTimeout(() => {
                      if (currentChat?.id) {
                        handleTyping(currentChat.id, false)
                      }
                    }, 1200)
                  }}
                  className="flex-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg 
                           text-white placeholder-gray-500 text-sm
                           focus:outline-none focus:border-purple-500"
                  placeholder="Введите сообщение..."
                  disabled={isSending || isSendingMedia}
                />
                
                <button
                  type="submit"
                  disabled={(!messageInput.trim() && attachedFiles.length === 0) || isSending || isSendingMedia}
                  className="px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg
                           hover:opacity-90 disabled:opacity-50 text-sm"
                >
                  {isSending || isSendingMedia ? '...' : 'Отпр'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>

      {/* МОДАЛКА ПЕРЕСЫЛКИ */}
      <ForwardModal />
      
      {/* ИНФОРМАЦИЯ О ВЫБРАННЫХ СООБЩЕНИЯХ */}
      <SelectedMessagesInfo />

      {pdfPreview.isOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 p-4 flex items-center justify-center">
          <div className="w-full max-w-5xl h-[85vh] bg-gray-900 border border-gray-700 rounded-lg overflow-hidden flex flex-col">
            <div className="px-4 py-3 border-b border-gray-700 flex items-center justify-between">
              <div className="text-sm text-gray-200 truncate" title={pdfPreview.title}>
                {pdfPreview.title || 'PDF'}
              </div>
              <button
                type="button"
                onClick={() => setPdfPreview({ isOpen: false, url: '', title: '' })}
                className="p-2 rounded hover:bg-gray-800 text-gray-300"
              >
                <GoX className="w-4 h-4" />
              </button>
            </div>
            <iframe
              src={pdfPreview.url}
              title={pdfPreview.title || 'PDF preview'}
              className="w-full h-full bg-white"
            />
          </div>
        </div>
      )}
    </>
  );
}