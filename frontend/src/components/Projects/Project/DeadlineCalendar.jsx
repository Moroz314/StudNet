import React, { useState, useMemo, useEffect } from 'react';
import { useDispatch } from 'react-redux';
import { FaLightbulb, FaStickyNote, FaTasks } from 'react-icons/fa';
import { createTask, deleteTask, fetchTasks } from '../../../store/slices/projects';


export const DeadlineCalendar = ({ tasks = [], workspaceId, projectId }) => {
  const dispatch = useDispatch();
  const [currentDate, setCurrentDate] = useState(new Date());
  const [activeTab, setActiveTab] = useState('deadlines');
  const [newIdea, setNewIdea] = useState('');
  const [creatingIdea, setCreatingIdea] = useState(false);
  const [notes, setNotes] = useState([]);
  const [newNote, setNewNote] = useState({ title: '', content: '' });

  const monthNames = [
    'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
  ];

  const weekDays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

  // Получаем дни месяца
  const getDaysInMonth = (date) => {
    const year = date.getFullYear();
    const month = date.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startingDayOfWeek = firstDay.getDay() === 0 ? 6 : firstDay.getDay() - 1;

    const days = [];
    
    // Пустые ячейки до начала месяца
    for (let i = 0; i < startingDayOfWeek; i++) {
      days.push(null);
    }
    
    // Дни месяца
    for (let i = 1; i <= daysInMonth; i++) {
      days.push(i);
    }
    
    return days;
  };

  // Преобразуем ISO‑дату задачи в строку YYYY-MM-DD
  const getDateOnly = (iso) => {
    if (!iso) return null;
    try {
      const d = new Date(iso);
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      return `${y}-${m}-${day}`;
    } catch {
      return null;
    }
  };

  // Строим массив дедлайнов на основе задач
  const deadlines = useMemo(
    () =>
      (tasks || [])
        .filter((t) => t.deadline)
        .map((t) => ({
          id: t.id,
          title: t.title,
          deadline: t.deadline,
          priority: t.priority,
          status: t.status,
        })),
    [tasks]
  );

  // Цвет маркера в календаре в зависимости от приоритета задачи
  const getDeadlineColor = (priority) => {
    switch (priority) {
      case 'low':
        return 'bg-gray-500';
      case 'medium':
        return 'bg-blue-500';
      case 'high':
        return 'bg-yellow-500';
      case 'urgent':
        return 'bg-red-500';
      default:
        return 'bg-purple-500';
    }
  };

  // Получаем дедлайны для конкретного дня
  const getDeadlinesForDay = (day) => {
    const dateStr = `${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    return deadlines.filter((deadline) => getDateOnly(deadline.deadline) === dateStr);
  };

  // Проверяем, является ли день сегодняшним
  const isToday = (day) => {
    const today = new Date();
    return (
      day === today.getDate() &&
      currentDate.getMonth() === today.getMonth() &&
      currentDate.getFullYear() === today.getFullYear()
    );
  };

  // Проверяем, просрочен ли дедлайн
  const isOverdue = (iso) => {
    if (!iso) return false;
    return new Date(iso) < new Date().setHours(0, 0, 0, 0);
  };

  const days = getDaysInMonth(currentDate);
  const currentMonth = monthNames[currentDate.getMonth()];
  const currentYear = currentDate.getFullYear();

  const navigateMonth = (direction) => {
    setCurrentDate(prev => {
      const newDate = new Date(prev);
      if (direction === 'prev') {
        newDate.setMonth(prev.getMonth() - 1);
      } else {
        newDate.setMonth(prev.getMonth() + 1);
      }
      return newDate;
    });
  };


  const ideas = useMemo(() => {
    return (tasks || []).filter(task => task.task_type === 'idea');
  }, [tasks]);

  // Функции для работы с идеями через API
  const addIdea = async () => {
    if (!newIdea.trim() || !projectId || !workspaceId || creatingIdea) return;

    try {
      setCreatingIdea(true);
      const payload = {
        title: newIdea.trim(),
        description: null,
        task_type: 'idea',
        priority: 'medium',
        status: 'idea',
        deadline: null,
        estimated_hours: null,
      };

      await dispatch(
        createTask({
          projectId,
          workspaceId,
          taskData: payload,
        })
      ).unwrap();

      // Перезагружаем задачи для обновления списка идей
      await dispatch(fetchTasks({ projectId, workspaceId, params: {} }));
      setNewIdea('');
    } catch (error) {
      console.error('Ошибка создания идеи:', error);
      alert('Не удалось создать идею. Попробуйте снова.');
    } finally {
      setCreatingIdea(false);
    }
  };

  const deleteIdea = async (taskId) => {
    if (!projectId || !workspaceId || !taskId) return;
    if (!window.confirm('Удалить идею?')) return;

    try {
      await dispatch(deleteTask({ projectId, workspaceId, taskId })).unwrap();
      // Перезагружаем задачи для обновления списка идей
      await dispatch(fetchTasks({ projectId, workspaceId, params: {} }));
    } catch (error) {
      console.error('Ошибка удаления идеи:', error);
      alert('Не удалось удалить идею. Попробуйте снова.');
    }
  };

  // Функции для работы с заметками
  const addNote = () => {
    if (newNote.title.trim() && newNote.content.trim()) {
      const note = {
        id: Date.now(),
        title: newNote.title.trim(),
        content: newNote.content.trim(),
        createdAt: new Date().toISOString().split('T')[0]
      };
      setNotes(prev => [note, ...prev]);
      setNewNote({ title: '', content: '' });
    }
  };

  const deleteNote = (id) => {
    setNotes(prev => prev.filter(note => note.id !== id));
  };

  // Вкладки (календарь + небольшие заметки/идеи для пространства)
  const tabs = [
    { id: 'deadlines', name: 'Календарь дедлайнов', icon: FaTasks },
    { id: 'ideas', name: 'Идеи проекта', icon: FaLightbulb },
  ];

  return (
    <div className="bg-gray-900/80 rounded-2xl p-6 border border-gray-800">
      <div className="mb-6">
        <h3 className="text-xl font-bold text-white mb-4">Планирование и дедлайны</h3>
        
        {/* Вкладки */}
        <div className="flex gap-2 border-b border-gray-700">
          {tabs.map(tab => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 rounded-t-lg transition-all duration-200 ${
                  activeTab === tab.id
                    ? 'bg-gray-800 text-purple-400 border-b-2 border-purple-500'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
                }`}
              >
                <Icon size={16} />
                <span className="font-medium">{tab.name}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Контент вкладок */}
      <div className="min-h-[400px]">
        {/* Доска задач */}
        {activeTab === 'deadlines' && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <h4 className="text-lg font-semibold text-white">Дедлайны задач</h4>
              <div className="flex items-center gap-4">
                <button 
                  onClick={() => navigateMonth('prev')}
                  className="p-2 hover:bg-gray-800 rounded-lg transition-colors text-white"
                >
                  ←
                </button>
                <span className="text-white font-semibold">
                  {currentMonth} {currentYear}
                </span>
                <button 
                  onClick={() => navigateMonth('next')}
                  className="p-2 hover:bg-gray-800 rounded-lg transition-colors text-white"
                >
                  →
                </button>
              </div>
            </div>

            {/* Дни недели */}
            <div className="grid grid-cols-7 gap-2 mb-2">
              {weekDays.map(day => (
                <div key={day} className="text-center text-sm font-medium text-gray-400 py-2">
                  {day}
                </div>
              ))}
            </div>

            {/* Дни календаря */}
            <div className="grid grid-cols-7 gap-2">
              {days.map((day, index) => {
                if (day === null) {
                  return <div key={`empty-${index}`} className="aspect-square" />;
                }

                const dayDeadlines = getDeadlinesForDay(day);
                const today = isToday(day);

                return (
                  <div 
                    key={day} 
                    className={`aspect-square bg-gray-800/50 rounded-lg p-2 relative hover:bg-gray-700/50 transition-colors cursor-pointer ${
                      today ? 'ring-2 ring-purple-500' : ''
                    }`}
                  >
                    <span className={`text-sm font-medium ${
                      today ? 'text-purple-400' : 'text-white'
                    }`}>
                      {day}
                    </span>
                    
                    {/* Индикаторы дедлайнов (реальные задачи) */}
                    <div className="absolute bottom-1 left-1 right-1 flex gap-1 flex-wrap">
                      {dayDeadlines.slice(0, 3).map((deadline) => (
                        <div
                          key={deadline.id}
                          className={`w-2 h-2 rounded-full ${getDeadlineColor(
                            deadline.priority
                          )} ${
                            isOverdue(deadline.deadline) ? 'animate-pulse' : ''
                          }`}
                          title={deadline.title}
                        />
                      ))}
                      {dayDeadlines.length > 3 && (
                        <span className="text-xs text-gray-400">+{dayDeadlines.length - 3}</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Ближайшие дедлайны */}
            <div className="mt-6 pt-4 border-t border-gray-700">
              <h4 className="text-sm font-semibold text-gray-300 mb-3">Ближайшие дедлайны задач:</h4>
              <div className="space-y-2 max-h-32 overflow-y-auto">
                {deadlines
                  .filter((d) => d.deadline && !isOverdue(d.deadline))
                  .sort((a, b) => new Date(a.deadline) - new Date(b.deadline))
                  .slice(0, 5)
                  .map((deadline) => (
                    <div key={deadline.id} className="flex items-center gap-2 text-sm">
                      <div className={`w-3 h-3 rounded-full ${getDeadlineColor(deadline.priority)}`} />
                      <span className="text-gray-300 flex-1 truncate">
                        {deadline.title}
                      </span>
                      <span className="text-gray-500 ml-auto text-xs">
                        {new Date(deadline.deadline).toLocaleDateString('ru-RU')}
                      </span>
                    </div>
                  ))}
                {deadlines.length === 0 && (
                  <p className="text-xs text-gray-500">
                    Дедлайны задач ещё не добавлены. Создайте задачу с датой в доске задач.
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Идеи проекта */}
        {activeTab === 'ideas' && (
          <div>
            <h4 className="text-lg font-semibold text-white mb-4">Идеи для проекта</h4>
            
            {/* Форма добавления идеи */}
            <div className="mb-6">
              {!workspaceId ? (
                <div className="bg-yellow-900/20 border border-yellow-700/50 rounded-lg p-4 text-yellow-400 text-sm">
                  Для создания идей необходимо рабочее пространство
                </div>
              ) : (
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newIdea}
                    onChange={(e) => setNewIdea(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && !creatingIdea && addIdea()}
                    placeholder="Введите новую идею..."
                    disabled={creatingIdea}
                    className="flex-1 px-4 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                  <button
                    onClick={addIdea}
                    disabled={creatingIdea || !newIdea.trim()}
                    className="px-6 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
                  >
                    {creatingIdea ? 'Создание...' : 'Добавить'}
                  </button>
                </div>
              )}
            </div>

            {/* Список идей */}
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {ideas.map(idea => (
                <div key={idea.id} className="bg-gray-800/50 rounded-lg p-4 border border-gray-700 hover:border-gray-600 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="text-gray-200 mb-2">{idea.title}</p>
                      {idea.description && (
                        <p className="text-gray-400 text-sm mb-2">{idea.description}</p>
                      )}
                      <span className="text-xs text-gray-500">
                        {idea.created_at ? new Date(idea.created_at).toLocaleDateString('ru-RU') : 'Дата не указана'}
                      </span>
                    </div>
                    {workspaceId && (
                      <button
                        onClick={() => deleteIdea(idea.id)}
                        className="text-red-400 hover:text-red-300 ml-4"
                        title="Удалить идею"
                      >
                        ×
                      </button>
                    )}
                  </div>
                </div>
              ))}
              {ideas.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <FaLightbulb size={48} className="mx-auto mb-4 opacity-50" />
                  <p>Пока нет идей. Добавьте первую!</p>
                </div>
              )}
            </div>
          </div>
        )}



    
      </div>
    </div>
  );
};