import React, { useState, useMemo, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { FaTasks, FaCode, FaGithub, FaPaperclip, FaTrash, FaPlus, FaExternalLinkAlt, FaCheck, FaFolder, FaFile, FaArrowLeft, FaSpinner } from 'react-icons/fa';
import TaskCard from './TaskCard';
import {
  createTask,
  updateTask,
  deleteTask,
  fetchTasks,
  fetchTask,
  fetchTaskComments,
  addTaskComment,
  deleteTaskComment,
  clearTaskComments,
  uploadProjectFile,
  updateWorkspace,
  fetchProject,
} from '../../../store/slices/projects';
import { githubAPI, formatApiError } from '../../../services/api';

export const KanbanBoard = ({ tasks = [], workspaceId, projectId, workspace }) => {
  const dispatch = useDispatch();
  const { currentTask, taskComments, taskCommentsLoading } = useSelector((state) => state.projects);
  const { profile } = useSelector((state) => state.profile);
  const [activeTab, setActiveTab] = useState('kanban');

  // Локальное состояние для создания/редактирования задач
  const [isCreating, setIsCreating] = useState(false);
  const [formData, setFormData] = useState({
    id: null,
    title: '',
    description: '',
    task_type: 'task', // Идеи создаются только в DeadlineCalendar
    priority: 'medium',
    status: 'todo', // Идеи создаются только в DeadlineCalendar
    deadline: '',
    estimated_hours: '',
  });

  // Модалка просмотра задачи
  const [isViewModalOpen, setIsViewModalOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);

  // Комментарии к задаче
  const [commentText, setCommentText] = useState('');
  const [sendingComment, setSendingComment] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState([]);
  const [commentUploadLoading, setCommentUploadLoading] = useState(false);

  // Репозитории GitHub (из workspace.github_links)
  const normalizeGithubLink = (item, idx) => {
    if (typeof item === 'string') {
      const parts = item.replace(/\/$/, '').split('/');
      const name = parts[parts.length - 1] || 'repo';
      const owner = parts[parts.length - 2] || '';
      return { id: `gh-${idx}`, url: item, name, owner, addedAt: new Date().toISOString() };
    }
    const link = item?.link ?? item?.url ?? '';
    const parts = link.replace(/\/$/, '').split('/');
    const name = item?.name ?? parts[parts.length - 1] ?? 'repo';
    const owner = parts[parts.length - 2] ?? '';
    return { id: `gh-${idx}`, url: link, name, owner, addedAt: new Date().toISOString() };
  };
  const repositories = useMemo(() => {
    const links = workspace?.github_links || [];
    return links.map((item, idx) => normalizeGithubLink(item, idx)).filter((r) => r.url);
  }, [workspace?.github_links]);

  const [isAddingRepo, setIsAddingRepo] = useState(false);
  const [repoUrl, setRepoUrl] = useState('');
  const [repoError, setRepoError] = useState('');
  
  // Просмотр содержимого репозитория
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [repoContents, setRepoContents] = useState([]);
  const [currentPath, setCurrentPath] = useState('');
  const [loadingContents, setLoadingContents] = useState(false);
  const [contentsError, setContentsError] = useState('');
  const [viewingFile, setViewingFile] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const [loadingFile, setLoadingFile] = useState(false);

  const resetForm = () => {
    setFormData({
      id: null,
      title: '',
      description: '',
      task_type: 'task', // Идеи создаются только в DeadlineCalendar
      priority: 'medium',
      status: 'todo', // Идеи создаются только в DeadlineCalendar
      deadline: '',
      estimated_hours: '',
    });
    setIsCreating(false);
  };

  const handleOpenTask = async (task) => {
    setSelectedTask(task);
    setIsViewModalOpen(true);
    setCommentText('');
    setAttachedFiles([]);
    dispatch(clearTaskComments());

    if (projectId && workspaceId && task?.id) {
      try {
        await dispatch(fetchTask({ projectId, workspaceId, taskId: task.id }));
        await dispatch(
          fetchTaskComments({ projectId, workspaceId, taskId: task.id, limit: 50, offset: 0 })
        );
      } catch (e) {
        console.error('Failed to fetch task details/comments', e);
      }
    }
  };

  const handleEditTask = (task) => {
    setFormData({
      id: task.id,
      title: task.title || '',
      description: task.description || '',
      task_type: task.task_type || 'task',
      priority: task.priority || 'medium',
      status: task.status || 'todo',
      deadline: task.deadline ? task.deadline.slice(0, 16) : '',
      estimated_hours: task.estimated_hours ?? '',
    });
    setIsCreating(true);
    setIsViewModalOpen(false);
  };

  const handleDeleteTask = async (task) => {
    if (!projectId || !workspaceId || !task?.id) return;
    if (!window.confirm('Удалить задачу?')) return;
    try {
      await dispatch(deleteTask({ projectId, workspaceId, taskId: task.id })).unwrap();
      dispatch(fetchTasks({ projectId, workspaceId, params: {} }));
    } catch (e) {
      console.error('Failed to delete task', e);
    }
  };

  const handleAddComment = async () => {
    if (!projectId || !workspaceId || !selectedTask?.id) return;
    if (!commentText.trim() && attachedFiles.length === 0) return;

    const commentData = {
      content: commentText.trim() || ' ',
      file_ids: attachedFiles.map((f) => f.id),
    };

    try {
      setSendingComment(true);
      await dispatch(
        addTaskComment({
          projectId,
          workspaceId,
          taskId: selectedTask.id,
          commentData,
        })
      ).unwrap();
      setCommentText('');
      setAttachedFiles([]);
    } catch (e) {
      console.error('Failed to add comment', e);
    } finally {
      setSendingComment(false);
    }
  };

  const handleDeleteComment = async (commentId) => {
    if (!projectId || !workspaceId || !commentId) return;
    if (!window.confirm('Удалить комментарий?')) return;
    try {
      await dispatch(
        deleteTaskComment({ projectId, workspaceId, commentId })
      ).unwrap();
    } catch (e) {
      console.error('Failed to delete comment', e);
    }
  };

  const handleAttachFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !projectId || !workspaceId) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('workspace_id', workspaceId);

    try {
      setCommentUploadLoading(true);
      const result = await dispatch(
        uploadProjectFile({ projectId, workspaceId, formData })
      ).unwrap();
      if (result?.file) {
        setAttachedFiles((prev) => [...prev, result.file]);
      }
      e.target.value = '';
    } catch (err) {
      console.error('Ошибка загрузки файла для комментария', err);
    } finally {
      setCommentUploadLoading(false);
    }
  };

  // Проверка подключения GitHub
  const isGitHubConnected = useMemo(() => {
    return profile?.github_access_token ? true : false;
  }, [profile]);

  // Сохранение репозиториев в workspace (API: github_links = string[])
  const saveGithubLinks = async (repos) => {
    if (!workspaceId || !workspace) return;
    const github_links = repos.map((r) => r.url);
    try {
      console.log(workspaceId, projectId, 'wergewrg')
      await dispatch(
        updateWorkspace({ projectId, workspaceId, workspaceData: { github_links } })
      ).unwrap();
      if (projectId) dispatch(fetchProject(projectId));
    } catch (e) {
      console.error('Ошибка сохранения репозиториев:', e);
    }
  };

  // Валидация URL репозитория GitHub
  const validateGitHubUrl = (url) => {
    if (!url.trim()) {
      return { valid: false, error: 'Введите URL репозитория' };
    }
  
    // Проверяем формат GitHub URL
    const githubUrlPattern = /^https?:\/\/(www\.)?github\.com\/[\w\-\.]+\/[\w\-\.]+(\/)?$/;
    if (!githubUrlPattern.test(url.trim())) {
      return { valid: false, error: 'Введите корректный URL репозитория GitHub (например: https://github.com/username/repo)' };
    }
    
    return { valid: true, error: '' };
  };

  // Добавление репозитория
  const handleAddRepository = async () => {
    setRepoError('');
    const validation = validateGitHubUrl(repoUrl);
    
    if (!validation.valid) {
      setRepoError(validation.error);
      return;
    }

    const cleanUrl = repoUrl.trim().replace(/\/$/, ''); // Убираем trailing slash
    
    // Проверяем, не добавлен ли уже этот репозиторий
    if (repositories.some((repo) => repo.url === cleanUrl)) {
      setRepoError('Этот репозиторий уже добавлен');
      return;
    }

    const urlParts = cleanUrl.split('/');
    const repoName = urlParts[urlParts.length - 1];
    const owner = urlParts[urlParts.length - 2];
    const newRepo = { id: `gh-${Date.now()}`, url: cleanUrl, name: repoName, owner, addedAt: new Date().toISOString() };
    const updatedRepos = [...repositories, newRepo];
    await saveGithubLinks(updatedRepos);
    setRepoUrl('');
    setIsAddingRepo(false);
  };

  // Удаление репозитория
  const handleRemoveRepository = async (repoId) => {
    if (!window.confirm('Удалить репозиторий из списка?')) return;
    const updatedRepos = repositories.filter((repo) => repo.id !== repoId);
    await saveGithubLinks(updatedRepos);
    if (selectedRepo?.id === repoId) {
      setSelectedRepo(null);
      setRepoContents([]);
      setCurrentPath('');
    }
  };

  // Открыть репозиторий для просмотра
  const handleOpenRepository = async (repo) => {
    if (!isGitHubConnected || !profile?.github_access_token) {
      setContentsError('GitHub не подключен');
      return;
    }

    setSelectedRepo(repo);
    setCurrentPath('');
    setContentsError('');
    setLoadingContents(true);
    setViewingFile(null);
    setFileContent('');

    try {
      const contents = await githubAPI.getRepositoryContents(
        repo.owner,
        repo.name,
        '',
        profile.github_access_token
      );
      setRepoContents(Array.isArray(contents) ? contents : [contents]);
    } catch (error) {
      console.error('Ошибка загрузки содержимого репозитория:', error);
      setContentsError('Не удалось загрузить содержимое репозитория. Проверьте доступ к репозиторию.');
    } finally {
      setLoadingContents(false);
    }
  };

  // Перейти в папку
  const handleNavigateToFolder = async (path) => {
    if (!selectedRepo || !profile?.github_access_token) return;

    setLoadingContents(true);
    setContentsError('');
    setViewingFile(null);
    setFileContent('');

    try {
      const contents = await githubAPI.getRepositoryContents(
        selectedRepo.owner,
        selectedRepo.name,
        path,
        profile.github_access_token
      );
      setRepoContents(Array.isArray(contents) ? contents : [contents]);
      setCurrentPath(path);
    } catch (error) {
      console.error('Ошибка загрузки содержимого папки:', error);
      setContentsError('Не удалось загрузить содержимое папки.');
    } finally {
      setLoadingContents(false);
    }
  };

  // Просмотр файла
  const handleViewFile = async (file) => {
    if (!selectedRepo || !profile?.github_access_token) return;

    setLoadingFile(true);
    setViewingFile(file);
    setFileContent('');
    setContentsError('');

    try {
      const fileData = await githubAPI.getFileContent(
        selectedRepo.owner,
        selectedRepo.name,
        file.path,
        profile.github_access_token
      );
      setFileContent(fileData.decodedContent || '');
    } catch (error) {
      console.error('Ошибка загрузки файла:', error);
      setContentsError('Не удалось загрузить содержимое файла.');
      setFileContent('');
    } finally {
      setLoadingFile(false);
    }
  };

  // Назад в родительскую папку
  const handleGoBack = () => {
    if (!currentPath || !selectedRepo || !profile?.github_access_token) {
      // Возвращаемся к корню
      handleOpenRepository(selectedRepo);
      return;
    }

    const parentPath = currentPath.split('/').slice(0, -1).join('/');
    handleNavigateToFolder(parentPath);
  };

  // Определение типа файла для иконки
  const getFileIcon = (item) => {
    if (item.type === 'dir') {
      return <FaFolder className="text-blue-400" />;
    }
    return <FaFile className="text-gray-400" />;
  };

  // Определение расширения файла для подсветки синтаксиса
  const getFileExtension = (filename) => {
    const parts = filename.split('.');
    return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : '';
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!projectId || !workspaceId || !formData.title.trim()) return;

    const payload = {
      title: formData.title.trim(),
      description: formData.description.trim() || null,
      task_type: formData.task_type,
      priority: formData.priority,
      status: formData.status,
      deadline: formData.deadline ? new Date(formData.deadline).toISOString() : null,
      estimated_hours:
        formData.estimated_hours !== ''
          ? Number(formData.estimated_hours)
          : null,
    };

    try {
      if (formData.id) {
        await dispatch(
          updateTask({
            projectId,
            workspaceId,
            taskId: formData.id,
            taskData: payload,
          })
        ).unwrap();
      } else {
        await dispatch(
          createTask({
            projectId,
            workspaceId,
            taskData: payload,
          })
        ).unwrap();
      }
      await dispatch(fetchTasks({ projectId, workspaceId, params: {} }));
      resetForm();
    } catch (e) {
      console.error('Failed to save task', e);
      alert(formatApiError(e, 'Не удалось сохранить задачу'));
    }
  };

  // Группируем задачи по статусу в соответствии с backend enum TaskStatus
  const columns = useMemo(
    () => [
      {
        id: 'idea',
        title: 'Идеи',
        tasks: tasks.filter((t) => t.status === 'idea'),
      },
      {
        id: 'todo',
        title: 'К выполнению',
        tasks: tasks.filter((t) => t.status === 'todo'),
      },
      {
        id: 'in_progress',
        title: 'В работе',
        tasks: tasks.filter((t) => t.status === 'in_progress'),
      },
      {
        id: 'review',
        title: 'На проверке',
        tasks: tasks.filter((t) => t.status === 'review'),
      },
      {
        id: 'done',
        title: 'Выполнено',
        tasks: tasks.filter((t) => t.status === 'done'),
      },
      {
        id: 'cancelled',
        title: 'Отменено',
        tasks: tasks.filter((t) => t.status === 'cancelled'),
      },
    ],
    [tasks]
  );

  // Вкладки
  const tabs = [
    { id: 'kanban', name: 'Доска задач', icon: FaTasks },
    { id: 'code', name: 'Код', icon: FaCode },
  ];

  return (
    <div className="bg-gray-900/80 rounded-2xl p-6">
      {/* Заголовок и вкладки */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-bold text-white">Управление задачами</h3>
          <button
            onClick={() => {
              if (isCreating) {
                resetForm();
              } else {
                setIsCreating(true);
              }
            }}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm"
          >
            {isCreating ? 'Отменить' : 'Новая задача'}
          </button>
        </div>

        {/* Форма создания/редактирования задачи */}
        {isCreating && (
          <form
            onSubmit={handleSubmit}
            className="mb-6 bg-gray-800/70 rounded-xl p-4 border border-gray-700 space-y-3"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-gray-400 mb-1">
                  Заголовок
                </label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      title: e.target.value,
                    }))
                  }
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:border-purple-500"
                  placeholder="Что нужно сделать?"
                  required
                />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">
                    Тип
                  </label>
                  {formData.task_type === 'idea' ? (
                    <div className="w-full px-2 py-2 bg-gray-900/50 border border-gray-700 rounded-lg text-xs text-gray-400 cursor-not-allowed">
                      Идея (редактируется в календаре)
                    </div>
                  ) : (
                    <select
                      value={formData.task_type}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          task_type: e.target.value,
                        }))
                      }
                      className="w-full px-2 py-2 bg-gray-900 border border-gray-700 rounded-lg text-xs text-white focus:outline-none focus:border-purple-500"
                    >
                      <option value="task">Задача</option>
                      <option value="urgent_task">Срочная задача</option>
                    </select>
                  )}
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">
                    Приоритет
                  </label>
                  <select
                    value={formData.priority}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        priority: e.target.value,
                      }))
                    }
                    className="w-full px-2 py-2 bg-gray-900 border border-gray-700 rounded-lg text-xs text-white focus:outline-none focus:border-purple-500"
                  >
                    <option value="low">Низкий</option>
                    <option value="medium">Средний</option>
                    <option value="high">Высокий</option>
                    <option value="urgent">Срочный</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">
                    Статус
                  </label>
                  {formData.status === 'idea' ? (
                    <div className="w-full px-2 py-2 bg-gray-900/50 border border-gray-700 rounded-lg text-xs text-gray-400 cursor-not-allowed">
                      Идея (редактируется в календаре)
                    </div>
                  ) : (
                    <select
                      value={formData.status}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          status: e.target.value,
                        }))
                      }
                      className="w-full px-2 py-2 bg-gray-900 border border-gray-700 rounded-lg text-xs text-white focus:outline-none focus:border-purple-500"
                    >
                      <option value="todo">К выполнению</option>
                      <option value="in_progress">В работе</option>
                      <option value="review">На проверке</option>
                      <option value="done">Выполнено</option>
                      <option value="cancelled">Отменено</option>
                    </select>
                  )}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="md:col-span-2">
                <label className="block text-xs text-gray-400 mb-1">
                  Описание
                </label>
                <textarea
                  rows={2}
                  value={formData.description}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      description: e.target.value,
                    }))
                  }
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:border-purple-500 resize-none"
                  placeholder="Краткое описание задачи"
                />
              </div>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">
                    Дедлайн
                  </label>
                  <input
                    type="datetime-local"
                    value={formData.deadline}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        deadline: e.target.value,
                      }))
                    }
                    className="w-full px-2 py-2 bg-gray-900 border border-gray-700 rounded-lg text-xs text-white focus:outline-none focus:border-purple-500"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">
                    Оценка (часы)
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={formData.estimated_hours}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        estimated_hours: e.target.value,
                      }))
                    }
                    className="w-full px-2 py-2 bg-gray-900 border border-gray-700 rounded-lg text-xs text-white focus:outline-none focus:border-purple-500"
                    placeholder="Напр. 4"
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={resetForm}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg text-sm"
              >
                Отмена
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm"
              >
                {formData.id ? 'Сохранить' : 'Создать'}
              </button>
            </div>
          </form>
        )}

        {/* Вкладки */}
        <div className="flex gap-2 border-b border-gray-700">
          {tabs.map((tab) => {
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
        {/* Доска задач с backend Tasks */}
        {activeTab === 'kanban' && (
          <div>
            <h4 className="text-lg font-semibold text-white mb-4">
              Доска задач рабочего пространства
            </h4>
            {tasks.length === 0 ? (
              <div className="text-center py-10 text-gray-500 text-sm">
                Задач пока нет. Нажмите «Новая задача», чтобы добавить первую.
              </div>
            ) : (
              <div className="flex flex-col md:flex-row gap-4 md:overflow-x-auto pb-2">
                {columns.map((column) => (
                  <div
                    key={column.id}
                    className="w-full md:min-w-[280px] md:max-w-xs md:flex-shrink-0 bg-gray-800/50 rounded-xl p-4"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-semibold text-white">
                        {column.title}
                      </h4>
                      <span className="text-xs text-gray-400">
                        {column.tasks.length}
                      </span>
                    </div>
                    <div className="space-y-3">
                      {column.tasks.map((task) => (
                        <TaskCard
                          key={task.id}
                          task={task}
                          onClick={() => handleOpenTask(task)}
                          onEdit={handleEditTask}
                          onDelete={handleDeleteTask}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Код / репозиторий */}
        {activeTab === 'code' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-lg font-semibold text-white">
                Репозитории проекта
              </h4>
              {isGitHubConnected && (
                <button
                  onClick={() => {
                    setIsAddingRepo(!isAddingRepo);
                    setRepoUrl('');
                    setRepoError('');
                  }}
                  className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm transition-all duration-200"
                >
                  <FaPlus size={14} />
                  Добавить репозиторий
                </button>
              )}
            </div>

            {/* Статус подключения GitHub */}
            {!isGitHubConnected && (
              <div className="bg-yellow-900/20 border border-yellow-700/50 rounded-xl p-6 mb-6">
                <div className="flex items-start gap-4">
                  <FaGithub className="text-yellow-400 text-2xl mt-1" />
                  <div className="flex-1">
                    <h5 className="text-yellow-400 font-semibold mb-2">
                      GitHub не подключен
                    </h5>
                    <p className="text-gray-300 text-sm mb-4">
                      Для привязки репозиториев необходимо подключить GitHub в профиле.
                    </p>
                    <a
                      href="/profile"
                      className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm transition-all duration-200"
                    >
                      Перейти в профиль
                      <FaExternalLinkAlt size={12} />
                    </a>
                  </div>
                </div>
              </div>
            )}

            {/* Форма добавления репозитория */}
            {isGitHubConnected && isAddingRepo && (
              <div className="bg-gray-800/70 rounded-xl p-4 border border-gray-700 mb-6">
                <h5 className="text-white font-semibold mb-3 flex items-center gap-2">
                  <FaGithub />
                  Добавить репозиторий GitHub
                </h5>
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">
                      URL репозитория
                    </label>
                    <input
                      type="text"
                      value={repoUrl}
                      onChange={(e) => {
                        setRepoUrl(e.target.value);
                        setRepoError('');
                      }}
                      placeholder="https://github.com/username/repository"
                      className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-white focus:outline-none focus:border-purple-500"
                    />
                    {repoError && (
                      <p className="text-red-400 text-xs mt-1">{repoError}</p>
                    )}
                  </div>
                  <div className="flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        setIsAddingRepo(false);
                        setRepoUrl('');
                        setRepoError('');
                      }}
                      className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-lg text-sm"
                    >
                      Отмена
                    </button>
                    <button
                      type="button"
                      onClick={handleAddRepository}
                      className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm"
                    >
                      Добавить
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Просмотр содержимого репозитория */}
            {selectedRepo ? (
              <div className="bg-gray-800/70 rounded-xl border border-gray-700">
                {/* Заголовок с навигацией */}
                <div className="p-4 border-b border-gray-700">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => {
                          setSelectedRepo(null);
                          setRepoContents([]);
                          setCurrentPath('');
                          setViewingFile(null);
                          setFileContent('');
                        }}
                        className="text-gray-400 hover:text-white transition-colors"
                        title="Вернуться к списку репозиториев"
                      >
                        <FaArrowLeft size={16} />
                      </button>
                      <div className="flex items-center gap-2">
                        <FaGithub className="text-purple-400" />
                        <h5 className="text-white font-semibold">
                          {selectedRepo.owner} / {selectedRepo.name}
                        </h5>
                      </div>
                    </div>
                    <a
                      href={selectedRepo.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-purple-400 hover:text-purple-300 text-sm flex items-center gap-1"
                    >
                      <span>На GitHub</span>
                      <FaExternalLinkAlt size={12} />
                    </a>
                  </div>
                  
                  {/* Хлебные крошки */}
                  {currentPath && (
                    <div className="flex items-center gap-2 text-sm text-gray-400">
                      <button
                        onClick={handleGoBack}
                        className="hover:text-white transition-colors"
                      >
                        Корень
                      </button>
                      <span>/</span>
                      {currentPath.split('/').map((part, index, arr) => {
                        const path = arr.slice(0, index + 1).join('/');
                        return (
                          <React.Fragment key={index}>
                            {index < arr.length - 1 ? (
                              <>
                                <button
                                  onClick={() => handleNavigateToFolder(path)}
                                  className="hover:text-white transition-colors"
                                >
                                  {part}
                                </button>
                                <span>/</span>
                              </>
                            ) : (
                              <span className="text-gray-500">{part}</span>
                            )}
                          </React.Fragment>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Содержимое */}
                <div className="p-4">
                  {loadingContents ? (
                    <div className="flex items-center justify-center py-12">
                      <FaSpinner className="animate-spin text-purple-400 text-2xl" />
                    </div>
                  ) : contentsError ? (
                    <div className="text-red-400 text-sm py-4">{contentsError}</div>
                  ) : repoContents.length === 0 ? (
                    <div className="text-gray-500 text-sm py-8 text-center">
                      Папка пуста
                    </div>
                  ) : (
                    <div className="space-y-1">
                      {repoContents
                        .sort((a, b) => {
                          // Папки сначала
                          if (a.type === 'dir' && b.type !== 'dir') return -1;
                          if (a.type !== 'dir' && b.type === 'dir') return 1;
                          return a.name.localeCompare(b.name);
                        })
                        .map((item) => (
                          <div
                            key={item.sha}
                            onClick={() => {
                              if (item.type === 'dir') {
                                handleNavigateToFolder(item.path);
                              } else {
                                handleViewFile(item);
                              }
                            }}
                            className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-700/50 cursor-pointer transition-colors group"
                          >
                            <div className="flex-shrink-0">
                              {getFileIcon(item)}
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-white text-sm truncate group-hover:text-purple-300 transition-colors">
                                {item.name}
                              </p>
                             
                            </div>
                            {item.type === 'file' && (
                              <span className="text-xs text-gray-500 px-2 py-1 bg-gray-900 rounded">
                                {getFileExtension(item.name) || 'file'}
                              </span>
                            )}
                          </div>
                        ))}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <>
                {/* Список репозиториев */}
                {repositories.length === 0 ? (
                  <div className="text-center py-16 text-gray-500">
                    <FaGithub size={64} className="mx-auto mb-4 opacity-50" />
                    <p className="mb-2">
                      {isGitHubConnected 
                        ? 'Репозитории не добавлены. Нажмите "Добавить репозиторий", чтобы начать.'
                        : 'Подключите GitHub в профиле, чтобы добавить репозитории.'}
                    </p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {repositories.map((repo) => (
                      <div
                        key={repo.id}
                        className="bg-gray-800/70 rounded-xl p-5 border border-gray-700 hover:border-purple-600/50 transition-all duration-300 group"
                      >
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-center gap-3 flex-1 min-w-0">
                            <div className="flex-shrink-0 w-10 h-10 bg-gray-900 rounded-lg flex items-center justify-center">
                              <FaGithub className="text-purple-400 text-xl" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <h5 className="text-white font-semibold truncate group-hover:text-purple-300 transition-colors">
                                {repo.name}
                              </h5>
                              <p className="text-gray-400 text-xs truncate">
                                {repo.owner}
                              </p>
                            </div>
                          </div>
                          <button
                            onClick={() => handleRemoveRepository(repo.id)}
                            className="flex-shrink-0 text-gray-500 hover:text-red-400 transition-colors p-1"
                            title="Удалить репозиторий"
                          >
                            <FaTrash size={14} />
                          </button>
                        </div>
                        
                        <div className="flex flex-col gap-2">
                          {isGitHubConnected && (
                            <button
                              onClick={() => handleOpenRepository(repo)}
                              className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm transition-all duration-200 flex items-center justify-center gap-2"
                            >
                              <FaCode size={14} />
                              Просмотреть код
                            </button>
                          )}
                          <a
                            href={repo.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-2 text-purple-400 hover:text-purple-300 text-sm font-medium transition-colors group/link justify-center"
                          >
                            <span>Открыть на GitHub</span>
                            <FaExternalLinkAlt size={12} className="group-hover/link:translate-x-1 transition-transform" />
                          </a>
                        </div>
                        
                        <div className="mt-3 pt-3 border-t border-gray-700">
                          <p className="text-gray-500 text-xs">
                            Добавлен {new Date(repo.addedAt).toLocaleDateString('ru-RU')}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}

            {/* Индикатор подключения GitHub */}
            {isGitHubConnected && repositories.length > 0 && !selectedRepo && (
              <div className="mt-6 flex items-center justify-center gap-2 text-green-400 text-sm">
                <FaCheck />
                <span>GitHub подключен</span>
              </div>
            )}
          </div>
        )}

      {/* Модальное окно просмотра файла */}
      {viewingFile && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 rounded-2xl w-full max-w-4xl max-h-[90vh] border border-gray-800 shadow-2xl flex flex-col">
            {/* Заголовок */}
            <div className="flex items-center justify-between p-4 border-b border-gray-800">
              <div className="flex items-center gap-3 flex-1 min-w-0">
                {getFileIcon(viewingFile)}
                <div className="flex-1 min-w-0">
                  <h3 className="text-white font-semibold truncate">
                    {viewingFile.name}
                  </h3>
                  <p className="text-gray-400 text-xs truncate">
                    {viewingFile.path}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <a
                  href={`https://github.com/${selectedRepo?.owner}/${selectedRepo?.name}/blob/main/${viewingFile.path}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-purple-400 hover:text-purple-300 text-sm flex items-center gap-1"
                >
                  <span>На GitHub</span>
                  <FaExternalLinkAlt size={12} />
                </a>
                <button
                  onClick={() => {
                    setViewingFile(null);
                    setFileContent('');
                  }}
                  className="text-gray-400 hover:text-white text-xl leading-none ml-2"
                >
                  ×
                </button>
              </div>
            </div>

            {/* Содержимое файла */}
            <div className="flex-1 overflow-auto p-4">
              {loadingFile ? (
                <div className="flex items-center justify-center py-12">
                  <FaSpinner className="animate-spin text-purple-400 text-2xl" />
                </div>
              ) : fileContent ? (
                <pre className="bg-gray-950 rounded-lg p-4 overflow-x-auto text-sm text-gray-300 font-mono">
                  <code>{fileContent}</code>
                </pre>
              ) : (
                <div className="text-gray-500 text-sm py-8 text-center">
                  Не удалось загрузить содержимое файла
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      </div>

      {/* Модальное окно просмотра задачи + комментарии */}
      {isViewModalOpen && selectedTask && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-gray-900 rounded-2xl w-full max-w-lg p-6 border border-gray-800 shadow-2xl">
            <div className="flex items-start justify-between mb-4">
              <div>
                <p className="text-xs text-gray-500 mb-1">Задача рабочего пространства</p>
                <h2 className="text-xl font-bold text-white">
                  {(currentTask && currentTask.id === selectedTask.id
                    ? currentTask.title
                    : selectedTask.title) || 'Задача'}
                </h2>
              </div>
              <button
                onClick={() => setIsViewModalOpen(false)}
                className="text-gray-400 hover:text-white text-lg leading-none"
              >
                ×
              </button>
            </div>

            {/* Описание */}
            <div className="mb-4">
              <h3 className="text-sm font-semibold text-gray-300 mb-1">Описание</h3>
              <p className="text-sm text-gray-300 whitespace-pre-line">
                {(currentTask && currentTask.id === selectedTask.id
                  ? currentTask.description
                  : selectedTask.description) || 'Описание не заполнено.'}
              </p>
            </div>

            {/* Метаданные */}
            <div className="grid grid-cols-2 gap-3 text-xs text-gray-400 mb-4">
              <div>
                <span className="block text-gray-500">Тип</span>
                <span className="text-white">
                  {selectedTask.task_type === 'idea'
                    ? 'Идея'
                    : selectedTask.task_type === 'urgent_task'
                    ? 'Срочная задача'
                    : 'Задача'}
                </span>
              </div>
              <div>
                <span className="block text-gray-500">Приоритет</span>
                <span className="text-white">
                  {selectedTask.priority === 'low'
                    ? 'Низкий'
                    : selectedTask.priority === 'medium'
                    ? 'Средний'
                    : selectedTask.priority === 'high'
                    ? 'Высокий'
                    : selectedTask.priority === 'urgent'
                    ? 'Срочный'
                    : selectedTask.priority}
                </span>
              </div>
              <div>
                <span className="block text-gray-500">Статус</span>
                <span className="text-white">
                  {selectedTask.status === 'idea'
                    ? 'Идея'
                    : selectedTask.status === 'todo'
                    ? 'К выполнению'
                    : selectedTask.status === 'in_progress'
                    ? 'В работе'
                    : selectedTask.status === 'review'
                    ? 'На проверке'
                    : selectedTask.status === 'done'
                    ? 'Выполнено'
                    : selectedTask.status === 'cancelled'
                    ? 'Отменено'
                    : selectedTask.status}
                </span>
              </div>
              <div>
                <span className="block text-gray-500">Дедлайн</span>
                <span className="text-white">
                  {selectedTask.deadline
                    ? new Date(selectedTask.deadline).toLocaleString('ru-RU')
                    : 'Не задан'}
                </span>
              </div>
            </div>

            {/* Комментарии к задаче */}
            <div className="mt-4 border-t border-gray-800 pt-4">
              <h3 className="text-sm font-semibold text-gray-300 mb-2 flex items-center gap-2">
                Комментарии
              </h3>

              {taskCommentsLoading ? (
                <p className="text-xs text-gray-500 mb-2">Загрузка комментариев...</p>
              ) : taskComments.length === 0 ? (
                <p className="text-xs text-gray-500 mb-2">
                  Комментариев пока нет. Оставьте первый.
                </p>
              ) : (
                <div className="max-h-48 overflow-y-auto space-y-2 mb-3 pr-1">
                  {taskComments.map((comment) => (
                    <div
                      key={comment.id}
                      className="bg-gray-800/60 rounded-lg px-3 py-2 text-xs text-gray-200 flex justify-between gap-2"
                    >
                      <div>
                        <p className="whitespace-pre-line text-gray-100">
                          {comment.content}
                        </p>
                        {comment.attachments && comment.attachments.length > 0 && (
                          <div className="flex flex-wrap gap-2 mt-1">
                            {comment.attachments.map((file) => (
                              <span
                                key={file.id}
                                className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-gray-900/70 text-[10px] text-gray-300 border border-gray-700"
                              >
                                <FaPaperclip size={10} />
                                {file.original_filename}
                              </span>
                            ))}
                          </div>
                        )}
                        <p className="text-[10px] text-gray-500 mt-1">
                          {new Date(comment.created_at).toLocaleString('ru-RU')}
                        </p>
                      </div>
                      <button
                        onClick={() => handleDeleteComment(comment.id)}
                        className="text-gray-500 hover:text-red-400 self-start"
                        title="Удалить комментарий"
                      >
                        <FaTrash size={10} />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Форма добавления комментария */}
              <div className="space-y-2">
                <textarea
                  rows={2}
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-xs text-white focus:outline-none focus:border-purple-500 resize-none"
                  placeholder="Оставьте комментарий к задаче..."
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                />

                {attachedFiles.length > 0 && (
                  <div className="flex flex-wrap gap-2 text-[10px] text-gray-300">
                    {attachedFiles.map((file) => (
                      <span
                        key={file.id}
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-gray-800 border border-gray-700"
                      >
                        <FaPaperclip size={10} />
                        {file.original_filename}
                      </span>
                    ))}
                  </div>
                )}

                <div className="flex items-center justify-between gap-2">
                  <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer">
                    <input
                      type="file"
                      className="hidden"
                      onChange={handleAttachFile}
                      disabled={!projectId || commentUploadLoading}
                    />
                    <FaPaperclip size={12} />
                    {commentUploadLoading ? 'Загрузка файла...' : 'Прикрепить файл'}
                  </label>

                  <button
                    onClick={handleAddComment}
                    disabled={sendingComment || (!commentText.trim() && attachedFiles.length === 0)}
                    className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-xs"
                  >
                    {sendingComment ? 'Отправка...' : 'Отправить комментарий'}
                  </button>
                </div>
              </div>
            </div>

            <div className="flex justify-between gap-2 mt-4">
              <button
                onClick={() => {
                  handleEditTask(
                    currentTask && currentTask.id === selectedTask.id
                      ? currentTask
                      : selectedTask
                  );
                }}
                className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm"
              >
                Редактировать задачу
              </button>
              <button
                onClick={() => handleDeleteTask(selectedTask)}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm"
              >
                Удалить
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};