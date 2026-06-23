// components/Auth/ProtectedRoute.jsx - ПОЛНОСТЬЮ ИСПРАВЛЕННЫЙ
import { useEffect, useState, useRef } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import { websocketService } from '../../services/websocket';
import { fetchProfile } from '../../store/slices/profile';
import { isAuthTokenError, clearAuthSession, isProfileMissingError, formatApiError } from '../../services/api';

export const ProtectedRoute = () => {
  const location = useLocation();
  const dispatch = useDispatch();
  const { profile, isLoading, error } = useSelector(state => state.profile);
  
  // 🔥 ИСПОЛЬЗУЕМ ПРАВИЛЬНЫЙ КЛЮЧ И ДОБАВЛЯЕМ REF ДЛЯ ОТСЛЕЖИВАНИЯ
  const token = localStorage.getItem('token') || localStorage.getItem('access_token');
  const [profileCheckComplete, setProfileCheckComplete] = useState(false);
  const [hasTokenError, setHasTokenError] = useState(false);
  
  // 🔥 REF ДЛЯ ОТСЛЕЖИВАНИЯ КОЛИЧЕСТВА ПОПЫТОК
  const checkAttemptsRef = useRef(0);
  const maxAttempts = 2; // Максимум 2 попытки
  
  console.log('🔒 ProtectedRoute check:', {
    hasToken: !!token,
    tokenValue: token ? token.substring(0, 20) + '...' : 'none',
    profileExists: !!profile,
    profileId: profile?.id,
    isLoading,
    errorStatus: error?.status,
    attempts: checkAttemptsRef.current,
    currentPath: location.pathname,
    profileCheckComplete,
    hasTokenError
  });
  
  // 🔥 ЭФФЕКТ ДЛЯ ПРОВЕРКИ ПРОФИЛЯ С ЗАЩИТОЙ ОТ ПЕТЛИ
  useEffect(() => {
    let isMounted = true;
    
    // 🔥 ФУНКЦИЯ ОЧИСТКИ ТОКЕНА
    const clearInvalidToken = () => {
      console.log('🧹 Clearing invalid token...');
      clearAuthSession();
      
      if (websocketService.isConnected()) {
        websocketService.disconnect();
      }
      
      if (isMounted) {
        setHasTokenError(true);
        setProfileCheckComplete(true);
      }
    };
    
    const checkProfile = async () => {
      // 🔥 Если уже достигли максимального количества попыток
      if (checkAttemptsRef.current >= maxAttempts) {
        console.log('⏹️ Max profile check attempts reached');
        if (isMounted) {
          setProfileCheckComplete(true);
        }
        return;
      }
      
      // 🔥 Если нет токена - не проверяем
      if (!token) {
        console.log('🔒 No token, skipping profile check');
        if (isMounted) {
          setProfileCheckComplete(true);
        }
        return;
      }
      
      // 🔥 Если профиль уже загружен или есть ошибка токена
      if (profile || hasTokenError) {
        console.log('⏭️ Profile already loaded or token error');
        if (isMounted) {
          setProfileCheckComplete(true);
        }
        return;
      }
      
      // 🔥 Если уже идет загрузка - выходим
      if (isLoading) {
        console.log('⏳ Profile loading in progress');
        return;
      }
      
      checkAttemptsRef.current++;
      console.log(`🔍 Profile check attempt ${checkAttemptsRef.current}/${maxAttempts}`);
      
      try {
        const result = await dispatch(fetchProfile()).unwrap();
        console.log('✅ Profile loaded successfully');
        
        if (isMounted) {
          setProfileCheckComplete(true);
          setHasTokenError(false);
          checkAttemptsRef.current = 0; // Сбрасываем счетчик при успехе
        }
      } catch (error) {
        console.error('❌ Profile check failed:', {
          status: error.status,
          message: error.message
        });
        
        if (!isMounted) return;
        
        if (isAuthTokenError(error)) {
          console.log('🔒 Authentication failed (token expired or invalid)');
          clearInvalidToken();
        } else if (isProfileMissingError(error)) {
          console.log('👤 Profile missing — clearing incomplete registration session');
          clearInvalidToken();
        } else {
          // Другие ошибки - завершаем проверку
          setProfileCheckComplete(true);
        }
      }
    };
    
    // 🔥 Запускаем проверку с небольшим debounce
    const timeoutId = setTimeout(() => {
      checkProfile();
    }, 100);
    
    return () => {
      isMounted = false;
      clearTimeout(timeoutId);
    };
  }, [dispatch, token, profile, isLoading, hasTokenError]);
  
  // 🔥 Маршруты, доступные без проверки профиля
  const publicRoutes = [
    '/auth',
    '/login', 
    '/registr',
    '/registr_code',
    '/registr_profile'
  ];
  
  // 🔥 Если публичный маршрут - сразу пропускаем
  if (publicRoutes.includes(location.pathname)) {
    return <Outlet />;
  }
  
  // 🔥 Пока проверяем - показываем загрузку
  if (token && !profileCheckComplete) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
          <p className="text-gray-400">
            {checkAttemptsRef.current > 0 ? 'Проверка сессии...' : 'Загрузка...'}
          </p>
        </div>
      </div>
    );
  }
  
  // 🔥 ЕСЛИ ТОКЕН НЕВАЛИДЕН ИЛИ ИСТЕК
  if (hasTokenError) {
    console.log('🔒 Token error detected, redirecting to login');
    return <Navigate to="/login" state={{ 
      from: location, 
      message: 'Сессия истекла или регистрация не завершена. Войдите с email и паролем.' 
    }} replace />;
  }
  
  // 🔥 ЕСЛИ НЕТ ТОКЕНА - на вход
  if (!token) {
    console.log('🔒 No token found in localStorage, redirecting to auth');
    console.log('🔍 Available localStorage keys:', Object.keys(localStorage));
    return <Navigate to="/auth" state={{ from: location }} replace />;
  }
  
  // 🔥 ЕСЛИ ТОКЕН ЕСТЬ, НО ПРОФИЛЯ НЕТ
  if (token && !profile && profileCheckComplete) {
    console.log('👤 Has token but no profile');
    
    // Разрешаем доступ к созданию профиля
    if (location.pathname === '/registr_profile') {
      return <Outlet />;
    }
    
    // Иначе перенаправляем на создание профиля
    return <Navigate to="/registr_profile" state={{ from: location }} replace />;
  }
  
  // 🔥 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ
  console.log('✅ All checks passed, allowing access');
  return <Outlet />;
};