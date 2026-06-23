import React, { useEffect, useState, useCallback } from 'react'
import Header from '../ui/Header'
import { FaGithub, FaTelegram, FaVk, FaInstagram, FaUniversity, FaBook, FaCode, FaCheck, FaSignOutAlt } from "react-icons/fa";
import { useDispatch, useSelector } from 'react-redux';
import { fetchProfile, clearProfile } from '../store/slices/profile';
import { authAPI, normalizeAssetUrl, profileAPI, projectsAPI } from '../services/api';
import { Link, useNavigate } from 'react-router-dom';
import { websocketService } from '../services/websocket';

const CLIENT_ID = 'Ov23lic2YCRXOp2ivNHk'
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://45.11.92.114:8000'

export default function Profile() {
  const [isGitHubLoading, setIsGitHubLoading] = useState(false);
  const [avatarError, setAvatarError] = useState(false);
  const [gitHubError, setGitHubError] = useState('');
  const [gitHubConnected, setGitHubConnected] = useState(false);
  const [localProfile, setLocalProfile] = useState(null);
  const [userProjects, setUserProjects] = useState([]);
  const [projectsLoading, setProjectsLoading] = useState(false);

  const navigate = useNavigate();
  const dispatch = useDispatch();
  
  // Получаем данные из Redux
  const { profile: reduxProfile, isLoading, error } = useSelector(state => state.profile);
  
  // Используем локальный профиль как fallback
  const profile = localProfile || reduxProfile;

  console.log('👤 Profile component state:', {
    reduxProfile: !!reduxProfile,
    localProfile: !!localProfile,
    isLoading,
    error,
    gitHubConnected
  });

  // Загрузка профиля
  const loadProfile = useCallback(async () => {
    try {
      const result = await dispatch(fetchProfile()).unwrap();
      console.log('✅ Profile loaded successfully:', result);

      let enriched = result;
      if (result && !result.avatar_url && result.avatar_file_id) {
        try {
          const { data } = await profileAPI.getAvatarUrl();
          if (data?.avatar_url) {
            enriched = { ...result, avatar_url: data.avatar_url };
          }
        } catch (avatarErr) {
          console.warn('Could not fetch avatar URL:', avatarErr);
        }
      }
      
      // Сохраняем в localStorage для быстрого доступа
      if (enriched) {
        localStorage.setItem('profile', JSON.stringify(enriched));
        setLocalProfile(enriched);
      }
    } catch (error) {
      console.error('❌ Error loading profile:', error);
      
      // Пробуем получить из localStorage
      const savedProfile = localStorage.getItem('profile');
      if (savedProfile) {
        try {
          const parsedProfile = JSON.parse(savedProfile);
          console.log('📂 Using cached profile from localStorage');
          setLocalProfile(parsedProfile);
        } catch (e) {
          console.error('Error parsing cached profile:', e);
        }
      }
    }
  }, [dispatch]);

  const loadUserProjects = useCallback(async () => {
    try {
      setProjectsLoading(true);
      const response = await projectsAPI.getProjects({ limit: 100, offset: 0 });
      const payload = response?.data;
      const list = Array.isArray(payload)
        ? payload
        : (Array.isArray(payload?.projects) ? payload.projects : []);
      setUserProjects(list);
    } catch (e) {
      console.error('❌ Error loading user projects:', e);
      setUserProjects([]);
    } finally {
      setProjectsLoading(false);
    }
  }, []);

  // Обработка GitHub кода из URL
  const handleGitHubCode = useCallback(async (code) => {
    if (!code) return;
    
    try {
      setIsGitHubLoading(true);
      setGitHubError('');
      
      console.log('🔐 Connecting GitHub with code:', code);
      const response = await profileAPI.getGitHub(code);
      console.log('✅ GitHub connected:', response.data);
      
      setGitHubConnected(true);
      
      // Перезагружаем профиль
      await loadProfile();
      await loadUserProjects();
      
      // Очищаем URL
      window.history.replaceState({}, document.title, window.location.pathname);
      
    } catch (error) {
      console.error('❌ GitHub connection error:', error);
      const errorMessage = error.response?.data?.detail?.[0]?.msg || 
                          error.response?.data?.detail || 
                          error.message || 
                          'Ошибка подключения GitHub';
      setGitHubError(errorMessage);
    } finally {
      setIsGitHubLoading(false);
    }
  }, [loadProfile, loadUserProjects]);

  // Основной эффект загрузки
  useEffect(() => {
    const initProfile = async () => {
      // Проверяем токен
      const token = localStorage.getItem('token');
      if (!token) {
        console.log('🔒 No token found, redirecting to login');
        navigate('/login');
        return;
      }

      await loadProfile();
      await loadUserProjects();

      // Проверяем GitHub code в URL
      const queryString = window.location.search;
      const urlParams = new URLSearchParams(queryString);
      const codeParams = urlParams.get("code");
      
      if (codeParams) {
        await handleGitHubCode(codeParams);
      }
    };

    initProfile();
  }, [dispatch, loadProfile, loadUserProjects, handleGitHubCode, navigate]);

  // Проверяем GitHub в профиле
  useEffect(() => {
    if (profile) {
      // Проверяем наличие OAuth токена для определения подключения
      const hasOAuthConnection = !!profile.github_access_token;
      
      // Ищем просто добавленную ссылку
      const hasGitHubLink = profile.links && profile.links.some(link => 
        link && (link.includes('github.com') || link.includes('github.io'))
      );
      
      setGitHubConnected(hasOAuthConnection);
      console.log('🔍 GitHub connection status:', { 
        oauth: hasOAuthConnection, 
        link: hasGitHubLink,
        connected: hasOAuthConnection,
        token: !!profile.github_access_token
      });
    }
  }, [profile]);

  useEffect(() => {
    setAvatarError(false);
  }, [profile?.avatar_url, profile?.avatar_path, profile?.avatar_file_id]);

  // Функции для работы с GitHub
  const loginWithGitHub = () => {
    setIsGitHubLoading(true);
    setGitHubError('');
    const redirectUri = encodeURIComponent(window.location.origin + window.location.pathname);
    // Добавляем scope 'repo' для доступа к репозиториям
    window.location.assign(
      `https://github.com/login/oauth/authorize?client_id=${CLIENT_ID}&redirect_uri=${redirectUri}&scope=user:email repo`
    );
  };

  // Выход из системы
  const handleLogout = async () => {
    try {
      console.log('🔌 Logging out...');
      
      // Отключаем WebSocket
      websocketService.disconnect();
      
      // Очищаем Redux
      dispatch(clearProfile());
      
      // Очищаем localStorage
      localStorage.removeItem('token');
      localStorage.removeItem('profile');
      
      // Редирект на логин
      navigate('/login');
      
    } catch (error) {
      console.error('❌ Logout error:', error);
    }
  };

  // Навигация
  const goToLogin = () => navigate('/login');
  const goToRegister = () => navigate('/registr');

  // Безопасное получение ссылок
  const getSocialLink = (links, index) => {
    if (!links || !Array.isArray(links)) return null;
    const link = links[index];
    return link && link !== '#' && link.trim() !== '' ? link : null;
  };

  // Компонент для безопасных ссылок
  const SafeSocialLink = ({ href, children, isConnected = false }) => {
    if (!href) {
      return (
        <span className="text-gray-600 cursor-not-allowed opacity-50" title="Ссылка не указана">
          {children}
        </span>
      );
    }

    return (
      <a 
        href={href} 
        target="_blank" 
        rel="noopener noreferrer"
        className={`transition-all duration-300 hover:scale-110 ${
          isConnected ? 'text-green-400 hover:text-green-300' : 'text-gray-400 hover:text-purple-400'
        }`}
        title={isConnected ? 'Подключено' : 'Перейти'}
      >
        {children}
      </a>
    );
  };

  // Пока данные загружаются
  if (isLoading && !profile) {
    return (
      <Header>
        <div className="bg-black p-6 min-h-screen flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
            <p className="text-gray-400">Загрузка профиля...</p>
          </div>
        </div>
      </Header>
    );
  }

  // Если произошла ошибка и нет профиля
  if (error && !profile) {
    return (
      <Header>
        <div className="bg-black p-6 min-h-screen flex items-center justify-center">
          <div className="bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-800 p-8 max-w-md w-full">
            <h1 className="text-2xl text-white text-center mb-6">STUDNET</h1>
            
            <div className="text-red-400 mb-6 p-4 bg-red-900/20 rounded-lg">
              Ошибка загрузки профиля
            </div>
            
            <div className="space-y-4">
              <button 
                type="button"
                onClick={goToLogin}
                className="w-full px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white font-bold rounded-lg transition-all duration-300 hover:scale-105"
              >
                Войти
              </button>
              
              <button 
                onClick={goToRegister}
                type="button"
                className="w-full px-6 py-3 bg-gray-800 hover:bg-gray-700 text-white font-bold rounded-lg transition-all duration-300 hover:scale-105"
              >
                Зарегистрироваться
              </button>
            </div>
          </div>
        </div>
      </Header>
    );
  }

  // Если профиль не загружен
  if (!profile) {
    return (
      <Header>
        <div className="bg-black p-6 min-h-screen flex items-center justify-center">
          <div className="bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-800 p-8 max-w-md w-full">
            <h1 className="text-2xl text-white text-center mb-6">STUDNET</h1>
            
            <div className="text-gray-400 mb-6 text-center">
              Профиль не найден
            </div>
            
            <div className="space-y-4">
              <button 
                type="button"
                onClick={goToLogin}
                className="w-full px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white font-bold rounded-lg transition-all duration-300 hover:scale-105"
              >
                Войти
              </button>
            </div>
          </div>
        </div>
      </Header>
    );
  }

  // Формируем данные для отображения
  const userData = {
    name: profile.name || "Не указано",
    surname: profile.lastname || "Не указано",
    nickname: profile.username || `@user${profile.id || ''}`,
    avatar: (() => {
      const rawAvatar = profile.avatar_url || profile.avatar_path || profile.avatar || null
      if (!rawAvatar || avatarError) return 'https://via.placeholder.com/150'
      return normalizeAssetUrl(rawAvatar)
    })(),
    university: profile.university || "Не указано",
    course: profile.course || "Не указано",
    faculty: profile.faculty || "Не указано",
    description: profile.info || "Расскажите о себе...",
    links: {
      github: getSocialLink(profile.links, 0),
      telegram: getSocialLink(profile.links, 1),
      vk: getSocialLink(profile.links, 2),
      instagram: getSocialLink(profile.links, 3)
    },
    interests: Array.isArray(profile.interests) ? profile.interests : [],
    skills: Array.isArray(profile.skills) ? profile.skills : [],
    projects: userProjects
  };

  return (
    <Header>
      <div className="bg-black p-4 md:p-6 min-h-screen">
        {/* Основная информация */}
        <div className="bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-800 p-6 md:p-8 mb-6 hover:border-gray-700 transition-all duration-300">
          <div className="flex flex-col lg:flex-row items-start gap-8">
            {/* Левая колонка - Аватар и основная информация */}
            <div className="flex-1">
              <div className="flex flex-col md:flex-row items-start md:items-center gap-6">
                {/* Аватар */}
                <div className="flex-shrink-0">
                  <img 
                    src={userData.avatar}
                    alt="Аватар пользователя"
                    className="w-28 h-28 md:w-32 md:h-32 rounded-full object-cover border-4 border-purple-600 shadow-lg shadow-purple-500/20"
                    onError={() => setAvatarError(true)}
                  />
                </div>
                
                {/* Информация */}
                <div className="flex-1">
                  <div className="flex flex-col md:flex-row md:items-center gap-2 md:gap-4 mb-3">
                    <h1 className="text-2xl md:text-3xl font-bold text-white break-words">
                      {userData.name} {userData.surname}
                    </h1>
                    <span className="text-purple-400 font-medium bg-purple-900/30 px-3 py-1 rounded-full text-sm md:text-base truncate max-w-full self-start">
                      {userData.nickname}
                    </span>
                  </div>
                  
                  {/* Образование */}
                  <div className="flex flex-wrap gap-3 mb-4">
                    <div className="flex items-center gap-2 bg-gray-800/50 px-3 py-1.5 rounded-lg">
                      <FaUniversity className="text-purple-400" />
                      <span className="text-gray-300 text-sm md:text-base">{userData.university}</span>
                    </div>
                    <div className="flex items-center gap-2 bg-gray-800/50 px-3 py-1.5 rounded-lg">
                      <FaBook className="text-purple-400" />
                      <span className="text-gray-300 text-sm md:text-base">{userData.course}</span>
                    </div>
                  </div>
                  <p className="text-gray-300 mb-4 leading-relaxed text-sm md:text-base break-words">
                    {userData.description}
                  </p>

                  {/* Соцсети */}
                  <div className="flex gap-4 items-center">
                    <SafeSocialLink href={userData.links.github} isConnected={gitHubConnected}>
                      <div className="flex items-center gap-2">
                        <FaGithub size={20} className="md:w-6 md:h-6" />
                        {gitHubConnected && (
                          <FaCheck className="text-green-400 text-xs md:text-sm" />
                        )}
                      </div>
                    </SafeSocialLink>
                    <SafeSocialLink href={userData.links.telegram}>
                      <FaTelegram size={20} className="md:w-6 md:h-6" />
                    </SafeSocialLink>
                    <SafeSocialLink href={userData.links.vk}>
                      <FaVk size={20} className="md:w-6 md:h-6" />
                    </SafeSocialLink>
                    <SafeSocialLink href={userData.links.instagram}>
                      <FaInstagram size={20} className="md:w-6 md:h-6" />
                    </SafeSocialLink>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Правая колонка - Действия */}
            <div className="w-full lg:w-auto">
              <div className="space-y-4">
                {gitHubError && (
                  <div className="text-red-400 text-sm bg-red-900/20 p-3 rounded-lg">
                    {gitHubError}
                  </div>
                )}
                
                {gitHubConnected && (
                  <div className="text-green-400 text-sm bg-green-900/20 p-3 rounded-lg flex items-center justify-center gap-2">
                    <FaCheck />
                    GitHub подключен
                  </div>
                )}
                
                <button 
                  type="button"
                  onClick={loginWithGitHub}
                  disabled={isGitHubLoading || gitHubConnected}
                  className={`w-full lg:w-64 px-4 py-3 text-white font-bold rounded-xl transition-all duration-300 hover:scale-105 shadow-lg flex items-center justify-center gap-2 ${
                    gitHubConnected 
                      ? 'bg-green-600 hover:bg-green-700 shadow-green-500/20 cursor-not-allowed' 
                      : 'bg-purple-600 hover:bg-purple-700 shadow-purple-500/20'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  {isGitHubLoading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      Подключение...
                    </>
                  ) : gitHubConnected ? (
                    <>
                      <FaCheck />
                      GitHub подключен
                    </>
                  ) : (
                    <>
                      <FaGithub />
                      Подключить GitHub
                    </>
                  )}
                </button>
                
                <button 
                  type="button"
                  onClick={handleLogout}
                  className="w-full lg:w-64 px-4 py-3 bg-red-500 hover:bg-red-600 text-white font-bold rounded-xl transition-all duration-300 hover:scale-105 shadow-lg shadow-red-500/20 flex items-center justify-center gap-2"
                >
                  <FaSignOutAlt />
                  Выйти
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Интересы и навыки */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Интересы */}
          <div className="bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-800 p-6 hover:border-gray-700 transition-all duration-300">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <FaCode className="text-purple-400" />
              Интересы
            </h2>
            <div className="flex flex-wrap gap-3">
              {userData.interests.length > 0 ? (
                userData.interests.map((interest, index) => (
                  <span 
                    key={index}
                    className="px-4 py-2 bg-purple-900/40 text-purple-300 rounded-full text-sm font-medium hover:bg-purple-800/60 hover:text-white transition-all duration-300 cursor-pointer border border-purple-800/50"
                  >
                    {interest}
                  </span>
                ))
              ) : (
                <span className="text-gray-400 italic">Интересы не указаны</span>
              )}
            </div>
          </div>

          {/* Навыки */}
          <div className="bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-800 p-6 hover:border-gray-700 transition-all duration-300">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <FaCode className="text-blue-400" />
              Навыки
            </h2>
            <div className="flex flex-wrap gap-3">
              {userData.skills.length > 0 ? (
                userData.skills.map((skill, index) => (
                  <span 
                    key={index}
                    className="px-4 py-2 bg-blue-900/40 text-blue-300 rounded-full text-sm font-medium hover:bg-blue-800/60 hover:text-white transition-all duration-300 cursor-pointer border border-blue-800/50"
                  >
                    {skill}
                  </span>
                ))
              ) : (
                <span className="text-gray-400 italic">Навыки не указаны</span>
              )}
            </div>
          </div>
        </div>

        {/* Проекты */}
        <div className="bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-800 p-6 hover:border-gray-700 transition-all duration-300">
          <h2 className="text-xl font-bold text-white mb-6">Проекты</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projectsLoading ? (
              <div className="col-span-full text-center text-gray-400 py-8 italic">
                Загрузка проектов...
              </div>
            ) : null}
            {userData.projects.length > 0 ? (
              userData.projects.map((project, index) => {
                const tagList = Array.isArray(project.tags)
                  ? project.tags
                  : (Array.isArray(project.technologies) ? project.technologies : []);
                return (
                <div key={project.id != null ? String(project.id) : index} className="bg-gray-800/30 border border-gray-700 rounded-xl p-5 hover:border-purple-600/50 hover:shadow-lg hover:shadow-purple-500/10 transition-all duration-300 group">
                  <h3 className="text-lg font-semibold text-white mb-2 group-hover:text-purple-300 transition-colors">
                    {project.name || `Проект ${index + 1}`}
                  </h3>
                  <p className="text-gray-400 text-sm mb-4 group-hover:text-gray-300 transition-colors line-clamp-2 break-words">
                    {project.description || "Описание проекта отсутствует"}
                  </p>
                  
                  {tagList.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-4">
                      {tagList.map((tech, techIndex) => (
                        <span 
                          key={techIndex}
                          className="px-3 py-1 bg-gray-700/50 text-gray-300 rounded-full text-xs border border-gray-600/50 group-hover:border-gray-500 transition-colors"
                        >
                          {tech}
                        </span>
                      ))}
                    </div>
                  )}
                  
                  <Link
                    to={project?.id ? `/projects/${project.id}` : '/projects'}
                    className="text-purple-400 hover:text-purple-300 font-medium text-sm transition-colors flex items-center gap-1 group-hover:gap-2 duration-300"
                  >
                    Посмотреть проект
                    <span className="group-hover:translate-x-1 transition-transform">→</span>
                  </Link>
                </div>
              );
              })
            ) : (
              <div className="col-span-full text-center text-gray-400 py-8 italic">
                Проекты не добавлены
              </div>
            )}
          </div>
        </div>
      </div>
    </Header>
  )
}