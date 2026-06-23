import React from 'react'
import { useSelector } from 'react-redux'

const TypingIndicator = ({ chatId }) => {
  const typingUsers = useSelector(state => 
    state.chat.typingUsers?.[chatId] || []
  )

  if (typingUsers.length === 0) return null

  return (
    <div className="flex justify-start mb-4">
      <div className="bg-gray-800 rounded-2xl p-4 rounded-tl-none max-w-[70%]">
        <div className="flex items-center gap-2">
          <div className="flex space-x-1">
            <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce"></div>
            <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
            <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
          </div>
          <span className="text-gray-400 text-sm">
            {typingUsers.length === 1 
              ? 'Печатает...' 
              : `${typingUsers.length} пользователя печатают...`}
          </span>
        </div>
      </div>
    </div>
  )
}

export default TypingIndicator