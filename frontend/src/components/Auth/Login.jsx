import React, { useState } from 'react'
import Header from '../../ui/Header'
import { FaEnvelope, FaLock } from "react-icons/fa";
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { fetchAuth, selectAuthError, selectAuthLoading } from '../../store/slices/auth';

export default function Login() {
    const navigate = useNavigate();
    const dispatch = useDispatch();
    
    const error = useSelector(selectAuthError);
    const isLoading = useSelector(selectAuthLoading);

    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')

    async function HandlerSubmitRegistration(e) {
        e.preventDefault();

        if (!email || !password) {
            alert('Пожалуйста, заполните все поля');
            return;
        }

        const userData = {
            email: email,
            password: password
        }
        
        console.log('Login attempt with:', userData);

        try {
            // Диспатчим action и ждем его завершения
            const result = await dispatch(fetchAuth(userData));
            
            console.log('Dispatch result:', result);
            
            // Проверяем, был ли action выполнен успешно
            if (fetchAuth.fulfilled.match(result)) {
                // ВАЖНО: данные теперь в result.payload (не response.payload!)
                const responseData = result.payload;
                
                console.log('Login successful, response data:', responseData);
                
                // Ищем токен в разных местах (как в вашем authSlice)
                const token = responseData?.access_token;
                
                if (token) {
                    console.log('Token received:', token.substring(0, 20) + '...');
                    navigate('/profile');
                } else {
                    console.error('Token not found in response:', responseData);
                    alert('Ошибка: токен не найден в ответе сервера');
                }
            } else if (fetchAuth.rejected.match(result)) {
                // Обработка ошибки из rejectWithValue
                console.error('Login rejected:', result.payload || result.error);
                
                // Показываем ошибку пользователю
                const errorMessage = 
                    result.payload?.detail?.[0]?.msg || 
                    result.payload?.message || 
                    result.payload?.detail ||
                    result.error?.message ||
                    'Неверный email или пароль';
                
                alert(`Ошибка входа: ${errorMessage}`);
            }
            
        } catch (error) {
            console.error('Unexpected error in login handler:', error);
            alert(`Произошла непредвиденная ошибка: ${error.message}`);
        }
    }

    return (
        <Header>
            <div className="bg-white dark:bg-black py-8">
                <div className="max-w-4xl mx-auto px-4 sm:px-6">
                    {/* Заголовок */}
                    <div className="text-center mb-8">
                        <h1 className="text-2xl sm:text-3xl font-bold text-black dark:text-white mb-2">Войти в аккаунт</h1>
                        <p className="text-gray-400">Заполните информацию о себе</p>
                    </div>

                    {/* Показываем ошибку, если есть */}
                    {error && (
                        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-xl">
                            <p className="text-red-400 text-center">
                                Ошибка: {error.message || error.detail || 'Неверные учетные данные'}
                            </p>
                        </div>
                    )}

                    <form className="space-y-6" onSubmit={HandlerSubmitRegistration}>
                        {/* Основная информация */}
                        <div className="bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-800 p-6 hover:border-gray-700 transition-all duration-300">
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
                                            disabled={isLoading}
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
                                            disabled={isLoading}
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="text-center">
                            <button 
                                type="submit"
                                className={`px-8 py-4 ${isLoading ? 'bg-purple-800' : 'bg-purple-600 hover:bg-purple-700'} text-white font-bold rounded-xl transition-all duration-300 ${!isLoading && 'hover:scale-105'} shadow-lg shadow-purple-500/20 flex items-center justify-center mx-auto`}
                                disabled={isLoading}
                            >
                                {isLoading ? (
                                    <>
                                        <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                        Вход...
                                    </>
                                ) : 'Войти'}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </Header>
    );
}