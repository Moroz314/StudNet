import React from 'react';
import { FaClock, FaUser, FaTag, FaComment, FaEllipsisH } from 'react-icons/fa';
import { MdCheckCircle, MdPriorityHigh, MdLightbulbOutline } from 'react-icons/md';

const TaskCard = ({ task, onClick, onEdit, onDelete }) => {
  const getTaskStatusColor = (status) => {
    const colors = {
      idea: 'bg-blue-900/50 text-blue-300',
      todo: 'bg-yellow-900/50 text-yellow-300',
      in_progress: 'bg-purple-900/50 text-purple-300',
      review: 'bg-orange-900/50 text-orange-300',
      done: 'bg-green-900/50 text-green-300',
      cancelled: 'bg-red-900/50 text-red-300',
    };
    return colors[status] || 'bg-gray-900/50 text-gray-300';
  };

  const getTaskTypeIcon = (type) => {
    const icons = {
      idea: <MdLightbulbOutline className="w-5 h-5 text-blue-400" />,
      task: <MdCheckCircle className="w-5 h-5 text-green-400" />,
      urgent_task: <MdPriorityHigh className="w-5 h-5 text-red-400" />,
    };
    return icons[type] || <MdCheckCircle className="w-5 h-5 text-gray-400" />;
  };

  const getTaskPriorityColor = (priority) => {
    const colors = {
      low: 'bg-gray-900/50 text-gray-300',
      medium: 'bg-yellow-900/50 text-yellow-300',
      high: 'bg-orange-900/50 text-orange-300',
      urgent: 'bg-red-900/50 text-red-300',
    };
    return colors[priority] || 'bg-gray-900/50 text-gray-300';
  };

  const isOverdue = task.is_overdue || (task.deadline && new Date(task.deadline) < new Date());
  console.log(task)
  return (
    <div 
      className="bg-gray-800/50 rounded-lg border border-gray-700 p-4 hover:border-purple-500/50 transition-all cursor-pointer group"
      onClick={onClick}
    >
      <div className="flex justify-between items-start mb-3">
        <div className="flex items-center gap-2">
          {getTaskTypeIcon(task.task_type)}
          <span className={`text-xs px-2 py-1 rounded ${getTaskStatusColor(task.status)}`}>
            {task.status.replace('_', ' ')}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-1 rounded ${getTaskPriorityColor(task.priority)}`}>
            {task.priority}
          </span>
          <button 
            className="text-gray-400 hover:text-white opacity-0 group-hover:opacity-100 transition-opacity"
            onClick={(e) => {
              e.stopPropagation();
              onEdit?.(task);
            }}
          >
            <FaEllipsisH size={14} />
          </button>
        </div>
      </div>

      <h4 className="font-semibold text-white mb-2 line-clamp-2">{task.title}</h4>
      
      {task.description && (
        <p className="text-gray-400 text-sm mb-3 line-clamp-2">{task.description}</p>
      )}

      <div className="flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center gap-3">
          {task.deadline && (
            <div className={`flex items-center gap-1 ${isOverdue ? 'text-red-400' : ''}`}>
              <FaClock size={12} />
              <span>{new Date(task.deadline).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })}</span>
            </div>
          )}
          {task.estimated_hours && (
            <div className="flex items-center gap-1">
              <FaUser size={12} />
              <span>{task.estimated_hours}ч</span>
            </div>
          )}
          {task.comments?.length > 0 && (
            <div className="flex items-center gap-1">
              <FaComment size={12} />
              <span>{task.comments.length}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TaskCard;