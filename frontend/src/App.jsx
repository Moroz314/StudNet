import { useEffect, useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import './App.css'
import Main from './components/Main'
import Profile from './components/Profile';
import Registration from './components/Auth/registration/Registration';
import ProjectWorkspace from './components/Projects/Project/ProjectWorkspace';
import Registr_code from './components/Auth/registration/Registr_code';
import Registration_profile from './components/Auth/registration/Registration_profile';
import Login from './components/Auth/Login';
import Chats from './components/Chats/ChatsMain';
import AddChat from './components/Chats/AddChat';
import FAQ from './components/FAQ';
import Friends from './components/Friends';
import Notifications from './components/Notifications';
import { ProtectedRoute } from './components/Auth/ProtectedRoute';
import NoAuth from './components/NoAuth.jsx';
import { websocketService } from './services/websocket';
import { fetchProfile } from './store/slices/profile.js';
import { isAuthTokenError, clearAuthSession, isProfileMissingError, formatApiError } from './services/api';
import PMenu from './components/Projects/Proj_menu/PMenu.jsx';
import CreateProject from './components/Projects/CreateProject.jsx';
import ProjectDetail from './components/Projects/ProjectDetail.jsx';
import CreateWorkspace from './components/Projects/CreateWorkspace.jsx';
import WorkspaceDetail from './components/Projects/WorkspaceDetail.jsx';
import ProjectsFeed from './components/Feed/ProjectsFeed.jsx';
import FeedProjectDetails from './components/Feed/FeedProjectDetails.jsx';
import PublishToFeed from './components/Projects/PublishToFeed.jsx';
import UserProfile from './components/UserProfile.jsx';
import AnnouncementsFeed from './components/Feed/AnnouncementsFeed.jsx';
import AnnouncementDetail from './components/Projects/AnnouncementDetail.jsx';

function App() {
  const dispatch = useDispatch();
  const { profile, isLoading, error: profileError } = useSelector(state => state.profile);
  const token = localStorage.getItem('token') || localStorage.getItem('access_token');
  const [authError, setAuthError] = useState(null);
  
  // 🔥 ЗАГРУЗКА ПРОФИЛЯ С ОБРАБОТКОЙ ОШИБОК
  useEffect(() => {
    if (!token) {
      console.log('🔍 App: No token, skipping profile load');
      return;
    }
    
    if (profile || isLoading) {
      console.log('⏭️ App: Profile already loaded or loading');
      return;
    }
    
    console.log('🔍 App: Loading profile with token...');
    
    const loadProfile = async () => {
      try {
        const result = await dispatch(fetchProfile()).unwrap();
        console.log('✅ App: Profile loaded successfully');
        setAuthError(null); // Очищаем ошибку при успехе
      } catch (error) {
        console.error('❌ App: Failed to load profile:', error);
        
        if (isAuthTokenError(error)) {
          console.log('🔒 App: Authentication failed (expired or invalid token)');
          setAuthError(formatApiError(error));
          clearAuthSession();
          
          // Отключаем WebSocket
          if (websocketService.isConnected()) {
            websocketService.disconnect();
          }
        } else if (isProfileMissingError(error)) {
          setAuthError('Регистрация не завершена. Войдите с email и паролем.');
          clearAuthSession();
        }
      }
    };
    
    loadProfile();
  }, [dispatch, token, profile, isLoading]);
  
  // 🔥 ПРОСТОЙ WEBSOCKET МЕНЕДЖЕР
  useEffect(() => {
    if (!token || !profile?.id || authError) {
      console.log('🔌 App: Skipping WebSocket - no auth');
      if (websocketService.isConnected()) {
        websocketService.disconnect();
      }
      return;
    }
    
    console.log('🔧 App: WebSocket check', {
      userId: profile.id,
      isConnected: websocketService.isConnected(),
      authError
    });
    
    // Подключаем WebSocket только если не подключены
    if (!websocketService.isConnected()) {
      console.log('🚀 App: Starting WebSocket for user', profile.id);
      websocketService.connect(profile.id);
    }
    
    // Очистка при размонтировании
    return () => {
      console.log('🧹 App: WebSocket effect cleanup');
      // Не отключаем здесь - оставляем соединение живым
    };
  }, [token, profile?.id, authError]);
  
  // 🔥 Глобальная очистка
  useEffect(() => {
    return () => {
      console.log('🔌 App: Global cleanup - disconnecting WebSocket');
      websocketService.disconnect();
    };
  }, []);
  
  // 🔥 Показываем ошибку аутентификации
  if (authError) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="bg-red-900/30 border border-red-700 rounded-xl p-8 max-w-md text-center">
          <div className="text-red-400 text-5xl mb-4">🔒</div>
          <h2 className="text-2xl font-bold text-white mb-2">Ошибка авторизации</h2>
          <p className="text-gray-300 mb-6">{authError}</p>
          <div className="space-y-3">
            <button
              onClick={() => {
                clearAuthSession();
                window.location.href = '/login';
              }}
              className="bg-red-600 hover:bg-red-700 text-white px-6 py-3 rounded-lg w-full"
            >
              Войти
            </button>
            <button
              onClick={() => {
                clearAuthSession();
                window.location.href = '/registr';
              }}
              className="bg-gray-800 hover:bg-gray-700 text-white px-6 py-3 rounded-lg w-full border border-gray-600"
            >
              Зарегистрироваться
            </button>
          </div>
        </div>
      </div>
    );
  }
  
  // 🔥 Показываем загрузку
  if (token && !profile && isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
          <p className="text-gray-400">Загрузка профиля...</p>
        </div>
      </div>
    );
  }
  
  const isAuthenticated = !!token && !!profile?.id && !authError;
  
  return (
    <>
      <Routes>
        {/* Публичные маршруты */}
        <Route path="/auth" element={<NoAuth />} />
        <Route path="/login" element={<Login />} />
        <Route path="/registr" element={<Registration />} />
        <Route path="/registr_code" element={<Registr_code />} />
        <Route path="/registr_profile" element={<Registration_profile />} />
        
        {/* Защищенные маршруты */}
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<Main />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/user_profile/:userId?" element={<UserProfile />} />
          <Route path="/chats" element={<Chats />} />
          <Route path="/projects" element={<PMenu />} />
          <Route path="/projects/:projectId" element={<ProjectDetail />} />
          <Route path="/projects/create" element={<CreateProject />} />
          <Route path="/projects/:projectId/workspaces/create" element={<CreateWorkspace />} />
          <Route path="/projects/:projectId/workspaces/:workspaceId" element={<WorkspaceDetail />} />
          <Route path="/projects/:projectId/workspaces/create" element={<CreateWorkspace />} />
          <Route path="/projects/:projectId/workspaces/:workspaceId" element={<WorkspaceDetail />} />
          <Route path="/projects/:projectId/publish-feed" element={<PublishToFeed />} />
          <Route path="/projects/:projectId/announcements/:announcementId" element={<AnnouncementDetail />} />
          <Route path="/feed" element={<ProjectsFeed />} />
          <Route path="/feed/projects/:projectId" element={<FeedProjectDetails />} />
          <Route path="/announcements" element={<AnnouncementsFeed />} />
          <Route path="/announcements/:announcementId" element={<AnnouncementDetail />} />
          <Route path="/add_chat" element={<AddChat />} />
          <Route path="/faq" element={<FAQ />} />
          <Route path="/friends" element={<Friends />} />
          <Route path="/notifications" element={<Notifications />} />
        </Route>
        
        {/* Редирект */}
        <Route path="*" element={
          <Navigate to={isAuthenticated ? "/" : "/auth"} replace />
        } />
      </Routes>
    </>
  );
}

export default App;