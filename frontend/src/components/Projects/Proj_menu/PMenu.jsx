import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import Header from '../../../ui/Header';
import { FiCalendar, FiFilter, FiX, FiChevronDown, FiPlus } from 'react-icons/fi';
import { Link } from 'react-router-dom';
import { fetchProjects } from '../../../store/slices/projects';

export default function PMenu()  {
    const dispatch = useDispatch();
    const { projects, isLoading, error } = useSelector(state => state.projects);
    
    const [search, setSearch] = useState('');
    const [filtersOpen, setFiltersOpen] = useState(false);
    
    // Фильтры
    const [statusFilter, setStatusFilter] = useState(''); // active, archived, completed
    const [selectedThemes, setSelectedThemes] = useState([]);

    // Получаем все уникальные темы
    const allThemes = useMemo(() => {
        const themes = new Set();
        projects.forEach(project => {
            if (project.tags) {
                project.tags.forEach(tag => themes.add(tag));
            }
        });
        return Array.from(themes);
    }, [projects]);

    // Debounced search function
    const debouncedSearch = useCallback(
        debounce((searchValue) => {
            const params = {
                search: searchValue || undefined,
                status: statusFilter || undefined,
                tags: selectedThemes.length > 0 ? selectedThemes : undefined,
                limit: 20,
                offset: 0
            };
            dispatch(fetchProjects(params));
        }, 500),
        [dispatch, statusFilter, selectedThemes]
    );

    // Fetch projects on component mount
    useEffect(() => {
        dispatch(fetchProjects({ limit: 20, offset: 0 }));
    }, [dispatch]);

    // Handle search with debouncing
    useEffect(() => {
        debouncedSearch(search);
    }, [search, debouncedSearch]);

    // Handle filter changes (immediate)
    useEffect(() => {
        if (statusFilter !== '' || selectedThemes.length > 0) {
            const params = {
                search: search || undefined,
                status: statusFilter || undefined,
                tags: selectedThemes.length > 0 ? selectedThemes : undefined,
                limit: 20,
                offset: 0
            };
            dispatch(fetchProjects(params));
        }
    }, [dispatch, statusFilter, selectedThemes, search]);

    // Helper function for debouncing
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Фильтрация проектов (только для локальной фильтрации, если нужна)
    const filteredProjects = useMemo(() => {
        return projects.filter(project => {
            // Поиск по названию и описанию (если API не поддерживает поиск)
            const matchesSearch = search === '' || 
                project.name.toLowerCase().includes(search.toLowerCase()) ||
                project.description.toLowerCase().includes(search.toLowerCase());

            // Фильтр по статусу
            const matchesStatus = statusFilter === '' || project.status === statusFilter;

            // Фильтр по темам
            const matchesThemes = selectedThemes.length === 0 || 
                (project.tags && project.tags.some(tag => selectedThemes.includes(tag)));

            return matchesSearch && matchesStatus && matchesThemes;
        });
    }, [projects, search, statusFilter, selectedThemes]);

    const toggleTheme = (theme) => {
        setSelectedThemes(prev => 
            prev.includes(theme) 
                ? prev.filter(t => t !== theme)
                : [...prev, theme]
        );
    };

    const clearFilters = () => {
        setStatusFilter('');
        setSelectedThemes([]);
        setSearch('');
    };

    const activeFiltersCount = [
        statusFilter !== '',
        selectedThemes.length > 0,
        search !== ''
    ].filter(Boolean).length;

    return (
        <Header>
            <div className="max-w-6xl mx-auto px-1 sm:px-0">
                {/* Поисковая строка и кнопки */}
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 mb-4">
                    <input 
                        type="text"
                        className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl 
                                    dark:text-white text-black placeholder-gray-500
                                    focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20
                                    transition-all duration-300
                                    backdrop-blur-sm
                                    min-w-0"
                        placeholder="Поиск..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                    <div className="flex gap-2 flex-shrink-0">
                        <Link to="/projects/create" className="flex-1 sm:flex-none">
                            <button className="w-full sm:w-auto px-3 sm:px-4 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors flex items-center justify-center whitespace-nowrap">
                                <FiPlus className="mr-2 flex-shrink-0" />
                                <span className="hidden xs:inline">Создать проект</span>
                                <span className="xs:hidden">Создать</span>
                            </button>
                        </Link>
                        <button 
                            className="flex-1 sm:flex-none px-3 sm:px-4 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors flex items-center justify-center whitespace-nowrap"
                            onClick={() => setFiltersOpen(!filtersOpen)}
                        >
                            <FiFilter className="mr-2 flex-shrink-0" />
                            Фильтры
                            {activeFiltersCount > 0 && (
                                <span className="ml-2 px-2 py-1 bg-purple-800 rounded-full text-xs">
                                    {activeFiltersCount}
                                </span>
                            )}
                        </button>
                    </div>
                </div>

                {/* Панель фильтров */}
                {filtersOpen && (
                    <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4 mb-4 backdrop-blur-sm">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-lg font-bold text-white">Фильтры</h2>
                            <button 
                                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors flex items-center"
                                onClick={clearFilters}
                            >
                                <FiX className="mr-2" />
                                Очистить
                            </button>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* Фильтр по статусу */}
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">
                                    Статус проекта
                                </label>
                                <select 
                                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-purple-500"
                                    value={statusFilter}
                                    onChange={(e) => setStatusFilter(e.target.value)}
                                >
                                    <option value="">Все статусы</option>
                                    <option value="active">Активные</option>
                                    <option value="archived">Архивированные</option>
                                    <option value="completed">Завершенные</option>
                                </select>
                            </div>

                            {/* Фильтр по темам */}
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">
                                    Темы проекта
                                </label>
                                <div className="max-h-32 overflow-y-auto space-y-1">
                                    {allThemes.map(theme => (
                                        <label key={theme} className="flex items-center text-gray-300 hover:text-white cursor-pointer">
                                            <input 
                                                type="checkbox"
                                                className="mr-2 rounded border-gray-600 bg-gray-700 text-purple-600 focus:ring-purple-500"
                                                checked={selectedThemes.includes(theme)}
                                                onChange={() => toggleTheme(theme)}
                                            />
                                            <span className="text-sm">{theme}</span>
                                        </label>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Список проектов */}
                <div className="">
                    {isLoading ? (
                        <div className="text-center py-8 text-gray-400">
                            <p>Загрузка проектов...</p>
                        </div>
                    ) : error ? (
                        <div className="text-center py-8 text-red-400">
                            <p>Ошибка загрузки проектов</p>
                            <p className="text-sm mt-2">{typeof error === 'string' ? error : error.detail || 'Попробуйте обновить страницу'}</p>
                        </div>
                    ) : filteredProjects.length === 0 ? (
                        <div className="text-center py-8 text-gray-400">
                            <p>Проекты не найдены</p>
                            <p className="text-sm mt-2">Попробуйте изменить фильтры или поисковый запрос</p>
                        </div>
                    ) : (
                        filteredProjects.map((project) => (
                            <div key={project.id} className="bg-gray-800/30 border border-gray-700 rounded-xl p-4 sm:p-5 hover:border-purple-600/50 hover:shadow-lg hover:shadow-purple-500/10 transition-all duration-300 group">
                                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                                <div className="flex-1 min-w-0">
                                    <p className='text-left text-xl sm:text-2xl font-semibold text-white break-words'>
                                        {project.name}
                                    </p>
                                  <p className="text-left text-gray-300 line-clamp-2 break-words mt-2">
                                        {project.description}
                                    </p>
                                    <p className='text-gray-500 text-sm mt-2'>Дата создания: {new Date(project.created_at).toLocaleDateString('ru-RU')}</p>
                                    <div className="flex flex-wrap gap-2 mt-2">
                                        {project.tags && project.tags.map((tag, index) => (
                                            <span 
                                                key={index}
                                                className="px-3 py-1 bg-purple-900/40 text-purple-300 rounded-full text-xs sm:text-sm font-medium hover:bg-purple-800/60 hover:text-white transition-all duration-300 cursor-pointer border border-purple-800/50"
                                            >
                                                {tag}
                                            </span>
                                        ))}
                                    </div>
                                    <div className="flex flex-wrap items-center gap-3 sm:gap-4 mt-3 text-sm">
                                        <span className="text-gray-500">
                                            Статус: <span className={`font-medium ${
                                                project.status === 'active' ? 'text-green-400' : 
                                                project.status === 'completed' ? 'text-blue-400' : 
                                                'text-gray-400'
                                            }`}>
                                                {project.status === 'active' ? 'Активный' : 
                                                 project.status === 'completed' ? 'Завершенный' : 
                                                 'Архивированный'}
                                            </span>
                                        </span>
                                        {project.participant_count !== undefined && (
                                            <span className="text-gray-500">
                                                Участники: {project.participant_count}
                                            </span>
                                        )}
                                        {project.unread_messages_count > 0 && (
                                            <span className="px-2 py-1 bg-red-600 text-white rounded-full text-xs">
                                                {project.unread_messages_count} новых сообщений
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <div className="flex sm:flex-col items-center sm:items-end gap-3 flex-shrink-0">
                                    <Link to={`/projects/${project.id}`}>
                                        <button className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors whitespace-nowrap">
                                            Открыть
                                        </button>
                                    </Link>
                                    {project.avatar_path && (
                                        <img 
                                            src={project.avatar_path} 
                                            alt={project.name}
                                            className="w-12 h-12 rounded-full object-cover"
                                        />
                                    )}
                                </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </Header>
    )
}