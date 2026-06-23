import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate, useParams } from 'react-router-dom';
import { createWorkspace } from '../../store/slices/projects';
import Header from '../../ui/Header';
import { FiX } from 'react-icons/fi';

export default function CreateWorkspace() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { projectId } = useParams();
  const { workspaceLoading, error } = useSelector(state => state.projects);

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    create_chat: true
  });

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const result = await dispatch(createWorkspace({ projectId, workspaceData: formData }));
      if (result.meta.requestStatus === 'fulfilled') {
        navigate(`/projects/${projectId}`);
      }
    } catch (error) {
      console.error('Error creating workspace:', error);
    }
  };

  return (
    <Header>
      <div className="max-w-2xl mx-auto">
        <div className="bg-gray-900/80 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-bold text-white">Создание рабочего пространства</h1>
            <button
              onClick={() => navigate(`/projects/${projectId}`)}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors text-white"
            >
              <FiX size={20} />
            </button>
          </div>

          {error && (
            <div className="mb-4 p-4 bg-red-900/50 border border-red-700 rounded-lg text-red-200">
              {typeof error === 'string' ? error : error.detail || 'Ошибка при создании рабочего пространства'}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-gray-300 text-sm font-medium mb-2">
                Название рабочего пространства *
              </label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                required
                className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300"
                placeholder="Введите название рабочего пространства"
              />
            </div>

            <div>
              <label className="block text-gray-300 text-sm font-medium mb-2">
                Описание рабочего пространства
              </label>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleInputChange}
                rows={4}
                className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300 resize-none"
                placeholder="Опишите рабочее пространство..."
              />
            </div>

            <div className="space-y-4">
              <label className="block text-gray-300 text-sm font-medium mb-3">
                Настройки рабочего пространства
              </label>
              <label className="flex items-center text-gray-300 hover:text-white cursor-pointer">
                <input
                  type="checkbox"
                  name="create_chat"
                  checked={formData.create_chat}
                  onChange={handleInputChange}
                  className="mr-3 rounded border-gray-600 bg-gray-700 text-purple-600 focus:ring-purple-500"
                />
                <span>Создать чат для общения</span>
              </label>
            </div>

            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={() => navigate(`/projects/${projectId}`)}
                className="px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
              >
                Отмена
              </button>
              <button
                type="submit"
                disabled={workspaceLoading}
                className="flex-1 px-6 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 text-white rounded-lg transition-colors font-medium"
              >
                {workspaceLoading ? 'Создание...' : 'Создать рабочее пространство'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Header>
  );
}
