import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { createProject } from '../../store/slices/projects';
import Header from '../../ui/Header';
import { FiX, FiPlus } from 'react-icons/fi';

export default function CreateProject() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { createLoading, error } = useSelector(state => state.projects);

  const categoryOptions = [
    { value: 'technology', label: 'Технологии и IT' },
    { value: 'science', label: 'Наука' },
    { value: 'mathematics', label: 'Математика' },
    { value: 'physics', label: 'Физика' },
    { value: 'chemistry', label: 'Химия' },
    { value: 'biology', label: 'Биология' },
    { value: 'medicine', label: 'Медицина' },
    { value: 'engineering', label: 'Инженерия' },
    { value: 'art', label: 'Искусство' },
    { value: 'design', label: 'Дизайн' },
    { value: 'music', label: 'Музыка' },
    { value: 'literature', label: 'Литература' },
    { value: 'linguistics', label: 'Лингвистика' },
    { value: 'history', label: 'История' },
    { value: 'philosophy', label: 'Философия' },
    { value: 'economics', label: 'Экономика' },
    { value: 'business', label: 'Бизнес' },
    { value: 'marketing', label: 'Маркетинг' },
    { value: 'education', label: 'Образование' },
    { value: 'environment', label: 'Экология' },
    { value: 'social', label: 'Социальные проекты' },
    { value: 'other', label: 'Другое' },
  ];

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    tags: [],
    create_chat: true,
    category: ''
  });

  const [newTag, setNewTag] = useState('');

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const addTag = () => {
    if (newTag.trim() && !formData.tags.includes(newTag.trim())) {
      setFormData(prev => ({
        ...prev,
        tags: [...prev.tags, newTag.trim()]
      }));
      setNewTag('');
    }
  };

  const removeTag = (tagToRemove) => {
    setFormData(prev => ({
      ...prev,
      tags: prev.tags.filter(tag => tag !== tagToRemove)
    }));
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addTag();
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const result = await dispatch(createProject(formData));
      if (result.meta.requestStatus === 'fulfilled') {
        navigate('/projects');
      }
    } catch (error) {
      console.error('Error creating project:', error);
    }
  };

  return (
    <Header>
      <div className="max-w-2xl mx-auto">
        <div className="bg-gray-900/80 rounded-2xl p-6">
          {/* Заголовок */}
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-bold text-white">Создание проекта</h1>
            <button
              onClick={() => navigate('/projects')}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors text-white"
            >
              <FiX size={20} />
            </button>
          </div>

          {error && (
            <div className="mb-4 p-4 bg-red-900/50 border border-red-700 rounded-lg text-red-200">
              {typeof error === 'string' ? error : error.detail || 'Ошибка при создании проекта'}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Название проекта */}
            <div>
              <label className="block text-gray-300 text-sm font-medium mb-2">
                Название проекта *
              </label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                required
                className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300"
                placeholder="Введите название проекта"
              />
            </div>

            {/* Категория */}
            <div>
              <label className="block text-gray-300 text-sm font-medium mb-2">
                Категория проекта *
              </label>
              <select
                name="category"
                value={formData.category}
                onChange={handleInputChange}
                required
                className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white"
              >
                <option value="" disabled>
                  Выберите категорию
                </option>
                {categoryOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Описание проекта */}
            <div>
              <label className="block text-gray-300 text-sm font-medium mb-2">
                Описание проекта *
              </label>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleInputChange}
                required
                rows={4}
                className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300 resize-none"
                placeholder="Опишите ваш проект..."
              />
            </div>

            {/* Теги */}
            <div>
              <label className="block text-gray-300 text-sm font-medium mb-2">
                Теги проекта
              </label>
              <div className="flex gap-2 mb-3">
                <input
                  type="text"
                  value={newTag}
                  onChange={(e) => setNewTag(e.target.value)}
                  onKeyPress={handleKeyPress}
                  className="flex-1 px-4 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
                  placeholder="Добавить тег..."
                />
                <button
                  type="button"
                  onClick={addTag}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors flex items-center"
                >
                  <FiPlus className="mr-2" />
                  Добавить
                </button>
              </div>
              
              {/* Список тегов */}
              <div className="flex flex-wrap gap-2">
                {formData.tags.map((tag, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-purple-900/40 text-purple-300 rounded-full text-sm font-medium border border-purple-800/50 flex items-center gap-2"
                  >
                    {tag}
                    <button
                      type="button"
                      onClick={() => removeTag(tag)}
                      className="text-purple-200 hover:text-white transition-colors"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            </div>

            {/* Настройки */}
            <div className="space-y-4">
              <label className="block text-gray-300 text-sm font-medium mb-3">
                Настройки проекта
              </label>
              
              <div className="space-y-3">
                <label className="flex items-center text-gray-300 hover:text-white cursor-pointer">
                  <input
                    type="checkbox"
                    name="create_chat"
                    checked={formData.create_chat}
                    onChange={handleInputChange}
                    className="mr-3 rounded border-gray-600 bg-gray-700 text-purple-600 focus:ring-purple-500"
                  />
                  <span>Создать чат для команды</span>
                </label>
              </div>
            </div>

            {/* Кнопки */}
            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={() => navigate('/projects')}
                className="px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
              >
                Отмена
              </button>
              <button
                type="submit"
                disabled={createLoading}
                className="flex-1 px-6 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 text-white rounded-lg transition-colors font-medium"
              >
                {createLoading ? 'Создание...' : 'Создать проект'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Header>
  );
}
