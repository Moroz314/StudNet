import React, { useState } from 'react'
import logo from '../assets/image.png'
import { useSelector } from 'react-redux';
import { GoHome, GoPerson, GoPaste, GoBook, GoListUnordered } from "react-icons/go";
import { GoBell } from "react-icons/go";
import { GoQuestion } from "react-icons/go";
import { GoBookmark } from "react-icons/go";
import { GoComment } from "react-icons/go";
import { GoPeople } from "react-icons/go";
import { GoPencil } from "react-icons/go";
import { GoRocket } from "react-icons/go";
import { Link } from 'react-router-dom';
import { useTheme } from '../hooks/useTheme';
import { selectIsAuth } from '../store/slices/auth';
import { normalizeAssetUrl } from '../services/api';

export default function Header({ children }) {

  const {theme, toggleTheme} = useTheme()
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  const isAuth = useSelector(selectIsAuth)
  const profile = useSelector(state => state.profile.profile)
  const name = profile?.name || ''
  const username = profile?.username || ''
  const avatar = normalizeAssetUrl(profile?.avatar_url || profile?.avatar_path || '')



  return (
    <div className="flex h-screen relative overflow-hidden">
      {/* Мобильное бургер-меню */}
      {isMobileMenuOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          {/* Затемнение фона */}
          <div 
            className="flex-1 bg-black/50"
            onClick={() => setIsMobileMenuOpen(false)}
          />
          
          {/* Выдвижная панель */}
          <div className="w-[70px] bg-[#ffff] dark:bg-[#000000] flex flex-col items-center justify-center py-4 space-y-20">
            <div className="w-[70px] h-[70x] absolute top-5">
            </div>
             <Link to='/feed' onClick={() => setIsMobileMenuOpen(false)}>
              <div className='transition-all duration-500 w-[50px] h-[50px] rounded-2xl hover:bg-[#9a17d6] flex justify-center items-center cursor-pointer'>
              <GoRocket className="w-[30px] h-[30px] dark:text-white text-black" />
              </div>
            </Link>
            <Link to='/projects' onClick={() => setIsMobileMenuOpen(false)}>
                <div className='transition-all duration-500 w-[50px] h-[50px] rounded-2xl hover:bg-[#9a17d6] flex justify-center items-center cursor-pointer'>
                <GoPencil className="w-[30px] h-[30px] dark:text-white text-black" />
                </div>
            </Link>
            <Link to='/chats' onClick={() => setIsMobileMenuOpen(false)}>
              <div className='transition-all duration-500 w-[50px] h-[50px] rounded-2xl hover:bg-[#9a17d6] flex justify-center items-center cursor-pointer'>
              <GoComment className="w-[30px] h-[30px] dark:text-white text-black" />
              </div>
            </Link>
            <Link to='/friends' onClick={() => setIsMobileMenuOpen(false)}>
              <div className='transition-all duration-500 w-[50px] h-[50px] rounded-2xl hover:bg-[#9a17d6] flex justify-center items-center cursor-pointer'>
              <GoPeople className="w-[30px] h-[30px] dark:text-white text-black" />
              </div>
            </Link>
            <Link to='/announcements' onClick={() => setIsMobileMenuOpen(false)}>
              <div className='transition-all duration-500 w-[50px] h-[50px] rounded-2xl hover:bg-[#9a17d6] flex justify-center items-center cursor-pointer'>
              <GoPaste className="w-[30px] h-[30px] dark:text-white text-black" />
              </div>
            </Link>
            <div className='transition-all duration-500 w-[50px] h-[50px] rounded-2xl hover:bg-[#9a17d6] flex justify-center items-center cursor-pointer'>
            <GoBookmark className="w-[30px] h-[30px] dark:text-white text-black" />
            </div>
            <div className='transition-all duration-500 w-[50px] h-[50px] rounded-2xl hover:bg-[#9a17d6] flex justify-center items-center cursor-pointer'>
            <GoQuestion className="w-[30px] h-[30px] dark:text-white text-black" />
            </div>
          </div>
        </div>
      )}

      {/* Боковая вертикальная панель - только на десктопах */}
      <div className="fixed top-0 left-0 w-[70px] h-screen bg-[#ffff] dark:bg-[#000000] flex-col items-center justify-center py-4 space-y-20 hidden md:flex z-40">
            <div className="w-[70px] h-[70x] absolute top-5">
              <img src={logo} alt="" 
              />
            </div>
            <Link to='/feed'>
              <div className='transition-all duration-500 w-[50px] h-[50px] rounded-2xl hover:bg-[#9a17d6] flex justify-center items-center cursor-pointer'>
              <GoRocket className="w-[30px] h-[30px] dark:text-white text-black" />
              </div>
            </Link>
            <Link to='/projects'>
                <div className='transition-all duration-500 w-[50px] h-[50px] rounded-2xl hover:bg-[#9a17d6] flex justify-center items-center cursor-pointer'>
                <GoPencil className="w-[30px] h-[30px] dark:text-white text-black" />
                </div>
            </Link>
            <Link to='/chats'>
              <div className='transition-all duration-500 w-[50px] h-[50px] rounded-2xl hover:bg-[#9a17d6] flex justify-center items-center cursor-pointer'>
              <GoComment className="w-[30px] h-[30px] dark:text-white text-black" />
              </div>
            </Link>
            <Link to='/friends'>
              <div className='transition-all duration-500 w-[50px] h-[50px] rounded-2xl hover:bg-[#9a17d6] flex justify-center items-center cursor-pointer'>
              <GoPeople className="w-[30px] h-[30px] dark:text-white text-black" />
              </div>
            </Link>
            <Link to='/announcements'>
              <div className='transition-all duration-500 w-[50px] h-[50px] rounded-2xl hover:bg-[#9a17d6] flex justify-center items-center cursor-pointer'>
              <GoPaste className="w-[30px] h-[30px] dark:text-white text-black" />
              </div>
            </Link>

           
             <Link to='/faq'>
            <div className='transition-all duration-500 w-[50px] h-[50px] rounded-2xl hover:bg-[#9a17d6] flex justify-center items-center cursor-pointer'>
            <GoQuestion className="w-[30px] h-[30px] dark:text-white text-black" />
            </div>
            </Link>
        </div>

      {/* Основная область */}
      <div className="flex-1 flex flex-col bg-[#ffff] dark:bg-[#000000] md:ml-[70px] ml-0 min-w-0 overflow-hidden">
        {/* Верхний горизонтальный хедер - зафиксирован наверху */}
        <div className="fixed top-0 left-0 right-0 z-20 w-full h-[70px] bg-[#ffff] dark:bg-[#000000] flex items-center justify-between px-3 sm:px-4 md:px-6 border-b border-gray-200 dark:border-gray-800 md:ml-[70px] md:w-[calc(100%-70px)]">
          {/* Левая часть - навигация */}
          <div className="flex items-center space-x-2 sm:space-x-4 dark:text-white text-black min-w-0">
            {/* Мобильная версия - бургер-меню и иконки */}
            <div className="flex md:hidden items-center space-x-4">
              {/* Бургер-кнопка */}
              <button
                onClick={() => setIsMobileMenuOpen(true)}
                className='transition-all duration-500 w-[40px] h-[40px] rounded-2xl hover:bg-[#9a17d6] flex justify-center items-center cursor-pointer'
              >
                <GoListUnordered className="w-5 h-5 md:w-[30px] md:h-[30px] dark:text-white text-black" />
              </button>
              
              {/* Иконки поиска */}
              <div className='transition-all duration-500 w-[40px] h-[40px] rounded-2xl hover:bg-[#9a17d6] flex justify-center items-center cursor-pointer'>
                <GoBook className="w-5 h-5 md:w-[30px] md:h-[30px] dark:text-white text-black" />
              </div>
              
            </div>
            
          </div>

          {/* Правая часть - поиск и иконки */}
          <div className="flex items-center space-x-2 sm:space-x-4 flex-shrink-0">

    
            <button
            onClick={toggleTheme}
            >
              {theme == 'dark' ? '🌛' :  '☀️'}
            </button>
            {/*<input 
            type="text"
            className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl 
                        dark:text-white text-black placeholder-gray-500
                        focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20
                        transition-all duration-300
                        backdrop-blur-sm
                        hidden md:block"
            placeholder="Поиск..."
            />*/}
            <div className="flex items-center space-x-1 sm:space-x-3">
              <Link to='/announcements'>
                <button className="hidden md:inline-flex px-3 py-2 text-sm font-medium rounded-lg bg-gray-800/70 hover:bg-purple-700 text-white transition-colors whitespace-nowrap">
                  Объявления
                </button>
              </Link>
              <Link to='/notifications'>
                <div className='transition-all duration-500 w-[40px] h-[40px] sm:w-[50px] sm:h-[50px] rounded-2xl hover:bg-[#9a17d6] flex justify-center items-center cursor-pointer'>
                  <GoBell className="w-5 h-5 md:w-[30px] md:h-[30px] dark:text-white text-black" />
                </div>
              </Link>
              {isAuth ? (
                <Link to='/profile' className="flex items-center space-x-2 sm:space-x-3 min-w-0">
                  {name && (
                    <div className="hidden sm:flex flex-col min-w-0 max-w-[120px] md:max-w-[180px]">
                      <span className="text-sm font-semibold dark:text-white text-black truncate">{name}</span>
                      <span className="text-xs text-gray-500 dark:text-gray-400 truncate">@{username}</span>
                    </div>
                  )}
                  <div className='transition-all duration-500 w-[40px] h-[40px] sm:w-[50px] sm:h-[50px] rounded-2xl hover:bg-[#9a17d6] flex justify-center items-center cursor-pointer overflow-hidden flex-shrink-0'>
                    {avatar ? (
                      <img 
                        src={avatar}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <img 
                        src={`https://ui-avatars.com/api/?name=${encodeURIComponent(name || username)}&background=9a17d6&color=fff&size=50`}
                        alt="Avatar" 
                        className="w-full h-full object-cover"
                      />
                    )}
                  </div>
                </Link>
              ) : (
                <div className="flex items-center space-x-2">
                  <Link to='/login'>
                    <button className="px-4 py-2 text-sm font-medium text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 transition-colors">
                      Войти
                    </button>
                  </Link>
                  <Link to='/register'>
                    <button className="px-4 py-2 text-sm font-medium bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
                      Зарегистрироваться
                    </button>
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Main контент вставляется здесь */}
        <div className="flex-1 p-3 sm:p-4 md:p-6 text-white mt-[70px] min-h-0 overflow-x-hidden overflow-y-auto">
          {children}
        </div>
      </div>
    </div>
  )
}


