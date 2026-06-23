import { useNavigate } from "react-router-dom";
import { useDispatch } from "react-redux";
import { setCurrentChat } from "../../../store/slices/chatSlice";
import { FiMessageSquare, FiHash } from "react-icons/fi";

export const ProjectChat = ({ workspace, project }) => {
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const handleOpenChat = (chat) => {
    if (!chat?.id) return;
    dispatch(setCurrentChat({ ...chat, type: chat.type || 'channel' }));
    navigate("/chats");
  };

  const chat = workspace?.chat;
  const channel = project?.channel || project?.project_channel;

  if (!chat && !channel) {
    return (
      <div className="bg-gray-900/85 rounded-2xl p-6 border border-gray-800">
        <h3 className="text-xl font-bold text-white mb-4">Чат и канал</h3>
        <p className="text-gray-500 text-sm">Чат и канал проекта пока не созданы.</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-900/85 rounded-2xl p-6 border border-gray-800">
      <h3 className="text-xl font-bold text-white mb-4">Чат и канал</h3>
      <div className="space-y-3">
        {chat && (
          <button
            onClick={() => handleOpenChat(chat)}
            className="w-full flex items-center gap-3 p-4 rounded-xl bg-gray-800/70 hover:bg-gray-800 border border-gray-700 hover:border-purple-500/50 transition-all text-left group"
          >
            <div className="w-10 h-10 rounded-lg bg-purple-600/30 flex items-center justify-center">
              <FiMessageSquare className="text-purple-400 text-xl" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-white font-medium truncate">{chat.name || "Чат пространства"}</p>
              <p className="text-gray-400 text-sm">Чат рабочего пространства</p>
            </div>
            <span className="text-gray-500 group-hover:text-purple-400 text-sm">Открыть →</span>
          </button>
        )}
        {channel && (
          <button
            onClick={() => handleOpenChat(channel)}
            className="w-full flex items-center gap-3 p-4 rounded-xl bg-gray-800/70 hover:bg-gray-800 border border-gray-700 hover:border-purple-500/50 transition-all text-left group"
          >
            <div className="w-10 h-10 rounded-lg bg-purple-600/30 flex items-center justify-center">
              <FiHash className="text-purple-400 text-xl" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-white font-medium truncate">{channel.name || "Канал проекта"}</p>
              <p className="text-gray-400 text-sm">Канал проекта</p>
            </div>
            <span className="text-gray-500 group-hover:text-purple-400 text-sm">Открыть →</span>
          </button>
        )}
      </div>
    </div>
  );
};
