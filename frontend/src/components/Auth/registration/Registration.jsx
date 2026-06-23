import React, { useState } from 'react'
import Header from '../../../ui/Header'
import { FaUser, FaEnvelope, FaLock, FaGithub, FaTelegram, FaVk, FaInstagram, FaUniversity, FaBook } from "react-icons/fa";
import { authAPI } from '../../../services/api';
import { useNavigate } from 'react-router-dom';


export default function Registration() {
    const navigate = useNavigate();

    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')

    async function HandlerSubmitReistration(e){
        e.preventDefault();

        if ( !email  || !password || !confirmPassword) {
            alert('Пожалуйста, заполните все поля');
            return;
        }

        if (password.length < 6) {
            alert('Пароль должен содержать минимум 6 символов');
            return;
        }


        if (password !== confirmPassword) {
            alert('Пароли не совпадают');
            return;
        }
        const userData = {
                email: email,
                password: password
        }
        console.log(userData)
        try {
                const response = await authAPI.register(userData);
                    
                console.log('Registration response:', response);
        
                if (response.data.message == "Код подтверждения отправлен на ваш email") {

                   navigate('/registr_code', { 
                      state: { email: userData.email } 
                  });
                        
                } else {
                    alert('Код подтверждения не отправлен на ваш email');
                }
        
        } catch (error) {
    console.error('Registration error:', error);
    
    // Детальная диагностика
    console.log('🔍 Error details:', {
        message: error.message,
        code: error.code,
        config: {
            url: error.config?.url,
            baseURL: error.config?.baseURL,
            method: error.config?.method,
            data: error.config?.data
        },
        response: error.response,
        request: error.request
    });
    
    if (error.code === 'ECONNABORTED') {
        alert('Сервер не отвечает. Проверьте:\n1. Запущен ли бэкенд на 45.11.92.114:8000\n2. Не блокирует ли брандмауэр');
    } else if (error.response) {
        // Сервер ответил с ошибкой
        const errorMessage = error.response?.data?.detail?.[0]?.msg || 
                           error.response?.data?.message || 
                           error.response?.data?.detail ||
                           `Ошибка сервера: ${error.response.status}`;
        alert(errorMessage);
    } else if (error.request) {
        // Запрос был сделан, но ответа нет
        alert('Не удалось подключиться к серверу 45.11.92.114:8000\n\nПроверьте:\n✅ Запущен ли бэкенд сервер\n✅ Правильный ли порт (8000)\n✅ Настройки CORS на бэкенде');
    } else {
        alert('Неизвестная ошибка: ' + error.message);
    }
}

    }


  return (
    <Header>
          <div className="bg-white dark:bg-black py-8">
            <div className="max-w-4xl mx-auto px-4 sm:px-6">
              {/* Заголовок */}
              <div className="text-center mb-8">
                <h1 className="text-2xl sm:text-3xl font-bold text-black dark:text-white mb-2">Регистрация</h1>
                <p className="text-gray-400">Заполните информацию о себе</p>
              </div>
    
              <form className="space-y-6" onSubmit={HandlerSubmitReistration}>
                {/* Основная информация */}
                <div className="bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-800 p-6 hover:border-gray-700 transition-all duration-300">
                  <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                    <FaUser className="text-purple-400" />
                    Основная информация
                  </h2>
                  
                  <div className="grid grid-cols-1 md:grid-cols-1 gap-4">
                    
                    <div>
                      <label className="block text-gray-300 text-sm font-medium mb-2">
                        Email *
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                          <FaEnvelope className="text-gray-500" />
                        </div>
                        <input 
                          type="email"
                          name="email"
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          className="w-full pl-10 pr-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300 backdrop-blur-sm"
                          placeholder="email@example.com"
                        />
                      </div>
                    </div>
                    
                    <div>
                      <label className="block text-gray-300 text-sm font-medium mb-2">
                        Пароль *
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                          <FaLock className="text-gray-500" />
                        </div>
                        <input 
                          type="password"
                          name="password"
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          required
                          className="w-full pl-10 pr-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300 backdrop-blur-sm"
                          placeholder="Введите пароль"
                        />
                      </div>
                    </div>
                    
                    <div>
                      <label className="block text-gray-300 text-sm font-medium mb-2">
                        Подтвердите пароль *
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                          <FaLock className="text-gray-500" />
                        </div>
                        <input 
                          type="password"
                          name="confirmPassword"
                          value={confirmPassword}
                          onChange={(e) => setConfirmPassword(e.target.value)}
                          required
                          className="w-full pl-10 pr-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300 backdrop-blur-sm"
                          placeholder="Повторите пароль"
                        />
                      </div>
                    </div>
                  </div>
                </div>
    
             
    
                <div className="text-center">
                  <button 
                    type="submit"
                    className="px-8 py-4 bg-purple-600 hover:bg-purple-700 text-white font-bold rounded-xl transition-all duration-300 hover:scale-105 shadow-lg shadow-purple-500/20"
                  >
                    Зарегистрироваться
                  </button>
                </div>
              </form>
            </div>
          </div>
        </Header>
  )
}
