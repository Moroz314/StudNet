export const Message = ({ user, text, time, isCurrentUser = false }) => {
  return (
    <div className={`flex ${isCurrentUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-xs lg:max-w-md rounded-2xl p-4 ${
        isCurrentUser 
          ? 'bg-purple-600/20 border border-purple-500/30 rounded-br-none' 
          : 'bg-gray-800/50 border border-gray-700 rounded-bl-none'
      }`}>
        
        {/* Header сообщения */}
        {!isCurrentUser && (
          <div className="flex items-center gap-2 mb-1">
            <div className="w-6 h-6 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center text-xs text-white font-bold">
              {user.charAt(0)}
            </div>
            <span className="text-purple-400 font-medium text-sm">{user}</span>
          </div>
        )}
        
        {/* Текст сообщения */}
        <p className={`text-sm ${
          isCurrentUser ? 'text-white' : 'text-gray-200'
        }`}>
          {text}
        </p>
        
        {/* Время */}
        <p className={`text-xs mt-2 ${
          isCurrentUser ? 'text-purple-300' : 'text-gray-500'
        }`}>
          {time}
        </p>
      </div>
    </div>
  );
};