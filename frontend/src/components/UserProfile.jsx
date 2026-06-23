import React, { useEffect, useState, useCallback, useRef } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import Header from '../ui/Header'
import { fetchViewedProfile, clearViewedProfile } from '../store/slices/viewedProfile';
import { profileAPI } from '../services/api';
import { FaGithub, FaTelegram, FaVk, FaInstagram, FaUniversity, FaBook, FaCode } from "react-icons/fa";

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://45.11.92.114:8000'

export default function UserProfile() {
  const { userId: urlUserId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  
  const userId = urlUserId || location.state?.userId || location.state;
  
  const [avatarError, setAvatarError] = useState(false);
  const [gitHubConnected, setGitHubConnected] = useState(false);
  const [userProjects, setUserProjects] = useState([]);
  const [projectsLoading, setProjectsLoading] = useState(false);
  
  // Используем viewedProfile вместо profile
  const { profile: viewedProfile, isLoading, error } = useSelector(state => state.viewedProfile);
  const profile = viewedProfile;
  
  const loadingRef = useRef(false);
  const lastUserIdRef = useRef(null);

  const loadProfile = useCallback(async () => {
    if (!userId) {
      console.warn('No userId provided');
      return;
    }
    
    if (lastUserIdRef.current === userId && loadingRef.current) {
      return;
    }
    
    try {
      loadingRef.current = true;
      lastUserIdRef.current = userId;
      await dispatch(fetchViewedProfile(userId)).unwrap();
    } catch (error) {
      console.error('Error loading profile:', error);
    } finally {
      loadingRef.current = false;
    }
  }, [dispatch, userId]);

  const loadUserProjects = useCallback(async () => {
    if (!userId) return;

    try {
      setProjectsLoading(true);
      const { data } = await profileAPI.getUserProjects(userId, 0, 50);
      setUserProjects(Array.isArray(data?.items) ? data.items : []);
    } catch (error) {
      console.error('Error loading user projects:', error);
      setUserProjects([]);
    } finally {
      setProjectsLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    if (userId) {
      loadProfile();
      loadUserProjects();
    }
    
    return () => {
      dispatch(clearViewedProfile());
    };
  }, [userId, loadProfile, loadUserProjects, dispatch]);

  const handleProjectClick = (project) => {
    if (!project?.is_published_in_feed || !project?.project_id) return;
    navigate(`/feed/projects/${project.project_id}`);
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
              Ошибка загрузки профиля: {error}
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
      if (String(rawAvatar).startsWith('http')) return rawAvatar
      return `${API_BASE_URL}${rawAvatar}`
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
                      <FaGithub size={20} className="md:w-6 md:h-6" />
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
          {projectsLoading ? (
            <div className="text-center text-gray-400 py-8">Загрузка проектов...</div>
          ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {userProjects.length > 0 ? (
              userProjects.map((project) => {
                const isClickable = Boolean(project.is_published_in_feed && project.project_id);
                return (
                <div
                  key={project.project_id}
                  role={isClickable ? 'button' : undefined}
                  tabIndex={isClickable ? 0 : undefined}
                  onClick={() => handleProjectClick(project)}
                  onKeyDown={(e) => {
                    if (isClickable && (e.key === 'Enter' || e.key === ' ')) {
                      e.preventDefault();
                      handleProjectClick(project);
                    }
                  }}
                  className={[
                    'bg-gray-800/30 border border-gray-700 rounded-xl p-5 transition-all duration-300',
                    isClickable
                      ? 'hover:border-purple-600/50 hover:shadow-lg hover:shadow-purple-500/10 cursor-pointer group'
                      : 'cursor-default opacity-90',
                  ].join(' ')}
                >
                  <h3 className={[
                    'text-lg font-semibold text-white mb-2 transition-colors',
                    isClickable ? 'group-hover:text-purple-300' : '',
                  ].join(' ')}>
                    {project.name || 'Проект'}
                  </h3>
                  <p className={[
                    'text-gray-400 text-sm mb-4 transition-colors line-clamp-2 break-words',
                    isClickable ? 'group-hover:text-gray-300' : '',
                  ].join(' ')}>
                    {project.description || 'Описание проекта отсутствует'}
                  </p>
                  
                  {project.tags && project.tags.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-4">
                      {project.tags.map((tech, techIndex) => (
                        <span 
                          key={techIndex}
                          className="px-3 py-1 bg-gray-700/50 text-gray-300 rounded-full text-xs border border-gray-600/50"
                        >
                          {tech}
                        </span>
                      ))}
                    </div>
                  )}

                  {isClickable ? (
                    <span className="text-purple-400 group-hover:text-purple-300 font-medium text-sm transition-colors flex items-center gap-1 group-hover:gap-2 duration-300">
                      Открыть в ленте
                      <span className="group-hover:translate-x-1 transition-transform">→</span>
                    </span>
                  ) : (
                    <span className="text-gray-500 text-xs">Проект не опубликован в ленте</span>
                  )}
                </div>
              )})
            ) : (
              <div className="col-span-full text-center text-gray-400 py-8 italic">
                Проекты не добавлены
              </div>
            )}
          </div>
          )}
        </div>
      </div>
    </Header>
  )
}