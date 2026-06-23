import React, { useState, useEffect } from 'react'
import Header from '../../ui/Header'
import ListsChats from './ListsChats';
import ScreenChat from './ScreenChat';
import { useChat } from '../../hooks/useChat'
import { useLocation } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import { setCurrentChat } from '../../store/slices/chatSlice'


export default function Chats() {
  const [isMobile, setIsMobile] = useState(false);
  const [showChatList, setShowChatList] = useState(true);
  const { currentChat } = useChat();
  const location = useLocation()
  const dispatch = useDispatch()

  // Определяем, мобильное ли устройство
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 1024);
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // На мобильных: при выборе чата показываем экран чата
  useEffect(() => {
    if (isMobile && currentChat) {
      setShowChatList(false);
    } else if (!isMobile) {
      setShowChatList(true);
    }
  }, [isMobile, currentChat]);

  useEffect(() => {
    const fromState = location.state?.openChat
    if (fromState?.id) {
      dispatch(setCurrentChat(fromState))
      window.history.replaceState({}, document.title)
    }
  }, [location.state, dispatch])

  // Функция для возврата к списку чатов на мобильных
  const handleBackToList = () => {
    setShowChatList(true);
  };

  return (
    <Header>
      <div className="relative page-viewport">
        {/* Десктоп: два столбца */}
        <div className="hidden lg:grid lg:grid-cols-3 gap-6 h-full">
          <div className="">
            <ListsChats initialTab={location.state?.openChat?.type === 'channel' ? 'channels' : undefined} />
          </div>
          <div className="col-span-2 flex flex-col h-full overflow-hidden min-h-0">
            <ScreenChat />
          </div>
        </div>

        {/* Мобильные: один вид за раз */}
        <div className="lg:hidden h-full overflow-hidden">
          {showChatList ? (
            <ListsChats onChatSelect={() => setShowChatList(false)} initialTab={location.state?.openChat?.type === 'channel' ? 'channels' : undefined} />
          ) : (
            <ScreenChat onBack={handleBackToList} />
          )}
        </div>
      </div>
    </Header>
  )
}
