import React, { useState, useEffect, useCallback } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import { createChat } from '../../store/slices/chatSlice'
import Header from '../../ui/Header'
import { 
  FaComments, 
  FaUserFriends, 
  FaSearch, 
  FaTimes, 
  FaUser,
  FaGraduationCap,
  FaHashtag
} from "react-icons/fa"
import { normalizeAssetUrl, searchAPI } from '../../services/api'
import debounce from 'lodash/debounce'

export default function AddChat() {
    const navigate = useNavigate()
    const dispatch = useDispatch()

    const [name, setName] = useState('')
    const [type, setType] = useState('private')
    const [loading, setLoading] = useState(false)
    const [searchQuery, setSearchQuery] = useState('')
    const [searchResults, setSearchResults] = useState([])
    const [selectedUser, setSelectedUser] = useState(null)
    const [isSearching, setIsSearching] = useState(false)
    const [searchError, setSearchError] = useState('')
    const { profile } = useSelector(state => state.profile)
    const userId = profile?.user_id

    // Дебаунс поиска пользователей (500ms)
    const debouncedSearch = useCallback(
        debounce(async (query) => {
            if (!query.trim() || query.length < 1) {
                setSearchResults([])
                setSearchError('')
                return
            }
            
            setIsSearching(true)
            setSearchError('')
            
            try {
                const response = await searchAPI.searchUsers(query, 1, 10)
                const data = response.data
                
                // Фильтруем себя из результатов
                const filteredResults = data.profiles.filter(user => 
                    user.user_id !== userId
                )
                
                setSearchResults(filteredResults)
                
                if (filteredResults.length === 0) {
                    setSearchError('Пользователи не найдены')
                }
                
            } catch (error) {
                console.error('❌ Ошибка поиска пользователей:', error)
                setSearchResults([])
                setSearchError('Ошибка при поиске пользователей')
            } finally {
                setIsSearching(false)
            }
        }, 500),
        [userId]
    )

    // Обработка изменения поискового запроса
    useEffect(() => {
        debouncedSearch(searchQuery)
        return () => debouncedSearch.cancel()
    }, [searchQuery, debouncedSearch])

    // Очистка результатов при смене типа чата
    useEffect(() => {
        if (type !== 'private') {
            setSearchResults([])
            setSearchQuery('')
            setSelectedUser(null)
        }
    }, [type])

async function handleSubmitChat(e) {
    e.preventDefault()
    
    // Валидация
    if (type === 'private' && !selectedUser) {
        alert('Выберите пользователя для приватного чата')
        return
    }

    if (type !== 'private' && !name.trim()) {
        alert('Введите название чата')
        return
    }

    // Для приватных чатов используем username собеседника как название
    const chatName = type === 'private' 
        ? selectedUser.username || `Чат с ${selectedUser.name}`
        : name.trim()

    // 🔥 ИСПРАВЛЕННЫЙ ФОРМАТ ДАННЫХ
    const chatData = {
        data: {
            name: chatName,
            type: type, // 'private', 'group', 'channel'
        },
        members: type === 'private' ? [selectedUser.user_id] : []
    }

    console.log('📤 Отправляемые данные:', JSON.stringify(chatData, null, 2))

    setLoading(true)

    try {
        const response = await dispatch(createChat(chatData))
        
        if (response.payload) {
            console.log('✅ Чат создан:', response.payload)
            navigate('/chats')
        } else {
            // Проверяем, есть ли ошибка в ответе
            if (response.error) {
                const errorMsg = response.error.message || 'Неизвестная ошибка'
                alert(`Ошибка: ${errorMsg}`)
            } else {
                alert('Не удалось создать чат')
            }
        }
        
    } catch (error) {
        console.error('❌ Ошибка создания чата:', error)
        
        // Детальная обработка ошибок
        if (error.status === 401) {
            alert('Вы не авторизованы. Пожалуйста, войдите в систему.')
            navigate('/login')
        } else if (error.status === 400) {
            const detail = error.data?.detail
            if (Array.isArray(detail)) {
                // Ошибки валидации FastAPI
                const errorMessages = detail.map(err => 
                    `${err.loc?.join('.')}: ${err.msg}`
                ).join('\n')
                alert(`Ошибка валидации:\n${errorMessages}`)
            } else if (typeof detail === 'string') {
                alert(`Ошибка: ${detail}`)
            } else {
                alert('Некорректные данные для создания чата')
            }
        } else if (error.status === 409) {
            alert('Приватный чат с этим пользователем уже существует')
        } else if (error.status === 404) {
            alert('Пользователь не найден')
        } else {
            alert('Неизвестная ошибка при создании чата')
        }
    } finally {
        setLoading(false)
    }
}

    const handleUserSelect = (user) => {
        setSelectedUser(user)
        setSearchQuery(user.username || `${user.name} ${user.lastname}`)
        setSearchResults([])
        setSearchError('')
    }

    const clearSelectedUser = () => {
        setSelectedUser(null)
        setSearchQuery('')
        setSearchResults([])
        setSearchError('')
    }

    const getInitials = (user) => {
        if (user.name && user.lastname) {
            return `${user.name.charAt(0)}${user.lastname.charAt(0)}`.toUpperCase()
        }
        return user.username?.charAt(0).toUpperCase() || 'U'
    }

    const getUserDisplayName = (user) => {
        if (user.username) return user.username
        if (user.name && user.lastname) return `${user.name} ${user.lastname}`
        return `Пользователь #${user.user_id}`
    }

    return (
        <Header>
            <div className="bg-white dark:bg-black py-8 min-h-screen">
                <div className="max-w-md mx-auto">
                    {/* Заголовок */}
                    <div className="text-center mb-8">
                        <h1 className="text-3xl font-bold text-white mb-2">
                            {type === 'private' ? 'Новый диалог' : 
                             type === 'group' ? 'Новая группа' : 'Новый канал'}
                        </h1>
                        <p className="text-gray-400">
                            {type === 'private' 
                                ? 'Начните приватное общение' 
                                : type === 'group'
                                ? 'Создайте группу для совместной работы'
                                : 'Создайте канал для публичных объявлений'}
                        </p>
                    </div>

                    <form className="space-y-6" onSubmit={handleSubmitChat}>
                        {/* Основной блок */}
                        <div className="bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-800 p-6 hover:border-gray-700 transition-all duration-300">
                            <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                                {type === 'private' ? (
                                    <>
                                        <FaUserFriends className="text-purple-400" />
                                        <span>Выберите собеседника</span>
                                    </>
                                ) : (
                                    <>
                                        <FaComments className="text-purple-400" />
                                        <span>Настройки чата</span>
                                    </>
                                )}
                            </h2>
                            
                            <div className="space-y-6">
                                {/* Выбор типа чата */}
                                <div>
                                    <label className="block text-gray-300 text-sm font-medium mb-3">
                                        Тип чата
                                    </label>
                                    <div className="grid grid-cols-3 gap-3">
                                        {[
                                            { type: 'private', label: 'Приватный', icon: FaUserFriends },
                                            { type: 'group', label: 'Группа', icon: FaComments }
                                        ].map((chatType) => (
                                            <button
                                                key={chatType.type}
                                                type="button"
                                                onClick={() => {
                                                    setType(chatType.type)
                                                    setSelectedUser(null)
                                                    setName('')
                                                    setSearchQuery('')
                                                    setSearchResults([])
                                                }}
                                                className={`flex flex-col items-center justify-center p-4 rounded-xl border transition-all duration-300 ${
                                                    type === chatType.type 
                                                        ? 'bg-purple-600 border-purple-500 text-white shadow-lg shadow-purple-500/30' 
                                                        : 'bg-gray-800/50 border-gray-700 text-gray-300 hover:border-gray-600 hover:bg-gray-800/80'
                                                }`}
                                                disabled={loading}
                                            >
                                                <chatType.icon className="w-6 h-6 mb-2" />
                                                <span className="text-sm font-medium">{chatType.label}</span>
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                {/* Для приватных чатов - поиск пользователей */}
                                {type === 'private' ? (
                                    <>
                                        {/* Выбранный пользователь */}
                                        {selectedUser ? (
                                            <div className="bg-gradient-to-r from-purple-900/20 to-pink-900/20 border border-purple-800/50 rounded-xl p-4">
                                                <div className="flex items-center justify-between">
                                                    <div className="flex items-center gap-3">
                                                        {normalizeAssetUrl(selectedUser.avatar_url || selectedUser.avatar_path) ? (
                                                            <img 
                                                                src={normalizeAssetUrl(selectedUser.avatar_url || selectedUser.avatar_path)}
                                                                alt={selectedUser.username}
                                                                className="w-12 h-12 rounded-full border-2 border-purple-500"
                                                                onError={(e) => {
                                                                    e.target.style.display = 'none'
                                                                    e.target.parentElement.querySelector('.avatar-fallback').style.display = 'flex'
                                                                }}
                                                            />
                                                        ) : null}
                                                        <div className="avatar-fallback hidden w-12 h-12 rounded-full bg-gradient-to-r from-purple-600 to-pink-600 border-2 border-purple-500 flex items-center justify-center text-white font-bold text-lg">
                                                            {getInitials(selectedUser)}
                                                        </div>
                                                        <div>
                                                            <div className="text-white font-semibold">
                                                                {getUserDisplayName(selectedUser)}
                                                            </div>
                                                            {selectedUser.university && (
                                                                <div className="text-gray-400 text-sm flex items-center gap-1">
                                                                    <FaGraduationCap className="w-3 h-3" />
                                                                    {selectedUser.university}
                                                                </div>
                                                            )}
                                                        </div>
                                                    </div>
                                                    <button
                                                        type="button"
                                                        onClick={clearSelectedUser}
                                                        className="p-2 text-gray-400 hover:text-white hover:bg-gray-800/50 rounded-lg transition-colors"
                                                        title="Изменить выбор"
                                                    >
                                                        <FaTimes />
                                                    </button>
                                                </div>
                                            </div>
                                        ) : (
                                            /* Поле поиска пользователей */
                                            <div>
                                                <label className="block text-gray-300 text-sm font-medium mb-2">
                                                    Найдите пользователя *
                                                    <span className="text-gray-500 text-xs ml-2">
                                                        (поиск по имени, фамилии или никнейму)
                                                    </span>
                                                </label>
                                                <div className="relative">
                                                    <div className="relative">
                                                        <FaSearch className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-500" />
                                                        <input 
                                                            type="text"
                                                            value={searchQuery}
                                                            onChange={(e) => setSearchQuery(e.target.value)}
                                                            className="w-full pl-12 pr-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300"
                                                            placeholder="Введите имя, фамилию или никнейм..."
                                                            disabled={loading}
                                                            minLength={1}
                                                            maxLength={100}
                                                        />
                                                        {searchQuery && (
                                                            <button
                                                                type="button"
                                                                onClick={() => setSearchQuery('')}
                                                                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-white"
                                                            >
                                                                <FaTimes />
                                                            </button>
                                                        )}
                                                    </div>
                                                    
                                                    {/* Индикатор поиска */}
                                                    {isSearching && (
                                                        <div className="absolute inset-x-0 top-full mt-1 bg-gray-900 border border-gray-800 rounded-xl shadow-lg p-4">
                                                            <div className="flex items-center justify-center gap-2 text-gray-400">
                                                                <div className="w-4 h-4 border-2 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
                                                                Поиск пользователей...
                                                            </div>
                                                        </div>
                                                    )}
                                                    
                                                    {/* Результаты поиска */}
                                                    {!isSearching && searchQuery.length >= 1 && searchResults.length > 0 && (
                                                        <div className="absolute z-10 w-full mt-2 bg-gray-900 border border-gray-800 rounded-xl shadow-2xl max-h-80 overflow-y-auto">
                                                            {searchResults.map((user) => (
                                                                <div
                                                                    key={user.user_id}
                                                                    onClick={() => handleUserSelect(user)}
                                                                    className="p-3 hover:bg-gray-800 cursor-pointer transition-colors border-b border-gray-800 last:border-b-0"
                                                                >
                                                                    <div className="flex items-center gap-3">
                                                                        {/* Аватар */}
                                                                        <div className="relative">
                                                                            {normalizeAssetUrl(user.avatar_url || user.avatar_path) ? (
                                                                                <img 
                                                                                    src={normalizeAssetUrl(user.avatar_url || user.avatar_path)}
                                                                                    alt={user.username}
                                                                                    className="w-10 h-10 rounded-full border border-gray-700"
                                                                                    onError={(e) => {
                                                                                        e.target.style.display = 'none'
                                                                                        e.target.nextElementSibling.style.display = 'flex'
                                                                                    }}
                                                                                />
                                                                            ) : null}
                                                                            <div className="hidden w-10 h-10 rounded-full bg-gradient-to-r from-blue-600 to-teal-600 flex items-center justify-center text-white font-bold text-sm border border-gray-700">
                                                                                {getInitials(user)}
                                                                            </div>
                                                                        </div>
                                                                        
                                                                        {/* Информация о пользователе */}
                                                                        <div className="flex-1 min-w-0">
                                                                            <div className="flex items-center gap-2">
                                                                                <div className="text-white font-medium truncate">
                                                                                    {getUserDisplayName(user)}
                                                                                </div>
                                                                                {user.course && (
                                                                                    <span className="text-xs bg-blue-900/30 text-blue-300 px-1.5 py-0.5 rounded">
                                                                                        {user.course} курс
                                                                                    </span>
                                                                                )}
                                                                            </div>
                                                                            
                                                                            {/* Дополнительная информация */}
                                                                            <div className="text-gray-400 text-sm space-y-1">
                                                                                {user.university && (
                                                                                    <div className="flex items-center gap-1 truncate">
                                                                                        <FaGraduationCap className="w-3 h-3 flex-shrink-0" />
                                                                                        <span className="truncate">{user.university}</span>
                                                                                    </div>
                                                                                )}
                                                                                {user.faculty && (
                                                                                    <div className="truncate">{user.faculty}</div>
                                                                                )}
                                                                            </div>
                                                                        </div>
                                                                    </div>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    )}
                                                    
                                                    {/* Сообщение об ошибке */}
                                                    {!isSearching && searchError && (
                                                        <div className="absolute inset-x-0 top-full mt-1 bg-gray-900 border border-red-800/50 rounded-xl shadow-lg p-4">
                                                            <div className="text-red-400 text-sm text-center">
                                                                {searchError}
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                                
                                                {/* Подсказка */}
                                                {!searchQuery && (
                                                    <div className="mt-3 text-gray-500 text-sm">
                                                        <p className="mb-2">💡 Советы по поиску:</p>
                                                        <ul className="list-disc list-inside space-y-1">
                                                            <li>Имя или фамилия: "Иван", "Петров"</li>
                                                            <li>Никнейм: "@ivan", "petrov_ivan"</li>
                                                            <li>Университет: "МГУ", "СПбГУ"</li>
                                                        </ul>
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </>
                                ) : (
                                    /* Для групповых чатов и каналов - поле названия */
                                    <div>
                                        <label className="block text-gray-300 text-sm font-medium mb-2">
                                            Название {type === 'group' ? 'группы' : 'канала'} *
                                            <span className="text-gray-500 text-xs ml-2">
                                                (можно изменить позже)
                                            </span>
                                        </label>
                                        <input 
                                            type="text"
                                            value={name}
                                            onChange={(e) => setName(e.target.value)}
                                            required
                                            className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300"
                                            placeholder={type === 'group' ? 'Например: Команда проекта, Друзья' : 'Например: Новости, Анонсы'}
                                            disabled={loading}
                                            minLength={1}
                                            maxLength={100}
                                        />
                                        <div className="mt-2 text-gray-500 text-sm">
                                            {type === 'group' 
                                                ? 'Выберите понятное название для участников группы'
                                                : 'Название канала будет видно всем подписчикам'}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                        
                        {/* Кнопки действий */}
                        <div className="flex flex-col sm:flex-row gap-4">
                            <button
                                type="button"
                                onClick={() => navigate('/chats')}
                                className="flex-1 px-6 py-3 bg-gray-800/50 border border-gray-700 text-gray-300 font-medium rounded-xl hover:bg-gray-800 hover:text-white transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
                                disabled={loading}
                            >
                                Отмена
                            </button>
                            
                            <button 
                                type="submit"
                                disabled={loading || (type === 'private' && !selectedUser) || (type !== 'private' && !name.trim())}
                                className={`flex-1 px-6 py-3 text-white font-bold rounded-xl transition-all duration-300 hover:shadow-lg ${
                                    loading || (type === 'private' && !selectedUser) || (type !== 'private' && !name.trim())
                                        ? 'bg-gray-600 cursor-not-allowed shadow-none' 
                                        : 'bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 shadow-purple-500/20 hover:shadow-purple-500/40'
                                }`}
                            >
                                {loading ? (
                                    <span className="flex items-center justify-center gap-2">
                                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                        {type === 'private' ? 'Создание...' : 'Создание...'}
                                    </span>
                                ) : (
                                    type === 'private' ? 'Начать диалог →' : 'Создать чат →'
                                )}
                            </button>
                        </div>
                        
                        {/* Информационная панель */}
                        <div className="bg-gray-900/50 rounded-xl p-4 border border-gray-800">
                            <div className="flex items-start gap-3">
                                <div className="text-purple-400 mt-0.5">
                                    {type === 'private' ? <FaUserFriends /> : 
                                     type === 'group' ? <FaComments /> : <FaHashtag />}
                                </div>
                                <div className="text-sm text-gray-300">
                                    <h4 className="font-medium mb-1">
                                        {type === 'private' ? 'Приватный чат' : 
                                         type === 'group' ? 'Групповой чат' : 'Канал'}
                                    </h4>
                                    <p className="text-gray-400">
                                        {type === 'private' 
                                            ? 'Только вы и выбранный пользователь. Идеально для личных бесед.'
                                            : type === 'group'
                                            ? 'Доступ для всех приглашенных участников. Подходит для командной работы.'
                                            : 'Публичный доступ. Отлично подходит для новостей и анонсов.'}
                                    </p>
                                </div>
                            </div>
                        </div>
                    </form>
                </div>
            </div>
        </Header>
    )
}