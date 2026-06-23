import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useSelector } from 'react-redux';
import { FiArrowLeft, FiCheck, FiPaperclip, FiThumbsDown, FiThumbsUp, FiUserPlus, FiX } from 'react-icons/fi';
import Header from '../../ui/Header';
import { announcementsAPI, filesAPI, projectsAPI } from '../../services/api';

export default function AnnouncementDetail() {
  const { announcementId, projectId } = useParams();
  const navigate = useNavigate();
  const isGlobalView = !projectId;
  const { profile } = useSelector((state) => state.profile);
  const currentUserId = profile?.user_id;

  const [announcement, setAnnouncement] = useState(null);
  const [applications, setApplications] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadingApps, setLoadingApps] = useState(true);
  const [error, setError] = useState('');
  const [applyForm, setApplyForm] = useState({ content: '', linksText: '' });
  const [attachedFiles, setAttachedFiles] = useState([]);
  const [isUploadingFiles, setIsUploadingFiles] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusUpdatingId, setStatusUpdatingId] = useState(null);
  const [deletingApplicationId, setDeletingApplicationId] = useState(null);
  const [sendingInviteId, setSendingInviteId] = useState(null);
  const [projectRole, setProjectRole] = useState(null);
  const [canManageAnnouncement, setCanManageAnnouncement] = useState(false);

  const canUpdateStatuses = Boolean(projectId) && (projectRole === 'owner' || projectRole === 'admin');

  const sortedApplications = useMemo(() => {
    const list = [...applications];
    return list.sort((a, b) => {
      const scoreA = (a.likes_count || 0) - (a.dislikes_count || 0);
      const scoreB = (b.likes_count || 0) - (b.dislikes_count || 0);
      if (scoreA !== scoreB) return scoreB - scoreA;
      if ((a.likes_count || 0) !== (b.likes_count || 0)) return (b.likes_count || 0) - (a.likes_count || 0);
      return new Date(a.created_at) - new Date(b.created_at);
    });
  }, [applications]);

  const getStatusLabel = (status) => {
    switch (status) {
      case 'pending':
        return 'На рассмотрении';
      case 'approved':
        return 'Одобрено';
      case 'rejected':
        return 'Отклонено';
      case 'withdrawn':
        return 'Отозвана';
      default:
        return status;
    }
  };

  const loadAnnouncement = async () => {
    try {
      const { data } = await announcementsAPI.getAnnouncement(announcementId);
      setAnnouncement(data);
      setError('');
      return data;
    } catch {
      setError('Объявление не найдено или недоступно');
      return null;
    }
  };

  const loadApplications = async () => {
    setLoadingApps(true);
    try {
      const { data } = await announcementsAPI.getAnnouncementApplications(announcementId, { limit: 100, status: 'pending' });
      setApplications(data.items || []);
    } catch {
      setApplications([]);
    } finally {
      setLoadingApps(false);
    }
  };

  const loadProjectPermissions = async (loadedAnnouncement) => {
    if (!projectId || !currentUserId || !loadedAnnouncement?.project_id) {
      setProjectRole(null);
      setCanManageAnnouncement(false);
      return;
    }
    try {
      const { data } = await projectsAPI.getProjectParticipants(loadedAnnouncement.project_id);
      const participants = data?.participants || data || [];
      const me = Array.isArray(participants) ? participants.find((p) => p.user_id === currentUserId) : null;
      const role = me?.status || null;
      setProjectRole(role);
      setCanManageAnnouncement(loadedAnnouncement.created_by === currentUserId || role === 'owner' || role === 'admin');
    } catch {
      setProjectRole(null);
      setCanManageAnnouncement(loadedAnnouncement.created_by === currentUserId);
    }
  };

  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      const data = await loadAnnouncement();
      if (data) {
        await loadProjectPermissions(data);
        await loadApplications();
      }
      setIsLoading(false);
    };
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [announcementId, currentUserId]);

  const handleAttachFiles = async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setIsUploadingFiles(true);
    try {
      const uploaded = [];
      for (const file of files) {
        const { data } = await filesAPI.uploadFile(file, 'application_file');
        uploaded.push({
          id: data.file_id,
          name: data.original_filename || file.name,
        });
      }
      setAttachedFiles((prev) => [...prev, ...uploaded]);
    } catch (err) {
      alert(err?.response?.data?.detail || err?.message || 'Не удалось загрузить файл');
    } finally {
      setIsUploadingFiles(false);
      e.target.value = '';
    }
  };

  const removeAttachedFile = (fileId) => {
    setAttachedFiles((prev) => prev.filter((file) => file.id !== fileId));
  };

  const handleApply = async (e) => {
    e.preventDefault();
    if (!applyForm.content.trim()) return;
    setIsSubmitting(true);
    try {
      const links = applyForm.linksText
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);
      const fileIds = attachedFiles.map((file) => file.id);
      await announcementsAPI.createApplication(announcementId, {
        content: applyForm.content.trim(),
        links,
        ...(fileIds.length ? { file_ids: fileIds } : {}),
      });
      setApplyForm({ content: '', linksText: '' });
      setAttachedFiles([]);
      await Promise.all([loadAnnouncement(), loadApplications()]);
    } catch (err) {
      alert(err?.response?.data?.detail || 'Не удалось отправить отклик');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVote = async (applicationId, voteType) => {
    try {
      const { data } = await announcementsAPI.voteApplication(applicationId, voteType);
      setApplications((prev) =>
        prev.map((item) =>
          item.id === applicationId
            ? {
                ...item,
                likes_count: data?.likes_count ?? item.likes_count,
                dislikes_count: data?.dislikes_count ?? item.dislikes_count,
                user_vote: data?.user_vote ?? null
              }
            : item
        )
      );
    } catch (err) {
      alert(err?.response?.data?.detail || 'Ошибка голосования');
    }
  };

  const handleStatusUpdate = async (applicationId, status) => {
    setStatusUpdatingId(applicationId);
    try {
      await announcementsAPI.updateApplicationStatus(applicationId, status);
      setApplications((prev) => prev.filter((item) => item.id !== applicationId));
    } catch (err) {
      alert(err?.response?.data?.detail || 'Не удалось обновить статус');
    } finally {
      setStatusUpdatingId(null);
    }
  };

  const handleApprove = async (app) => {
    setStatusUpdatingId(app.id);
    try {
      await announcementsAPI.updateApplicationStatus(app.id, 'approved');
      setSendingInviteId(app.id);
      await projectsAPI.createProjectInvitations(projectId, { user_ids: [app.user_id] });
      setApplications((prev) => prev.filter((item) => item.id !== app.id));
    } catch (err) {
      alert(err?.response?.data?.detail || 'Не удалось принять заявку');
    } finally {
      setSendingInviteId(null);
      setStatusUpdatingId(null);
    }
  };

  const handleReject = async (app) => {
    setStatusUpdatingId(app.id);
    try {
      await announcementsAPI.updateApplicationStatus(app.id, 'rejected');
      setApplications((prev) => prev.filter((item) => item.id !== app.id));
      alert('Кандидату отправлено уведомление об отклонении заявки');
    } catch (err) {
      alert(err?.response?.data?.detail || 'Не удалось отклонить заявку');
    } finally {
      setStatusUpdatingId(null);
    }
  };

  const handleDeleteApplication = async (app) => {
    if (!window.confirm('Удалить заявку из списка откликов?')) return;
    setDeletingApplicationId(app.id);
    try {
      await announcementsAPI.deleteApplication(app.id);
      setApplications((prev) => prev.filter((item) => item.id !== app.id));
    } catch (err) {
      alert(err?.response?.data?.detail || 'Не удалось удалить заявку');
    } finally {
      setDeletingApplicationId(null);
    }
  };

  const handleDeleteAnnouncement = async () => {
    if (!window.confirm('Удалить объявление?')) return;
    try {
      await announcementsAPI.deleteAnnouncement(announcementId);
      navigate(`/projects/${announcement.project_id}`);
    } catch (err) {
      alert(err?.response?.data?.detail || 'Не удалось удалить объявление');
    }
  };

  const backTo = projectId ? `/projects/${projectId}` : '/announcements';

  if (isLoading) {
    return (
      <Header>
        <div className="max-w-5xl mx-auto text-center py-10 text-gray-400">Загрузка объявления...</div>
      </Header>
    );
  }

  if (error || !announcement) {
    return (
      <Header>
        <div className="max-w-5xl mx-auto text-center py-10">
          <p className="text-red-400">{error || 'Объявление не найдено'}</p>
          <button
            onClick={() => navigate(backTo)}
            className="mt-4 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg"
          >
            Назад
          </button>
        </div>
      </Header>
    );
  }

  return (
    <Header>
      <div className="max-w-5xl mx-auto space-y-6">
        <button
          onClick={() => navigate(backTo)}
          className="inline-flex items-center gap-2 text-gray-300 hover:text-white"
        >
          <FiArrowLeft />
          Назад
        </button>

        <div className="bg-gray-800/50 border border-gray-700 rounded-2xl p-6">
          {canManageAnnouncement && (
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <button
                onClick={() => navigate(`/projects/${announcement.project_id}`)}
                className="px-3 py-1.5 bg-gray-800 border border-gray-600 hover:border-gray-500 text-white rounded-lg text-sm"
              >
                Изменить
              </button>
              <button
                onClick={handleDeleteAnnouncement}
                className="px-3 py-1.5 bg-red-900/30 border border-red-800 hover:border-red-700 text-red-300 rounded-lg text-sm"
              >
                Удалить объявление
              </button>
            </div>
          )}
          <div className="flex flex-wrap gap-2 mb-3">
            <span className="text-xs px-2 py-1 rounded-full border border-purple-800 text-purple-300 bg-purple-900/30">
              {announcement.project_name || `Проект ${String(announcement.project_id).slice(0, 8)}`}
            </span>
            <span className="text-xs px-2 py-1 rounded-full border border-gray-700 text-gray-300 bg-gray-900/40">
              {announcement.workspace_name || `Workspace ${String(announcement.workspace_id).slice(0, 8)}`}
            </span>
          </div>
          <h1 className="text-2xl font-bold text-white">{announcement.title}</h1>
          <p className="text-gray-300 mt-3 whitespace-pre-wrap">{announcement.content}</p>

          {!!announcement.questions?.length && (
            <div className="mt-5">
              <h2 className="text-lg font-semibold text-white mb-2">Вопросы к кандидату</h2>
              <ul className="space-y-2">
                {announcement.questions.map((q, i) => (
                  <li key={i} className="text-gray-300 bg-gray-900/40 border border-gray-700 rounded-lg p-3">
                    {q}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {!announcement.has_user_application && !canUpdateStatuses && (
            <form onSubmit={handleApply} className="mt-6 border-t border-gray-700 pt-5 space-y-3">
              <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                <FiUserPlus className="text-purple-400" />
                Откликнуться
              </h3>
              <textarea
                value={applyForm.content}
                onChange={(e) => setApplyForm((prev) => ({ ...prev, content: e.target.value }))}
                rows={5}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white resize-none"
                placeholder="Расскажите о себе, опыте и почему хотите в команду"
                required
              />
              <textarea
                value={applyForm.linksText}
                onChange={(e) => setApplyForm((prev) => ({ ...prev, linksText: e.target.value }))}
                rows={3}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white resize-none"
                placeholder={'Ссылки на портфолио / GitHub (каждая ссылка с новой строки)'}
              />
              <div>
                <label className="block text-sm text-gray-300 mb-2 flex items-center gap-2">
                  <FiPaperclip className="text-purple-400" />
                  Прикрепить файлы (портфолио, резюме и т.д., до 15 МБ каждый)
                </label>
                <input
                  type="file"
                  multiple
                  onChange={handleAttachFiles}
                  disabled={isUploadingFiles || isSubmitting}
                  className="block w-full text-sm text-gray-300 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:bg-purple-700 file:text-white hover:file:bg-purple-600"
                />
                {isUploadingFiles && <p className="text-xs text-purple-300 mt-1">Загрузка файлов...</p>}
                {attachedFiles.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {attachedFiles.map((file) => (
                      <li
                        key={file.id}
                        className="flex items-center justify-between gap-2 px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-gray-200"
                      >
                        <span className="truncate">{file.name}</span>
                        <button
                          type="button"
                          onClick={() => removeAttachedFile(file.id)}
                          className="text-gray-400 hover:text-red-300 shrink-0"
                          aria-label="Удалить файл"
                        >
                          <FiX />
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <button
                type="submit"
                disabled={isSubmitting || isUploadingFiles}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-60 text-white rounded-lg"
              >
                {isSubmitting ? 'Отправка...' : 'Отправить отклик'}
              </button>
            </form>
          )}

          {!canUpdateStatuses && announcement.has_user_application && (
            <div className="mt-6 border-t border-gray-700 pt-5 text-green-300 inline-flex items-center gap-2">
              <FiCheck />
              Вы уже отправили отклик на это объявление
            </div>
          )}
        </div>

        {!isGlobalView && (
          <div className="bg-gray-800/50 border border-gray-700 rounded-2xl p-6">
            <h2 className="text-xl font-bold text-white mb-4">Отклики и голосование</h2>
            {loadingApps ? (
              <p className="text-gray-400">Загрузка откликов...</p>
            ) : sortedApplications.length === 0 ? (
              <p className="text-gray-400">Пока нет откликов</p>
            ) : (
              <div className="space-y-4">
                {sortedApplications.map((app) => (
                  <div key={app.id} className="border border-gray-700 rounded-xl p-4 bg-gray-900/40">
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                      <div>
                        <p className="text-white font-medium">
                          {app.user?.name} {app.user?.lastname}
                          {app.user?.username ? ` (@${app.user.username})` : ''}
                        </p>
                        <p className="text-xs text-gray-400">
                          Статус: <span className="text-gray-300">{getStatusLabel(app.status)}</span>
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleVote(app.id, app.user_vote === 'like' ? 'remove' : 'like')}
                          className={`px-3 py-1.5 rounded-lg text-sm inline-flex items-center gap-1 ${
                            app.user_vote === 'like'
                              ? 'bg-green-700/40 text-green-200 border border-green-600 shadow-[0_0_0_1px_rgba(34,197,94,.2)]'
                              : 'bg-gray-800 text-gray-200 border border-gray-700 hover:border-green-700/70'
                          }`}
                        >
                          <FiThumbsUp /> {app.likes_count}
                        </button>
                        <button
                          onClick={() => handleVote(app.id, app.user_vote === 'dislike' ? 'remove' : 'dislike')}
                          className={`px-3 py-1.5 rounded-lg text-sm inline-flex items-center gap-1 ${
                            app.user_vote === 'dislike'
                              ? 'bg-red-700/40 text-red-200 border border-red-600 shadow-[0_0_0_1px_rgba(248,113,113,.2)]'
                              : 'bg-gray-800 text-gray-200 border border-gray-700 hover:border-red-700/70'
                          }`}
                        >
                          <FiThumbsDown /> {app.dislikes_count}
                        </button>
                      </div>
                    </div>
                    <p className="text-gray-300 mt-3 whitespace-pre-wrap">{app.content}</p>
                    {!!app.links?.length && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {app.links.map((link, i) => (
                          <a
                            key={`${app.id}-${i}`}
                            href={link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm px-2 py-1 rounded bg-gray-800 border border-gray-700 text-purple-300 hover:text-purple-200"
                          >
                            {link}
                          </a>
                        ))}
                      </div>
                    )}
                    {Array.isArray(app.files) && app.files.length > 0 && (
                      <div className="mt-3">
                        <p className="text-xs text-gray-400 mb-1">Вложения:</p>
                        <div className="flex flex-wrap gap-2">
                          {app.files.map((file) => (
                            <a
                              key={file.id}
                              href={file.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-sm px-2 py-1 rounded bg-gray-800 border border-gray-700 text-gray-200 hover:text-white inline-flex items-center gap-1"
                            >
                              <FiPaperclip size={12} />
                              {file.original_filename || 'Файл'}
                            </a>
                          ))}
                        </div>
                      </div>
                    )}
                    {canUpdateStatuses && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        <button
                          disabled={statusUpdatingId === app.id || sendingInviteId === app.id}
                          onClick={() => handleApprove(app)}
                          className="px-3 py-1.5 text-xs rounded bg-green-900/30 border border-green-700 text-green-300 hover:text-green-200 disabled:opacity-50 inline-flex items-center gap-1"
                        >
                          <FiCheck size={14} />
                          {sendingInviteId === app.id ? 'Отправка заявки...' : 'Принять'}
                        </button>
                        <button
                          disabled={statusUpdatingId === app.id}
                          onClick={() => handleReject(app)}
                          className="px-3 py-1.5 text-xs rounded bg-red-900/30 border border-red-700 text-red-300 hover:text-red-200 disabled:opacity-50 inline-flex items-center gap-1"
                        >
                          <FiX size={14} />
                          Отклонить
                        </button>
                        <button
                          disabled={deletingApplicationId === app.id}
                          onClick={() => handleDeleteApplication(app)}
                          className="px-3 py-1.5 text-xs rounded bg-gray-800 border border-gray-700 text-gray-300 hover:text-white disabled:opacity-50"
                        >
                          {deletingApplicationId === app.id ? 'Удаление...' : 'Удалить из списка'}
                        </button>
                        <button
                          disabled={statusUpdatingId === app.id}
                          onClick={() => handleStatusUpdate(app.id, 'withdrawn')}
                          className="px-3 py-1.5 text-xs rounded bg-gray-800 border border-gray-700 text-gray-300 hover:text-white disabled:opacity-50"
                        >
                          Снять
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </Header>
  );
}