import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { FiBriefcase, FiEdit2, FiPlus, FiSearch, FiTrash2, FiUsers } from 'react-icons/fi';
import { announcementsAPI } from '../../services/api';

export default function ProjectAnnouncementsTab({
  projectId,
  workspaces = [],
  canCreate = false,
  canManageAnnouncements = false
}) {
  const [announcements, setAnnouncements] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [editingAnnouncementId, setEditingAnnouncementId] = useState(null);
  const [deletingAnnouncementId, setDeletingAnnouncementId] = useState(null);
  const [form, setForm] = useState({
    workspaceId: '',
    title: '',
    content: '',
    questionsText: ''
  });

  const workspaceMap = useMemo(
    () => new Map(workspaces.map((ws) => [ws.id, ws])),
    [workspaces]
  );

  const loadAnnouncements = async () => {
    if (!projectId || !workspaces.length) {
      setAnnouncements([]);
      return;
    }

    setIsLoading(true);
    setError('');
    try {
      const responses = await Promise.all(
        workspaces.map((ws) =>
          announcementsAPI
            .getWorkspaceAnnouncements(projectId, ws.id, { limit: 100, status: 'active' })
            .then((res) => res.data.items || [])
            .catch(() => [])
        )
      );

      const merged = responses.flat().sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      setAnnouncements(merged);
    } catch {
      setError('Не удалось загрузить объявления');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAnnouncements();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, workspaces.length]);

  useEffect(() => {
    if (!form.workspaceId && workspaces.length) {
      setForm((prev) => ({ ...prev, workspaceId: workspaces[0].id }));
    }
  }, [workspaces, form.workspaceId]);

  const filteredAnnouncements = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return announcements;
    return announcements.filter((item) => {
      const wsName = workspaceMap.get(item.workspace_id)?.name || item.workspace_name || '';
      return (
        item.title?.toLowerCase().includes(q) ||
        item.content?.toLowerCase().includes(q) ||
        wsName.toLowerCase().includes(q)
      );
    });
  }, [announcements, search, workspaceMap]);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!form.workspaceId || !form.title.trim() || !form.content.trim()) return;

    setIsCreating(true);
    try {
      const questions = form.questionsText
        .split('\n')
        .map((q) => q.trim())
        .filter(Boolean);

      if (editingAnnouncementId) {
        await announcementsAPI.updateAnnouncement(editingAnnouncementId, {
          title: form.title.trim(),
          content: form.content.trim(),
          questions
        });
      } else {
        await announcementsAPI.createAnnouncement(projectId, form.workspaceId, {
          title: form.title.trim(),
          content: form.content.trim(),
          questions
        });
      }

      setShowCreateModal(false);
      setEditingAnnouncementId(null);
      setForm({
        workspaceId: workspaces[0]?.id || '',
        title: '',
        content: '',
        questionsText: ''
      });
      await loadAnnouncements();
    } catch {
      alert(editingAnnouncementId ? 'Не удалось обновить объявление' : 'Не удалось создать объявление');
    } finally {
      setIsCreating(false);
    }
  };

  const handleStartEdit = (item) => {
    setEditingAnnouncementId(item.id);
    setForm({
      workspaceId: item.workspace_id,
      title: item.title || '',
      content: item.content || '',
      questionsText: (item.questions || []).join('\n')
    });
    setShowCreateModal(true);
  };

  const handleDeleteAnnouncement = async (announcementId) => {
    if (!window.confirm('Удалить объявление? Оно исчезнет из активных.')) return;
    setDeletingAnnouncementId(announcementId);
    try {
      await announcementsAPI.deleteAnnouncement(announcementId);
      await loadAnnouncements();
    } catch {
      alert('Не удалось удалить объявление');
    } finally {
      setDeletingAnnouncementId(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <FiBriefcase className="text-purple-400" />
          Вакансии проекта
        </h2>
        {canCreate && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors inline-flex items-center gap-2"
          >
            <FiPlus />
            Создать объявление
          </button>
        )}
      </div>

      <div className="relative">
        <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Найти объявление по названию, описанию или workspace..."
          className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
        />
      </div>

      {isLoading ? (
        <p className="text-gray-400 py-6 text-center">Загрузка объявлений...</p>
      ) : error ? (
        <p className="text-red-400 py-6 text-center">{error}</p>
      ) : filteredAnnouncements.length === 0 ? (
        <p className="text-gray-400 py-8 text-center">Объявления не найдены</p>
      ) : (
        <div className="space-y-3">
          {filteredAnnouncements.map((item) => {
            const workspace = workspaceMap.get(item.workspace_id);
            return (
              <div
                key={item.id}
                className="p-4 border border-gray-700 rounded-xl bg-gray-900/40 hover:bg-gray-800/60 transition-colors"
              >
                <div className="flex items-start justify-between gap-4">
                  <Link to={`/projects/${projectId}/announcements/${item.id}`} className="block flex-1 min-w-0">
                    <h3 className="text-white font-semibold">{item.title}</h3>
                    <p className="text-sm text-gray-400 mt-1 line-clamp-2">{item.content}</p>
                  </Link>
                  <div className="flex items-start gap-2">
                    <span className="text-xs px-2 py-1 rounded-full border border-purple-800 text-purple-300 bg-purple-900/30 whitespace-nowrap">
                      {workspace?.name || item.workspace_name || 'Workspace'}
                    </span>
                    {canManageAnnouncements && (
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleStartEdit(item)}
                          className="px-2 py-1 rounded border border-gray-600 text-gray-300 hover:text-white hover:border-gray-500"
                          title="Изменить объявление"
                        >
                          <FiEdit2 size={14} />
                        </button>
                        <button
                          onClick={() => handleDeleteAnnouncement(item.id)}
                          disabled={deletingAnnouncementId === item.id}
                          className="px-2 py-1 rounded border border-red-800/60 text-red-300 hover:text-red-200 hover:border-red-700 disabled:opacity-50"
                          title="Удалить объявление"
                        >
                          <FiTrash2 size={14} />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
                <div className="mt-3 flex items-center gap-4 text-xs text-gray-400">
                  <span className="inline-flex items-center gap-1">
                    <FiUsers />
                    Откликов: {item.applications_count || 0}
                  </span>
                  <span>{new Date(item.created_at).toLocaleString('ru-RU')}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {showCreateModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="w-full max-w-2xl bg-gray-900 border border-gray-700 rounded-2xl p-6">
            <h3 className="text-xl font-bold text-white mb-4">
              {editingAnnouncementId ? 'Изменить объявление' : 'Новое объявление'}
            </h3>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm text-gray-300 mb-1">Workspace</label>
                <select
                  value={form.workspaceId}
                  onChange={(e) => setForm((prev) => ({ ...prev, workspaceId: e.target.value }))}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
                  required
                >
                  {workspaces.map((ws) => (
                    <option key={ws.id} value={ws.id}>
                      {ws.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-300 mb-1">Название</label>
                <input
                  value={form.title}
                  onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
                  placeholder="Frontend разработчик React"
                  required
                />
              </div>
              <div>
                <label className="block text-sm text-gray-300 mb-1">Описание</label>
                <textarea
                  value={form.content}
                  onChange={(e) => setForm((prev) => ({ ...prev, content: e.target.value }))}
                  rows={5}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white resize-none"
                  placeholder="Опишите задачи, требования и формат сотрудничества"
                  required
                />
              </div>
              <div>
                <label className="block text-sm text-gray-300 mb-1">Вопросы кандидату (по одному на строку)</label>
                <textarea
                  value={form.questionsText}
                  onChange={(e) => setForm((prev) => ({ ...prev, questionsText: e.target.value }))}
                  rows={4}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white resize-none"
                  placeholder={'Сколько лет опыта?\nКакие проекты были похожи?'}
                />
              </div>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false);
                    setEditingAnnouncementId(null);
                    setForm({
                      workspaceId: workspaces[0]?.id || '',
                      title: '',
                      content: '',
                      questionsText: ''
                    });
                  }}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg"
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  disabled={isCreating}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-60 text-white rounded-lg"
                >
                  {isCreating ? 'Сохранение...' : editingAnnouncementId ? 'Сохранить' : 'Создать'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
