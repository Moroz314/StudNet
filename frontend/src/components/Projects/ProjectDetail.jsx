import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { FiArrowLeft, FiUsers, FiCalendar, FiTag, FiMessageSquare, FiSettings, FiPlus, FiX, FiSearch, FiEdit2, FiLogOut, FiBriefcase } from 'react-icons/fi';
import Header from '../../ui/Header';
import { fetchProject, fetchProjectParticipants, createProjectInvitations, updateParticipantStatus, leaveProject, updateProject } from '../../store/slices/projects';
import { useUserSearch } from '../../hooks/useUserSearch';
import { channelAPI } from '../../services/api';
import { feedAPI } from '../../services/api';
import ProjectAnnouncementsTab from './ProjectAnnouncementsTab';

export default function ProjectDetail() {
    const { projectId } = useParams();
    const dispatch = useDispatch();
    const navigate = useNavigate();
    const { currentProject, isLoading, error } = useSelector(state => state.projects);
    const [activeTab, setActiveTab] = useState('overview');

    useEffect(() => {
        if (projectId) {
            dispatch(fetchProject(projectId));
            dispatch(fetchProjectParticipants(projectId));
        }
    }, [dispatch, projectId]);

      const categoryOptions = [
    { value: 'technology', label: 'Технологии и IT' },
    { value: 'science', label: 'Наука' },
    { value: 'mathematics', label: 'Математика' },
    { value: 'physics', label: 'Физика' },
    { value: 'chemistry', label: 'Химия' },
    { value: 'biology', label: 'Биология' },
    { value: 'medicine', label: 'Медицина' },
    { value: 'engineering', label: 'Инженерия' },
    { value: 'art', label: 'Искусство' },
    { value: 'design', label: 'Дизайн' },
    { value: 'music', label: 'Музыка' },
    { value: 'literature', label: 'Литература' },
    { value: 'linguistics', label: 'Лингвистика' },
    { value: 'history', label: 'История' },
    { value: 'philosophy', label: 'Философия' },
    { value: 'economics', label: 'Экономика' },
    { value: 'business', label: 'Бизнес' },
    { value: 'marketing', label: 'Маркетинг' },
    { value: 'education', label: 'Образование' },
    { value: 'environment', label: 'Экология' },
    { value: 'social', label: 'Социальные проекты' },
    { value: 'other', label: 'Другое' },
  ];

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    tags: [],
    create_chat: true,
    category: ''
  });

  const [newTag, setNewTag] = useState('');

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const addTag = () => {
    if (newTag.trim() && !formData.tags.includes(newTag.trim())) {
      setFormData(prev => ({
        ...prev,
        tags: [...prev.tags, newTag.trim()]
      }));
      setNewTag('');
    }
  };

  const removeTag = (tagToRemove) => {
    setFormData(prev => ({
      ...prev,
      tags: prev.tags.filter(tag => tag !== tagToRemove)
    }));
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addTag();
    }
  };


    const getStatusColor = (status) => {
        switch (status) {
            case 'active':
                return 'text-green-400 bg-green-900/20 border-green-800';
            case 'completed':
                return 'text-blue-400 bg-blue-900/20 border-blue-800';
            case 'archived':
                return 'text-gray-400 bg-gray-900/20 border-gray-800';
            default:
                return 'text-gray-400 bg-gray-900/20 border-gray-800';
        }
    };

    const getStatusText = (status) => {
        switch (status) {
            case 'active':
                return 'Активный';
            case 'completed':
                return 'Завершенный';
            case 'archived':
                return 'Архивированный';
            default:
                return status;
        }
    };

    const getParticipantStatusText = (status) => {
        switch (status) {
            case 'owner':
                return 'Владелец';
            case 'admin':
                return 'Администратор';
            case 'editor':
                return 'Редактор';
            case 'viewer':
                return 'Наблюдатель';
            default:
                return status;
        }
    };

    const { profile } = useSelector(state => state.profile);
    const currentUserId = profile?.user_id;
    const getUserProfileFromParticipant = (participant) => {
        const p = participant || {};
        const u = p.user_profile || p.invited_user || p.user || {};
        return {
            user_id: p.user_id ?? u.user_id,
            name: u.name ?? p.name,
            lastname: u.lastname ?? p.lastname,
            username: u.username ?? p.username,
            avatar_path: u.avatar_path ?? u.avatar_url ?? p.avatar_path ?? p.avatar_url,
        };
    };

    const participantsList = Array.isArray(currentProject?.participants) ? currentProject.participants : [];
    const currentParticipant = participantsList.find(p => p.user_id === currentUserId);
    const isCreator = currentProject?.created_by === currentUserId;
    const canManageParticipants = isCreator || currentParticipant?.status === 'owner' || currentParticipant?.status === 'admin';

    const displayParticipants = (() => {
        const list = [...participantsList];
        const creatorId = currentProject?.created_by;
        const hasCreator = creatorId && list.some(p => p.user_id === creatorId);
        if (!hasCreator && currentProject?.creator?.user_id) {
            list.unshift({
                id: `creator-${currentProject.creator.user_id}`,
                user_id: currentProject.creator.user_id,
                status: 'owner',
                joined_at: currentProject.created_at,
                user_profile: {
                    name: currentProject.creator.name,
                    lastname: currentProject.creator.lastname,
                    username: currentProject.creator.username,
                    avatar_path: currentProject.creator.avatar_path || currentProject.creator.avatar_url,
                }
            });
        }
        return list;
    })();

    
    const [showAddParticipantModal, setShowAddParticipantModal] = useState(false);
    const [selectedUsers, setSelectedUsers] = useState([]);
    const [showStatusModal, setShowStatusModal] = useState(false);
    const [selectedParticipant, setSelectedParticipant] = useState(null);
    const [isLeaving, setIsLeaving] = useState(false);
    const [showAddLinkModal, setShowAddLinkModal] = useState(false);
    const [showSettingsModal, setShowSettingsModal] = useState(false);
    const [newLinkUrl, setNewLinkUrl] = useState('');
    const [projectChannel, setProjectChannel] = useState(null);
    const [channelName, setChannelName] = useState('');
    const [channelDescription, setChannelDescription] = useState('');
    const [channelLoading, setChannelLoading] = useState(false);
    const [isPublishedToFeed, setIsPublishedToFeed] = useState(false);

    const { searchQuery, setSearchQuery, results, isSearching, error: searchError, searchUsers, clearSearch } = useUserSearch(currentUserId);
    
    useEffect(() => {
        if (searchQuery) {
            searchUsers(searchQuery);
        }
    }, [searchQuery, searchUsers]);

    useEffect(() => {
        if (!currentProject) return
        setFormData((prev) => ({
        name: currentProject.name || prev.name || '',           
        description: currentProject.description || prev.description || '',
        tags: currentProject.tags || prev.tags || [],
        category: currentProject.category || prev.category || '',
        }))
    }, [currentProject])

    useEffect(() => {
        const loadProjectChannel = async () => {
            if (!projectId) return;
            try {
                const response = await channelAPI.getProjectChannel(projectId);
                const data = response?.data || null;
                setProjectChannel(data);
                if (data) {
                    setChannelName(data.name || '');
                    setChannelDescription(data.description || '');
                }
            } catch (e) {
                setProjectChannel(null);
            }
        };
        loadProjectChannel();
    }, [projectId]);

    useEffect(() => {
        const checkPublished = async () => {
            if (!projectId) return;
            try {
                await feedAPI.getProjectDetail(projectId);
                setIsPublishedToFeed(true);
            } catch {
                setIsPublishedToFeed(false);
            }
        };
        checkPublished();
    }, [projectId]);

    // Фильтруем уже добавленных участников
    const existingParticipantIds = currentProject?.participants?.map(p => p.user_id) || [];
    const availableUsers = results.filter(user => !existingParticipantIds.includes(user.user_id));

    const handleAddParticipants = async () => {
        if (selectedUsers.length === 0) return;
        
        try {
            const userIds = selectedUsers.map(u => u.user_id);
            await dispatch(createProjectInvitations({ projectId, userIds })).unwrap();
            setSelectedUsers([]);
            setShowAddParticipantModal(false);
            clearSearch();
            dispatch(fetchProject(projectId));
        } catch (error) {
            console.error('Failed to add participants:', error);
        }
    };

    const handleUpdateStatus = async (newStatus) => {
        if (!selectedParticipant) return;
        
        try {
            await dispatch(updateParticipantStatus({
                projectId,
                participantUserId: selectedParticipant.user_id,
                status: newStatus
            })).unwrap();
            setShowStatusModal(false);
            setSelectedParticipant(null);
            dispatch(fetchProject(projectId));
        } catch (error) {
            console.error('Failed to update status:', error);
        }
    };

    const handleLeaveProject = async () => {
        if (!window.confirm('Вы уверены, что хотите покинуть проект?')) return;
        
        setIsLeaving(true);
        try {
            await dispatch(leaveProject(projectId)).unwrap();
            navigate('/projects');
        } catch (error) {
            console.error('Failed to leave project:', error);
            setIsLeaving(false);
        }
    };

    const getDisplayName = (url) => {
        try {
            const u = (url || '').startsWith('http') ? url : 'https://' + url;
            return new URL(u).hostname.replace(/^www\./, '');
        } catch { return url || 'Ссылка'; }
    };
    const normalizeLink = (item) => {
        if (typeof item === 'string') return { name: getDisplayName(item), link: item };
        return { name: item?.name ?? item?.title ?? getDisplayName(item?.link || item?.url), link: item?.link ?? item?.url ?? '' };
    };

    const projectLinksList = (currentProject?.links || []).map(normalizeLink).filter((l) => l.link);

    const handleAddProjectLink = async () => {
        const url = newLinkUrl.trim();
        if (!url) return;
        const current = (currentProject?.links || []).map((l) => (typeof l === 'string' ? l : l?.link || l?.url)).filter(Boolean);
        const updated = [...current, url];
        try {
            await dispatch(updateProject({ projectId, projectData: { links: updated } })).unwrap();
            dispatch(fetchProject(projectId));
            setNewLinkUrl('');
            setShowAddLinkModal(false);
        } catch (err) {
            console.error('Failed to add link:', err);
        }
    };

    const handleRemoveProjectLink = async (index) => {
        const current = (currentProject?.links || []).map((l) => (typeof l === 'string' ? l : l?.link || l?.url)).filter(Boolean);
        const updated = current.filter((_, i) => i !== index);
        try {
            await dispatch(updateProject({ projectId, projectData: { links: updated } })).unwrap();
            dispatch(fetchProject(projectId));
        } catch (err) {
            console.error('Failed to remove link:', err);
        }
    };

    const handleCreateChannel = async () => {
        if (!channelName.trim()) return;
        try {
            setChannelLoading(true);
            const response = await channelAPI.createChannel({
                name: channelName.trim(),
                description: channelDescription.trim() || null,
                project_id: projectId,
            });
            setProjectChannel(response?.data || null);
        } catch (e) {
            console.error('Failed to create channel:', e);
            alert('Не удалось создать канал проекта');
        } finally {
            setChannelLoading(false);
        }
    };

    const handleUpdateChannel = async () => {
        if (!projectChannel?.id) return;
        try {
            setChannelLoading(true);
            const response = await channelAPI.updateChannel(projectChannel.id, {
                name: channelName.trim() || null,
                description: channelDescription.trim() || null,
            });
            setProjectChannel(response?.data || { ...projectChannel, name: channelName, description: channelDescription });
        } catch (e) {
            console.error('Failed to update channel:', e);
            alert('Не удалось обновить канал');
        } finally {
            setChannelLoading(false);
        }
    };

    const handleUnpublishFromFeed = async () => {
        try {
            await feedAPI.unpublishProject(projectId);
            setIsPublishedToFeed(false);
            alert('Проект снят с публикации');
        } catch (e) {
            console.error('Failed to unpublish project:', e);
            alert('Не удалось снять проект с публикации');
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        try {
            // Исправьте: updateProject ожидает (projectId, projectData)
            const result = await dispatch(updateProject({ 
                projectId, 
                projectData: formData 
            }));
            
            if (result.meta.requestStatus === 'fulfilled') {
                setShowSettingsModal(false);
                // Обновить данные проекта
                dispatch(fetchProject(projectId));
            } else {
                console.error('Ошибка сохранения:', result.error);
                alert('Не удалось сохранить изменения');
            }
        } catch (error) {
            console.error('Error updating project:', error);
            alert('Произошла ошибка при сохранении');
        }
    };

    if (isLoading) {
        return (
            <Header>
                <div className="max-w-6xl mx-auto">
                    <div className="text-center py-8 text-gray-400">
                        <p>Загрузка проекта...</p>
                    </div>
                </div>
            </Header>
        );
    }

    if (error) {
        return (
            <Header>
                <div className="max-w-6xl mx-auto">
                    <div className="text-center py-8 text-red-400">
                        <p>Ошибка загрузки проекта</p>
                        <p className="text-sm mt-2">{typeof error === 'string' ? error : error.detail || 'Попробуйте обновить страницу'}</p>
                        <button
                            onClick={() => navigate('/projects')}
                            className="mt-4 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
                        >
                            Вернуться к проектам
                        </button>
                    </div>
                </div>
            </Header>
        );
    }

    if (!currentProject) {
        return (
            <Header>
                <div className="max-w-6xl mx-auto">
                    <div className="text-center py-8 text-gray-400">
                        <p>Проект не найден</p>
                        <button
                            onClick={() => navigate('/projects')}
                            className="mt-4 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
                        >
                            Вернуться к проектам
                        </button>
                    </div>
                </div>
            </Header>
        );
    }

    return (
        <Header>
            <div className="max-w-6xl mx-auto">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-6">
                    <div className="flex items-start gap-3 sm:gap-4 min-w-0 flex-1">
                        <button
                            onClick={() => navigate('/projects')}
                            className="p-2 hover:bg-gray-800 rounded-lg transition-colors text-white flex-shrink-0"
                        >
                            <FiArrowLeft size={20} />
                        </button>
                        <div className="min-w-0 flex-1">
                            <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-white break-words">{currentProject.name}</h1>
                            <div className="flex flex-wrap items-center gap-2 sm:gap-4 mt-2">
                                <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getStatusColor(currentProject.status)}`}>
                                    {getStatusText(currentProject.status)}
                                </span>
                                <span className="text-gray-400 text-sm">
                                    Создан {new Date(currentProject.created_at).toLocaleDateString('ru-RU')}
                                </span>
                            </div>
                        </div>
                    </div>
                    <button
                        onClick={() => setShowSettingsModal(true)}
                        className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors flex items-center whitespace-nowrap flex-shrink-0 self-start">
                        <FiSettings className="mr-2" />
                        Настройки
                    </button>
                </div>

                {/* Tabs */}
                <div className="border-b border-gray-700 mb-6 overflow-x-auto">
                    <nav className="flex gap-4 sm:gap-8 min-w-max sm:min-w-0">
                        <button
                            onClick={() => setActiveTab('overview')}
                            className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors whitespace-nowrap flex-shrink-0 ${
                                activeTab === 'overview'
                                    ? 'border-purple-500 text-purple-400'
                                    : 'border-transparent text-gray-400 hover:text-gray-300'
                            }`}
                        >
                            Обзор
                        </button>
                        <button
                            onClick={() => setActiveTab('participants')}
                            className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors whitespace-nowrap flex-shrink-0 ${
                                activeTab === 'participants'
                                    ? 'border-purple-500 text-purple-400'
                                    : 'border-transparent text-gray-400 hover:text-gray-300'
                            }`}
                        >
                            Участники
                        </button>
                        <button
                            onClick={() => setActiveTab('workspaces')}
                            className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors whitespace-nowrap flex-shrink-0 ${
                                activeTab === 'workspaces'
                                    ? 'border-purple-500 text-purple-400'
                                    : 'border-transparent text-gray-400 hover:text-gray-300'
                            }`}
                        >
                            Рабочие пространства
                        </button>
                        <button
                            onClick={() => setActiveTab('announcements')}
                            className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors inline-flex items-center gap-2 whitespace-nowrap flex-shrink-0 ${
                                activeTab === 'announcements'
                                    ? 'border-purple-500 text-purple-400'
                                    : 'border-transparent text-gray-400 hover:text-gray-300'
                            }`}
                        >
                            <FiBriefcase size={14} />
                            Объявления
                        </button>
                    </nav>
                </div>

                {/* Tab Content */}
                <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6 backdrop-blur-sm">
                    {activeTab === 'overview' && (
                        <div className="space-y-6">
                            {/* Description */}
                            <div>
                                <h2 className="text-xl font-bold text-white mb-3">Описание проекта</h2>
                             <p className="text-gray-300 break-words">
                                    {currentProject.description || 'Описание отсутствует'}
                                </p>
                            </div>

                            {/* Category */}

<                           div>
                                <h2 className="text-xl font-bold text-white mb-3">Категория</h2>
                                <p className="text-gray-300 leading-relaxed">
                                    {currentProject.category || 'Категория отсутствует'}
                                </p>
                            </div>
                            

                            {/* Tags */}
                            {currentProject.tags && currentProject.tags.length > 0 && (
                                <div>
                                    <h3 className="text-lg font-semibold text-white mb-3 flex items-center">
                                        <FiTag className="mr-2" />
                                        Теги
                                    </h3>
                                    <div className="flex flex-wrap gap-2">
                                        {currentProject.tags.map((tag, index) => (
                                            <span
                                                key={index}
                                                className="px-3 py-1 bg-purple-900/40 text-purple-300 rounded-full text-sm font-medium border border-purple-800/50"
                                            >
                                                {tag}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Ссылки проекта (соцсети, каналы) */}
                            <div>
                                <div className="flex items-center justify-between mb-3">
                                    <h3 className="text-lg font-semibold text-white">Ссылки проекта</h3>
                                    {canManageParticipants && (
                                        <button
                                            onClick={() => setShowAddLinkModal(true)}
                                            className="flex items-center gap-2 px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm"
                                        >
                                            <FiPlus size={14} />
                                            Добавить ссылку
                                        </button>
                                    )}
                                </div>
                                {projectLinksList.length > 0 ? (
                                    <div className="flex flex-wrap gap-3">
                                        {projectLinksList.map((item, i) => (
                                            <div key={i} className="flex items-center gap-2 px-4 py-2 bg-gray-700/50 rounded-lg group">
                                                <a
                                                    href={item.link}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-purple-400 hover:text-purple-300 font-medium"
                                                >
                                                    {item.name}
                                                </a>
                                                {canManageParticipants && (
                                                    <button
                                                        onClick={() => handleRemoveProjectLink(i)}
                                                        className="text-gray-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                                                    >
                                                        <FiX size={14} />
                                                    </button>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-gray-500 text-sm">
                                        Ссылки на соцсети и каналы не добавлены.
                                    </p>
                                )}
                            </div>

                            <div className="rounded-xl border border-gray-700 bg-gray-900/40 p-4">
                                <div className="flex items-center justify-between mb-3">
                                    <h3 className="text-lg font-semibold text-white">Канал проекта</h3>
                                    {projectChannel && (
                                        <span className="text-xs text-green-400 bg-green-900/20 border border-green-800 px-2 py-1 rounded-full">
                                            Создан
                                        </span>
                                    )}
                                </div>
                                <p className="text-sm text-gray-400 mb-4">
                                    Канал создается отдельно после проекта. Подписчики увидят его во вкладке каналов.
                                </p>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
                                    <input
                                        type="text"
                                        value={channelName}
                                        onChange={(e) => setChannelName(e.target.value)}
                                        placeholder="Название канала"
                                        className="w-full px-4 py-2 bg-gray-700 text-white rounded-lg"
                                    />
                                    <input
                                        type="text"
                                        value={channelDescription}
                                        onChange={(e) => setChannelDescription(e.target.value)}
                                        placeholder="Описание канала"
                                        className="w-full px-4 py-2 bg-gray-700 text-white rounded-lg"
                                    />
                                </div>
                                <div className="flex items-center gap-2">
                                    {!projectChannel ? (
                                        <button
                                            onClick={handleCreateChannel}
                                            disabled={!channelName.trim() || channelLoading}
                                            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-lg"
                                        >
                                            {channelLoading ? 'Создание...' : 'Создать канал'}
                                        </button>
                                    ) : (
                                        <>
                                            <button
                                                onClick={handleUpdateChannel}
                                                disabled={channelLoading}
                                                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-lg"
                                            >
                                                {channelLoading ? 'Сохранение...' : 'Сохранить'}
                                            </button>
                                            <Link
                                                to="/chats"
                                                state={{ openChat: { ...projectChannel, type: 'channel' } }}
                                                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg"
                                            >
                                                Открыть канал
                                            </Link>
                                        </>
                                    )}
                                </div>
                            </div>

                            <div className="rounded-xl border border-gray-700 bg-gray-900/40 p-4">
                                <div className="flex items-center justify-between mb-3">
                                    <h3 className="text-lg font-semibold text-white">Публикация в ленту</h3>
                                    <span className={`text-xs px-2 py-1 rounded-full border ${isPublishedToFeed ? 'text-green-400 border-green-800 bg-green-900/20' : 'text-gray-400 border-gray-700 bg-gray-900/30'}`}>
                                        {isPublishedToFeed ? 'Опубликован' : 'Не опубликован'}
                                    </span>
                                </div>
                                <p className="text-sm text-gray-400 mb-3">
                                    Создайте отдельную публичную страницу для ленты через полную форму.
                                </p>
                                <div className="flex items-center gap-2">
                                    {!isPublishedToFeed ? (
                                        <Link
                                            to={`/projects/${projectId}/publish-feed`}
                                            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg"
                                        >
                                            Открыть форму публикации
                                        </Link>
                                    ) : (
                                        <button
                                            onClick={handleUnpublishFromFeed}
                                            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg"
                                        >
                                            Снять с публикации
                                        </button>
                                    )}
                                    <Link to="/feed" className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg">
                                        Открыть ленту
                                    </Link>
                                </div>
                            </div>

                            {/* Creator Info */}
                            {currentProject.creator && (
                                <div>
                                    <h3 className="text-lg font-semibold text-white mb-3">Создатель проекта</h3>
                                    <div className="flex items-center gap-3 p-3 bg-gray-700/50 rounded-lg">
                                        {currentProject.creator.avatar_path ? (
                                            <img
                                                src={currentProject.creator.avatar_path}
                                                alt={`${currentProject.creator.name} ${currentProject.creator.lastname}`}
                                                className="w-12 h-12 rounded-full object-cover"
                                            />
                                        ) : (
                                            <div className="w-12 h-12 rounded-full bg-purple-600 flex items-center justify-center text-white font-bold">
                                                {currentProject.creator.name?.[0] || 'U'}
                                            </div>
                                        )}
                                        <div>
                                            <p className="text-white font-medium">
                                                {currentProject.creator.name} {currentProject.creator.lastname}
                                            </p>
                                            <p className="text-gray-400 text-sm">@{currentProject.creator.username}</p>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Project Stats */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div className="bg-gray-700/50 rounded-lg p-4">
                                    <div className="flex items-center gap-3">
                                        <FiUsers className="text-purple-400" size={20} />
                                        <div>
                                            <p className="text-2xl font-bold text-white">
                                                {displayParticipants.length}
                                            </p>
                                            <p className="text-gray-400 text-sm">Участников</p>
                                        </div>
                                    </div>
                                </div>
                                <div className="bg-gray-700/50 rounded-lg p-4">
                                    <div className="flex items-center gap-3">
                                        <FiMessageSquare className="text-purple-400" size={20} />
                                        <div>
                                            <p className="text-2xl font-bold text-white">
                                                {currentProject.workspaces?.length || 0}
                                            </p>
                                            <p className="text-gray-400 text-sm">Рабочих пространств</p>
                                        </div>
                                    </div>
                                </div>
                                <div className="bg-gray-700/50 rounded-lg p-4">
                                    <div className="flex items-center gap-3">
                                        <FiCalendar className="text-purple-400" size={20} />
                                        <div>
                                            <p className="text-2xl font-bold text-white">
                                                {Math.floor((new Date() - new Date(currentProject.created_at)) / (1000 * 60 * 60 * 24))}
                                            </p>
                                            <p className="text-gray-400 text-sm">Дней существует</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {activeTab === 'participants' && (
                        <div>
                            <div className="flex items-center justify-between mb-4">
                                <h2 className="text-xl font-bold text-white">Участники проекта</h2>
                                <div className="flex gap-2">
                                    {canManageParticipants && (
                                        <button
                                            onClick={() => setShowAddParticipantModal(true)}
                                            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors flex items-center"
                                        >
                                            <FiPlus className="mr-2" />
                                            Отправить приглашение
                                        </button>
                                    )}
                                    {currentParticipant && currentParticipant.status !== 'owner' && (
                                        <button
                                            onClick={handleLeaveProject}
                                            disabled={isLeaving}
                                            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors flex items-center disabled:opacity-50"
                                        >
                                            <FiLogOut className="mr-2" />
                                            {isLeaving ? 'Выход...' : 'Покинуть проект'}
                                        </button>
                                    )}
                                </div>
                            </div>
                            {displayParticipants.length > 0 ? (
                                <div className="space-y-3">
                                    {displayParticipants.map((participant) => {
                                        const up = getUserProfileFromParticipant(participant)
                                        const fullName = `${up.name || ''} ${up.lastname || ''}`.trim() || 'Пользователь'
                                        const initials = (up.name?.[0] || 'U').toUpperCase()

                                        return (
                                        <div key={participant.id || participant.user_id} className="flex items-center justify-between p-4 bg-gray-700/50 rounded-lg">
                                            <div className="flex items-center gap-3">
                                                {up.avatar_path ? (
                                                    <img
                                                        src={up.avatar_path}
                                                        alt={fullName}
                                                        className="w-10 h-10 rounded-full object-cover"
                                                    />
                                                ) : (
                                                    <div className="w-10 h-10 rounded-full bg-purple-600 flex items-center justify-center text-white font-bold text-sm">
                                                        {initials}
                                                    </div>
                                                )}
                                                <div>
                                                    <p className="text-white font-medium">
                                                        {fullName}
                                                    </p>
                                                    {up.username && (
                                                        <p className="text-gray-400 text-sm">@{up.username}</p>
                                                    )}
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-4">
                                                <div className="text-right">
                                                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                                                        participant.status === 'owner' ? 'bg-yellow-900/30 text-yellow-400' :
                                                        participant.status === 'admin' ? 'bg-blue-900/30 text-blue-400' :
                                                        participant.status === 'editor' ? 'bg-green-900/30 text-green-400' :
                                                        'bg-gray-900/30 text-gray-400'
                                                    }`}>
                                                        {getParticipantStatusText(participant.status)}
                                                    </span>
                                                    <p className="text-gray-500 text-xs mt-1">
                                                        Присоединился {new Date(participant.joined_at).toLocaleDateString('ru-RU')}
                                                    </p>
                                                </div>
                                                {canManageParticipants && participant.status !== 'owner' && (
                                                    <button
                                                        onClick={() => {
                                                            setSelectedParticipant(participant);
                                                            setShowStatusModal(true);
                                                        }}
                                                        className="p-2 hover:bg-gray-600 rounded-lg transition-colors text-gray-400 hover:text-white"
                                                        title="Изменить статус"
                                                    >
                                                        <FiEdit2 size={16} />
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                    )})}
                                </div>
                            ) : (
                                <p className="text-gray-400 text-center py-8">Участники отсутствуют</p>
                            )}
                        </div>
                    )}

                    {activeTab === 'workspaces' && (
                        <div>
                            <div className="flex items-center justify-between mb-4">
                                <h2 className="text-xl font-bold text-white">Рабочие пространства</h2>
                                <Link to={`/projects/${currentProject.id}/workspaces/create`}>
                                    <button className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors flex items-center">
                                        <FiPlus className="mr-2" />
                                        Создать рабочее пространство
                                    </button>
                                </Link>
                            </div>
                            {currentProject.workspaces && currentProject.workspaces.length > 0 ? (
                                <div className="space-y-4">
                                    {currentProject.workspaces.map((workspace) => (
                                        <Link 
                                            key={workspace.id} 
                                            to={`/projects/${currentProject.id}/workspaces/${workspace.id}`}
                                            className="block p-4 bg-gray-700/50 rounded-lg hover:bg-gray-700/70 transition-colors cursor-pointer"
                                        >
                                            <div className="flex items-center justify-between mb-3">
                                                <div>
                                                    <h3 className="text-lg font-medium text-white">{workspace.name}</h3>
                                                    <p className="text-gray-400 text-sm">{workspace.description || 'Нет описания'}</p>
                                                </div>
                                                {workspace.is_main && (
                                                    <span className="px-2 py-1 bg-purple-900/30 text-purple-400 rounded text-xs font-medium">
                                                        Основное
                                                    </span>
                                                )}
                                            </div>
                                            {workspace.chat && (
                                                <div className="flex items-center gap-2 text-sm">
                                                    <FiMessageSquare className="text-gray-400" size={16} />
                                                    <span className="text-gray-300">
                                                        Чат: {workspace.chat.name}
                                                    </span>
                                                    <span className={`px-2 py-0.5 rounded text-xs ${
                                                        workspace.chat.is_active ? 'bg-green-900/30 text-green-400' : 'bg-gray-900/30 text-gray-400'
                                                    }`}>
                                                        {workspace.chat.is_active ? 'Активен' : 'Неактивен'}
                                                    </span>
                                                </div>
                                            )}
                                            <p className="text-gray-500 text-xs mt-2">
                                                Создано {new Date(workspace.created_at).toLocaleDateString('ru-RU')}
                                            </p>
                                        </Link>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-8">
                                    <p className="text-gray-400 mb-4">Рабочие пространства отсутствуют</p>
                                    <Link to={`/projects/${currentProject.id}/workspaces/create`}>
                                        <button className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors">
                                            Создать первое рабочее пространство
                                        </button>
                                    </Link>
                                </div>
                            )}
                        </div>
                    )}

                    {activeTab === 'announcements' && (
                        <ProjectAnnouncementsTab
                            projectId={currentProject.id}
                            workspaces={currentProject.workspaces || []}
                            canCreate={isCreator || currentParticipant?.status === 'owner' || currentParticipant?.status === 'admin'}
                            canManageAnnouncements={canManageParticipants}
                        />
                    )}
                </div>
            </div>

            {/* Add Participant Modal */}
            {showAddParticipantModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-xl font-bold text-white">Отправить приглашение в проект</h3>
                            <button
                                onClick={() => {
                                    setShowAddParticipantModal(false);
                                    setSelectedUsers([]);
                                    clearSearch();
                                }}
                                className="text-gray-400 hover:text-white"
                            >
                                <FiX size={20} />
                            </button>
                        </div>
                        
                        <div className="mb-4">
                            <div className="relative">
                                <FiSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                                <input
                                    type="text"
                                    placeholder="Поиск пользователей..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="w-full pl-10 pr-4 py-2 bg-gray-700 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                                />
                            </div>
                            
                            {isSearching && (
                                <p className="text-gray-400 text-sm mt-2">Поиск...</p>
                            )}
                            
                            {searchError && (
                                <p className="text-red-400 text-sm mt-2">{searchError}</p>
                            )}
                            
                            {availableUsers.length > 0 && (
                                <div className="mt-2 max-h-60 overflow-y-auto bg-gray-900/50 rounded-lg">
                                    {availableUsers.map((user) => {
                                        const isSelected = selectedUsers.some(u => u.user_id === user.user_id);
                                        return (
                                            <div
                                                key={user.user_id}
                                                onClick={() => {
                                                    if (isSelected) {
                                                        setSelectedUsers(selectedUsers.filter(u => u.user_id !== user.user_id));
                                                    } else {
                                                        setSelectedUsers([...selectedUsers, user]);
                                                    }
                                                }}
                                                className={`p-3 cursor-pointer hover:bg-gray-700/50 transition-colors flex items-center gap-3 ${
                                                    isSelected ? 'bg-purple-900/30' : ''
                                                }`}
                                            >
                                                {user.avatar_path ? (
                                                    <img src={user.avatar_path} alt={user.name} className="w-8 h-8 rounded-full object-cover" />
                                                ) : (
                                                    <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-white font-bold text-xs">
                                                        {user.name?.[0] || 'U'}
                                                    </div>
                                                )}
                                                <div className="flex-1">
                                                    <p className="text-white text-sm">{user.name} {user.lastname}</p>
                                                    <p className="text-gray-400 text-xs">@{user.username}</p>
                                                </div>
                                                {isSelected && (
                                                    <div className="w-5 h-5 bg-purple-600 rounded-full flex items-center justify-center">
                                                        <FiX size={12} className="text-white" />
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>

                        {selectedUsers.length > 0 && (
                            <div className="mb-4">
                                <p className="text-gray-400 text-sm mb-2">Выбрано: {selectedUsers.length}</p>
                                <div className="flex flex-wrap gap-2">
                                    {selectedUsers.map((user) => (
                                        <div key={user.user_id} className="flex items-center gap-2 px-3 py-1 bg-purple-900/30 rounded-full">
                                            <span className="text-white text-sm">{user.name} {user.lastname}</span>
                                            <button
                                                onClick={() => setSelectedUsers(selectedUsers.filter(u => u.user_id !== user.user_id))}
                                                className="text-purple-400 hover:text-purple-300"
                                            >
                                                <FiX size={14} />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div className="flex gap-2">
                            <button
                                onClick={handleAddParticipants}
                                disabled={selectedUsers.length === 0}
                                className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                Отправить
                            </button>
                            <button
                                onClick={() => {
                                    setShowAddParticipantModal(false);
                                    setSelectedUsers([]);
                                    clearSearch();
                                }}
                                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
                            >
                                Отмена
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Update Status Modal */}
            {showStatusModal && selectedParticipant && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-xl font-bold text-white">Изменить статус участника</h3>
                            <button
                                onClick={() => {
                                    setShowStatusModal(false);
                                    setSelectedParticipant(null);
                                }}
                                className="text-gray-400 hover:text-white"
                            >
                                <FiX size={20} />
                            </button>
                        </div>
                        
                        <div className="mb-4">
                            <p className="text-gray-400 text-sm mb-4">Текущий статус: <span className="text-white">{getParticipantStatusText(selectedParticipant.status)}</span></p>
                            
                            <div className="space-y-2">
                                {['admin', 'editor', 'viewer'].map((status) => (
                                    <button
                                        key={status}
                                        onClick={() => handleUpdateStatus(status)}
                                        disabled={selectedParticipant.status === status}
                                        className={`w-full px-4 py-2 rounded-lg transition-colors text-left ${
                                            selectedParticipant.status === status
                                                ? 'bg-purple-600 text-white cursor-not-allowed'
                                                : 'bg-gray-700 hover:bg-gray-600 text-white'
                                        }`}
                                    >
                                        {getParticipantStatusText(status)}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <button
                            onClick={() => {
                                setShowStatusModal(false);
                                setSelectedParticipant(null);
                            }}
                            className="w-full px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
                        >
                            Отмена
                        </button>
                    </div>
                </div>
            )}

            {showSettingsModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" style={{ zIndex: 1000 }}>
                    <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-white text-xl">Настройки страницы проекта</h3>
                            <button
                                onClick={() => {
                                    setShowSettingsModal(false);
                                    setNewTag('');
                                }}
                                className="text-gray-400 hover:text-white"
                            >
                                <FiX size={20} />
                            </button>
                        </div>
                        
                        <form onSubmit={handleSubmit}>
                            <div className="space-y-4 mb-4">
                                {/* Название проекта */}
                                <div>
                                    <label className="block text-gray-300 text-sm font-medium mb-2">
                                        Название проекта *
                                    </label>
                                    <input
                                        type="text"
                                        name="name"
                                        value={formData.name}
                                        onChange={handleInputChange}
                                        required
                                        className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300"
                                        placeholder="Введите название проекта"
                                    />
                                </div>
                                
                                {/* Категория */}
                                <div>
                                    <label className="block text-gray-300 text-sm font-medium mb-2">
                                        Категория проекта *
                                    </label>
                                    <select
                                        name="category"
                                        value={formData.category}
                                        onChange={handleInputChange}
                                        required
                                        className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white"
                                    >
                                        <option value="" disabled>
                                            Выберите категорию
                                        </option>
                                        {categoryOptions.map((opt) => (
                                            <option key={opt.value} value={opt.value}>
                                                {opt.label}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                
                                {/* Описание проекта */}
                                <div>
                                    <label className="block text-gray-300 text-sm font-medium mb-2">
                                        Описание проекта *
                                    </label>
                                    <textarea
                                        name="description"
                                        value={formData.description}
                                        onChange={handleInputChange}
                                        required
                                        rows={4}
                                        className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300 resize-none"
                                        placeholder="Опишите ваш проект..."
                                    />
                                </div>
                                
                                {/* Теги */}
                                <div>
                                    <label className="block text-gray-300 text-sm font-medium mb-2">
                                        Теги проекта
                                    </label>
                                    <div className="flex gap-2 mb-3">
                                        <input
                                            type="text"
                                            value={newTag}
                                            onChange={(e) => setNewTag(e.target.value)}
                                            onKeyPress={handleKeyPress}
                                            className="flex-1 px-4 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
                                            placeholder="Добавить тег..."
                                        />
                                        <button
                                            type="button"
                                            onClick={addTag}
                                            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors flex items-center"
                                        >
                                            <FiPlus className="mr-2" />
                                            Добавить
                                        </button>
                                    </div>
                                    
                                    {/* Список тегов */}
                                    <div className="flex flex-wrap gap-2">
                                        {formData.tags.map((tag, index) => (
                                            <span
                                                key={index}
                                                className="px-3 py-1 bg-purple-900/40 text-purple-300 rounded-full text-sm font-medium border border-purple-800/50 flex items-center gap-2"
                                            >
                                                {tag}
                                                <button
                                                    type="button"
                                                    onClick={() => removeTag(tag)}
                                                    className="text-purple-200 hover:text-white transition-colors"
                                                >
                                                    ×
                                                </button>
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            </div>
                            
                            <div className="flex gap-2">
                                <button
                                    type="submit"
                                    className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg"
                                >
                                    Сохранить изменения
                                </button>
                                <button
                                    type="button"
                                    onClick={() => {
                                        setShowSettingsModal(false);
                                        setNewTag('');
                                    }}
                                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg"
                                >
                                    Отмена
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Add Project Link Modal (соцсети, каналы) */}
            {showAddLinkModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-xl font-bold text-white">Добавить ссылку</h3>
                            <button
                                onClick={() => {
                                    setShowAddLinkModal(false);
                                    setNewLinkUrl('');
                                }}
                                className="text-gray-400 hover:text-white"
                            >
                                <FiX size={20} />
                            </button>
                        </div>
                        <div className="space-y-4 mb-4">
                            <div>
                                <label className="block text-gray-400 text-sm mb-1">URL (Telegram, VK и т.д.)</label>
                                <input
                                    type="url"
                                    value={newLinkUrl}
                                    onChange={(e) => setNewLinkUrl(e.target.value)}
                                    placeholder="https://t.me/..."
                                    className="w-full px-4 py-2 bg-gray-700 text-white rounded-lg"
                                />
                            </div>
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={handleAddProjectLink}
                                disabled={!newLinkUrl.trim()}
                                className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-lg"
                            >
                                Добавить
                            </button>
                            <button
                                onClick={() => {
                                    setShowAddLinkModal(false);
                                    setNewLinkUrl('');
                                }}
                                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg"
                            >
                                Отмена
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </Header>
    );
}
