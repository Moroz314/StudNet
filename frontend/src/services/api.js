import axios from 'axios';

// В dev-режиме используем относительный baseURL.
// Это важно, чтобы запросы уходили в Vite (и прокси в `vite.config.js` перенаправлял их на backend),
// а не напрямую на `http://45.11.92.114:8000` (иначе снова будет CORS).
const API_BASE_URL = 'http://45.11.92.114:8000';
const MINIO_INTERNAL_ORIGIN = 'http://minio:9000';
const MINIO_PUBLIC_ORIGIN = 'http://localhost:9100';

export const normalizeAssetUrl = (rawUrl) => {
  if (!rawUrl || typeof rawUrl !== 'string') return rawUrl;

  if (rawUrl.startsWith(MINIO_INTERNAL_ORIGIN)) {
    return rawUrl.replace(MINIO_INTERNAL_ORIGIN, MINIO_PUBLIC_ORIGIN);
  }

  if (rawUrl.startsWith('/')) {
    return `${API_BASE_URL}${rawUrl}`;
  }

  return rawUrl;
};

const normalizeResponseUrls = (value) => {
  if (Array.isArray(value)) {
    return value.map(normalizeResponseUrls);
  }

  if (value && typeof value === 'object') {
    const next = {};
    Object.entries(value).forEach(([k, v]) => {
      next[k] = normalizeResponseUrls(v);
    });
    return next;
  }

  if (typeof value === 'string') {
    return normalizeAssetUrl(value);
  }

  return value;
};

const PERMISSION_DENIED_MARKERS = [
  'access denied',
  "you don't have access",
  'not allowed',
  'permission',
  'forbidden resource',
];

export const isAuthTokenError = (error) => {
  const status = error?.response?.status ?? error?.status;
  const detailRaw = error?.response?.data?.detail ?? error?.data?.detail ?? error?.detail;
  const detail = typeof detailRaw === 'string' ? detailRaw : JSON.stringify(detailRaw || '');

  if (status === 401) return true;
  if (status !== 403) return false;

  const normalized = detail.toLowerCase();
  if (PERMISSION_DENIED_MARKERS.some((marker) => normalized.includes(marker))) {
    return false;
  }

  return (
    normalized.includes('expired')
    || normalized.includes('signature')
    || normalized.includes('jwt')
    || normalized.includes('not user token')
    || normalized.includes('could not validate')
    || normalized.includes('invalid token')
    || normalized.includes('credentials')
  );
};

export const clearAuthSession = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('access_token');
  localStorage.removeItem('profile');
  localStorage.removeItem('registration_email');
};

export const formatApiError = (error, fallback = 'Произошла ошибка. Попробуйте ещё раз.') => {
  const status = error?.response?.status ?? error?.status;
  const detailRaw = error?.response?.data?.detail ?? error?.data?.detail ?? error?.detail ?? error?.message;
  let detail = '';
  if (typeof detailRaw === 'string') detail = detailRaw;
  else if (Array.isArray(detailRaw)) detail = detailRaw.map((x) => x?.msg || x?.message || JSON.stringify(x)).join(', ');
  else if (detailRaw && typeof detailRaw === 'object') detail = detailRaw.message || JSON.stringify(detailRaw);
  else detail = String(detailRaw || '');

  const normalized = detail.toLowerCase();

  if (status === 401 || isAuthTokenError(error)) {
    return 'Сессия истекла. Войдите снова, используя email и пароль.';
  }
  if (status === 403) {
    if (normalized.includes('workspace')) return 'У вас нет доступа к этому рабочему пространству.';
    if (normalized.includes('project')) return 'У вас нет доступа к этому проекту.';
    if (normalized.includes('permission') || normalized.includes('access')) return 'Недостаточно прав для этого действия.';
    return detail || 'Доступ запрещён.';
  }
  if (status === 404) {
    if (normalized.includes('profile') || normalized.includes('профил')) return 'Профиль не найден. Завершите регистрацию или войдите снова.';
    if (normalized.includes('project')) return 'Проект не найден или недоступен.';
    if (normalized.includes('post')) return 'Публикация в ленте не найдена.';
    return detail || 'Данные не найдены.';
  }
  if (status === 400) {
    if (normalized.includes('code') || normalized.includes('verification') || normalized.includes('expired')) {
      return 'Код подтверждения неверный или истёк. Войдите с паролем или запросите новый код.';
    }
    return detail || 'Проверьте введённые данные.';
  }
  if (status === 409) return detail || 'Конфликт данных. Возможно, такая запись уже существует.';
  if (status === 422) return detail || 'Некорректные данные в форме.';
  if (status >= 500) return 'Ошибка сервера. Попробуйте позже.';

  return detail || fallback;
};

export const isProfileMissingError = (error) => {
  const status = error?.response?.status ?? error?.status;
  if (status !== 404) return false;
  const detail = String(error?.response?.data?.detail ?? error?.detail ?? '').toLowerCase();
  return detail.includes('profile') || detail.includes('профил');
};

export const redirectToAuth = () => {
  const path = window.location.pathname;
  if (path.startsWith('/login') || path.startsWith('/auth') || path.startsWith('/registr')) {
    return;
  }
  window.location.href = '/login';
};

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
  withCredentials: false,
});

const apiFile = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  withCredentials: false,
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    
    if (token) {
      console.log('🔐 Adding token to request:', config.url, 'Token:', token.substring(0, 20) + '...');
      config.headers.Authorization = `Bearer ${token}`;
    } else {
      console.warn('⚠️ No token found for request:', config.url);
    }
    
    return config;
  },
  (error) => {
    console.error('❌ Request interceptor error:', error);
    return Promise.reject(error);
  }
);

apiFile.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    
    if (token) {
      console.log('🔐 Adding token to file upload:', config.url);
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    if (config.headers['Content-Type']) {
      delete config.headers['Content-Type'];
    }
    
    return config;
  },
  (error) => {
    console.error('❌ File request interceptor error:', error);
    return Promise.reject(error);
  }
);

const responseInterceptor = (response) => {
  if (response?.data !== undefined) {
    response.data = normalizeResponseUrls(response.data);
  }
  console.log('✅ Response success:', response.config.url, response.status);
  return response;
};

const errorInterceptor = (error) => {
  const originalRequest = error.config;
  const status = error.response?.status;
  
  console.error('❌ Response error:', {
    url: originalRequest?.url,
    status: status,
    data: error.response?.data
  });

  if (isAuthTokenError(error)) {
    console.warn('🔄 Session expired or invalid token - redirecting to login');
    clearAuthSession();
    redirectToAuth();
  }
  // 403 с "Access denied" и т.п. — отказ в правах, токен не трогаем

  const enhancedError = {
    ...error,
    message: formatApiError(error, error.response?.data?.message || error.message),
    friendlyMessage: formatApiError(error),
    status: status,
    data: error.response?.data
  };

  return Promise.reject(enhancedError);
};

api.interceptors.response.use(responseInterceptor, errorInterceptor);
apiFile.interceptors.response.use(responseInterceptor, errorInterceptor);

export const setAuthToken = (token) => {
  if (token) {
    localStorage.setItem('token', token);
  } else {
    localStorage.removeItem('token');
  }
};

export const getAuthToken = () => {
  return localStorage.getItem('token');
};

export const authAPI = {
  login: (credentials) => api.post('/user/login', credentials),
  register: (userData) => api.post('/user/register-init', userData),
  register_code: (userData) => api.post('/user/register', userData),
  logout: () => {
    setAuthToken(null);
    return Promise.resolve();
  },
};

export const profileAPI = {
  createProf: (data) => api.post('/user/profile', data),
  getProfile: () => api.get('/user/profile/personal'),
  getUserProfile: (user_id) => 
    api.get(`/user/profile?user_id=${user_id}`),
  getUserProjects: (user_id, offset = 0, limit = 50) =>
    api.get(`/user/profile/projects?user_id=${user_id}&offset=${offset}&limit=${limit}`),
  UploadAvatar: (avatarData) => apiFile.post('/user/avatar', avatarData),
  deleteAvatar: () => api.delete('/user/avatar'),
  getAvatarUrl: () => api.get('/user/avatar/url'),
  getGitHub: (code) => api.patch(`/user/connect-github?code=${encodeURIComponent(code)}`)
};

// GitHub API сервис (используется напрямую с токеном пользователя)
export const githubAPI = {
  decodeBase64Utf8: (base64) => {
    // GitHub отдает content в base64 (UTF-8), atob без TextDecoder ломает кириллицу.
    const binary = atob((base64 || '').replace(/\n/g, ''))
    const bytes = Uint8Array.from(binary, (ch) => ch.charCodeAt(0))
    return new TextDecoder('utf-8').decode(bytes)
  },
  buildHeaders: (accessToken) => {
    const headers = {
      'Accept': 'application/vnd.github.v3+json'
    }
    if (accessToken) {
      headers.Authorization = `Bearer ${accessToken}`
    }
    return headers
  },
  // Получить содержимое репозитория
  getRepositoryContents: async (owner, repo, path = '', accessToken) => {
    const url = `https://api.github.com/repos/${owner}/${repo}/contents/${path}`;
    const response = await fetch(url, {
      headers: githubAPI.buildHeaders(accessToken)
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`GitHub API error: ${response.status} - ${errorText}`);
    }
    return response.json();
  },
  
  // Получить содержимое файла (декодированный base64)
  getFileContent: async (owner, repo, path, accessToken) => {
    const url = `https://api.github.com/repos/${owner}/${repo}/contents/${path}`;
    const response = await fetch(url, {
      headers: githubAPI.buildHeaders(accessToken)
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`GitHub API error: ${response.status} - ${errorText}`);
    }
    const data = await response.json();
    if (data.content && data.encoding === 'base64') {
      return {
        ...data,
        decodedContent: githubAPI.decodeBase64Utf8(data.content)
      };
    }
    return data;
  },
  
  // Получить информацию о репозитории
  getRepositoryInfo: async (owner, repo, accessToken) => {
    const url = `https://api.github.com/repos/${owner}/${repo}`;
    const response = await fetch(url, {
      headers: githubAPI.buildHeaders(accessToken)
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`GitHub API error: ${response.status} - ${errorText}`);
    }
    return response.json();
  }
};

export const projectsAPI = {
  createProject: (projectData) => api.post('/projects/', projectData),
  getProjects: (params = {}) => {
    const queryParams = new URLSearchParams();
    
    if (params.status != null && params.status !== '') queryParams.append('status', params.status);
    if (params.search != null && params.search !== '') queryParams.append('search', params.search);
    if (params.limit != null) queryParams.append('limit', String(params.limit));
    if (params.offset != null) queryParams.append('offset', String(params.offset));
    if (params.tags && params.tags.length > 0) {
      params.tags.forEach(tag => queryParams.append('tags', tag));
    }
    
    const queryString = queryParams.toString();
    return api.get(queryString ? `/projects/?${queryString}` : '/projects/');
  },
  getProject: (projectId) => api.get(`/projects/${projectId}`),
  updateProject: (projectId, projectData) => api.patch(`/projects/${projectId}`, projectData),
  deleteProject: (projectId) => api.delete(`/projects/${projectId}/archive`),
  restoreProject: (projectId) => api.post(`/projects/${projectId}/restore`),
  
  // Workspace methods
  createWorkspace: (projectId, workspaceData) => api.post(`/projects/${projectId}/workspaces`, workspaceData),
  getWorkspaces: (projectId) => api.get(`/projects/${projectId}/workspaces`),
  getWorkspace: (projectId, workspaceId) => api.get(`/projects/${projectId}/workspaces/${workspaceId}`),
  updateWorkspace: (projectId, workspaceId, workspaceData) =>
    api.patch(`/projects/${projectId}/workspaces/${workspaceId}`, workspaceData),
  deleteWorkspace: (projectId, workspaceId) =>
    api.delete(`/projects/${projectId}/workspaces/${workspaceId}`),
  getWorkspaceParticipants: (projectId, workspaceId) =>
    api.get(`/projects/${projectId}/workspaces/${workspaceId}/participants`),
  addWorkspaceParticipants: (projectId, workspaceId, userIds, privileges = []) =>
    api.post(`/projects/${projectId}/workspaces/${workspaceId}/participants`, { user_ids: userIds, privileges }),
  removeWorkspaceParticipants: (projectId, workspaceId, participantUserIds) => {
    const ids = Array.isArray(participantUserIds) ? participantUserIds : [participantUserIds];
    const qs = ids.map((id) => `participant_user_ids=${encodeURIComponent(id)}`).join('&');
    return api.delete(`/projects/${projectId}/workspaces/${workspaceId}/participants${qs ? `?${qs}` : ''}`);
  },

  // Participant methods
  addProjectParticipants: (projectId, userIds) => api.post(`/projects/${projectId}/participants`, { user_ids: userIds }),
  getProjectParticipants: (projectId) => api.get(`/projects/${projectId}/participants`),
  removeProjectParticipants: (projectId, participantUserIds) => {
    const ids = Array.isArray(participantUserIds) ? participantUserIds : [participantUserIds];
    const qs = ids.map((id) => `participant_user_ids=${encodeURIComponent(id)}`).join('&');
    return api.delete(`/projects/${projectId}/participants${qs ? `?${qs}` : ''}`);
  },
  updateParticipant: (projectId, participantUserId, data) => api.patch(`/projects/${projectId}/participants/${participantUserId}`, data),
  leaveProject: (projectId) => api.delete(`/projects/${projectId}/leave`),
  
  // Invitations (project join flow)
  createProjectInvitations: (projectId, invitationData) =>
    api.post(`/projects/${projectId}/invitations`, invitationData),
  getProjectInvitations: (projectId, status = null) => {
    const query = status ? `?status=${encodeURIComponent(status)}` : ''
    return api.get(`/projects/${projectId}/invitations${query}`)
  },
  getMyProjectInvitations: (status = null) => {
    const query = status ? `?status=${encodeURIComponent(status)}` : ''
    return api.get(`/projects/invitations/personal${query}`)
  },
  respondToProjectInvitation: (invitationId, action) =>
    api.post(`/projects/invitations/${invitationId}/respond`, { action }),
  cancelProjectInvitation: (invitationId) =>
    api.delete(`/projects/invitations/${invitationId}`),

  // Task methods
  createTask: (projectId, workspaceId, taskData) =>
    api.post(`/projects/${projectId}/workspaces/${workspaceId}/tasks/`, taskData),
  getTasks: (projectId, workspaceId, params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.search) queryParams.append('search', params.search);
    if (params.task_type) queryParams.append('task_type', params.task_type);
    if (params.status) queryParams.append('status', params.status);
    if (params.priority) queryParams.append('priority', params.priority);
    if (params.has_deadline) queryParams.append('has_deadline', params.has_deadline);
    if (params.deadline_before) queryParams.append('deadline_before', params.deadline_before);
    if (params.deadline_after) queryParams.append('deadline_after', params.deadline_after);
    if (params.assignee_id) queryParams.append('assignee_id', params.assignee_id);
    if (params.limit) queryParams.append('limit', params.limit);
    if (params.offset) queryParams.append('offset', params.offset);
    const queryString = queryParams.toString();
    return api.get(
      `/projects/${projectId}/workspaces/${workspaceId}/tasks/${queryString ? '?' + queryString : ''}`
    );
  },
  getTask: (projectId, workspaceId, taskId) =>
    api.get(`/projects/${projectId}/workspaces/${workspaceId}/tasks/${taskId}`),
  updateTask: (projectId, workspaceId, taskId, taskData) =>
    api.put(`/projects/${projectId}/workspaces/${workspaceId}/tasks/${taskId}`, taskData),
  deleteTask: (projectId, workspaceId, taskId) =>
    api.delete(`/projects/${projectId}/workspaces/${workspaceId}/tasks/${taskId}`),
  getUpcomingDeadlines: (projectId, workspaceId, days_ahead = 7) =>
    api.get(
      `/projects/${projectId}/workspaces/${workspaceId}/tasks/upcoming-deadlines?days_ahead=${days_ahead}`
    ),
  
  // Task Assignees
  getTaskAssignees: (projectId, workspaceId, taskId) =>
    api.get(`/projects/${projectId}/workspaces/${workspaceId}/tasks/${taskId}/assignees`),
  addTaskAssignees: (projectId, workspaceId, taskId, assignees) =>
    api.post(`/projects/${projectId}/workspaces/${workspaceId}/tasks/${taskId}/assignees`, { assignees }),
  setTaskAssignees: (projectId, workspaceId, taskId, assignees) =>
    api.put(`/projects/${projectId}/workspaces/${workspaceId}/tasks/${taskId}/assignees`, { assignees }),
  removeTaskAssignee: (projectId, workspaceId, taskId, assigneeId) =>
    api.delete(`/projects/${projectId}/workspaces/${workspaceId}/tasks/${taskId}/assignees/${assigneeId}`),

  // Task Comments
  getTaskComments: (projectId, workspaceId, taskId, limit = 50, offset = 0) =>
    api.get(
      `/projects/${projectId}/workspaces/${workspaceId}/tasks/${taskId}/comments?limit=${limit}&offset=${offset}`
    ),
  addTaskComment: (projectId, workspaceId, taskId, commentData) =>
    api.post(`/projects/${projectId}/workspaces/${workspaceId}/tasks/${taskId}/comments`, commentData),
  updateTaskComment: (projectId, workspaceId, commentId, commentData) =>
    api.put(`/projects/${projectId}/workspaces/${workspaceId}/tasks/comments/${commentId}`, commentData),
  deleteTaskComment: (projectId, workspaceId, commentId) =>
    api.delete(`/projects/${projectId}/workspaces/${workspaceId}/tasks/comments/${commentId}`),
  addCommentAttachments: (projectId, workspaceId, commentId, fileIds) =>
    api.post(`/projects/${projectId}/workspaces/${workspaceId}/tasks/comments/${commentId}/attachments`, fileIds),
  removeCommentAttachment: (projectId, workspaceId, commentId, fileId) =>
    api.delete(`/projects/${projectId}/workspaces/${workspaceId}/tasks/comments/${commentId}/attachments/${fileId}`),

  // Statistics
  getWorkspaceStatistics: (projectId, workspaceId, start_date = null, end_date = null) => {
    const params = new URLSearchParams();
    if (start_date) params.append('start_date', start_date);
    if (end_date) params.append('end_date', end_date);
    return api.get(
      `/projects/${projectId}/workspaces/${workspaceId}/tasks/statistics/current?${params.toString()}`
    );
  },
  getStatisticsHistory: (projectId, workspaceId, days = 30) =>
    api.get(
      `/projects/${projectId}/workspaces/${workspaceId}/tasks/statistics/history?days=${days}`
    ),

  // Project Files (S3) - UPDATED according to openapi.json
  attachFileToProject: (projectId, data) => 
    api.post(`/projects/${projectId}/files/attach`, data),
  listProjectFiles: (projectId, workspaceId, params = {}) => {
    const queryParams = new URLSearchParams();
    queryParams.append('workspace_id', workspaceId);
    if (params.limit) queryParams.append('limit', params.limit);
    if (params.offset) queryParams.append('offset', params.offset);
    return api.get(`/projects/${projectId}/files?${queryParams.toString()}`);
  },
  getProjectFile: (projectId, fileId, workspaceId) =>
    api.get(`/projects/${projectId}/files/${fileId}?workspace_id=${encodeURIComponent(workspaceId)}`),
  updateProjectFileMetadata: (projectId, fileId, workspaceId, data) =>
    api.patch(`/projects/${projectId}/files/${fileId}?workspace_id=${encodeURIComponent(workspaceId)}`, data),
  detachFileFromProject: (projectId, fileId, workspaceId, delete_permanently = false) =>
    api.delete(`/projects/${projectId}/files/${fileId}?workspace_id=${encodeURIComponent(workspaceId)}&delete_permanently=${delete_permanently}`),
  getProjectFileDownloadUrl: (projectId, fileId, workspaceId, expiresIn = 3600) =>
    api.get(
      `/projects/${projectId}/files/${fileId}/download-url?workspace_id=${encodeURIComponent(workspaceId)}&expires_in=${expiresIn}`
    ),

  uploadProjectFile: async (projectId, workspaceId, formData) => {
    const file = formData instanceof FormData ? formData.get('file') : formData?.file;
    if (!file) {
      throw new Error('File is required');
    }
    const { data: uploaded } = await filesAPI.uploadFile(file, 'project_file');
    return api.post(`/projects/${projectId}/files/attach`, {
      file_id: uploaded.file_id,
      workspace_id: workspaceId,
    });
  },

  deleteProjectFile: (projectId, workspaceId, fileId, delete_permanently = false) =>
    api.delete(
      `/projects/${projectId}/files/${fileId}?workspace_id=${encodeURIComponent(workspaceId)}&delete_permanently=${delete_permanently}`
    ),

  // Project Avatar
  setProjectAvatar: (projectId, fileId) => 
    api.post(`/projects/${projectId}/avatar`, { file_id: fileId }),
  getProjectAvatar: (projectId) => 
    api.get(`/projects/${projectId}/avatar`),
  removeProjectAvatar: (projectId) => 
    api.delete(`/projects/${projectId}/avatar`),
};

export const feedAPI = {
  getFeed: (params = {}) => {
    const query = new URLSearchParams()
    if (params.limit) query.append('limit', params.limit)
    if (params.offset !== undefined) query.append('offset', params.offset)
    if (params.category) query.append('category', params.category)
    return api.get(`/feed/posts${query.toString() ? `?${query.toString()}` : ''}`)
  },
  getRecommended: (limit = 20) => api.get(`/feed/posts/recommended?limit=${limit}`),
  getTrending: (days = 7, limit = 20) => api.get(`/feed/posts/trending?days=${days}&limit=${limit}`),
  getLiked: (limit = 20, offset = 0) => api.get(`/feed/posts/liked?limit=${limit}&offset=${offset}`),
  getCategories: () => api.get('/feed/categories'),
  getPostByProject: (projectId) => api.get(`/feed/posts/project/${projectId}`),
  getPostsByCreator: (userId, limit = 20, offset = 0) =>
    api.get(`/feed/posts/user/${userId}?limit=${limit}&offset=${offset}`),
  likePost: (postId) => api.post(`/feed/posts/${postId}/like`),
  unlikePost: (postId) => api.delete(`/feed/posts/${postId}/like`),
  publishProject: (projectId, payload = {}) => {
    const body = Array.isArray(payload)
      ? { media_file_ids: payload }
      : { media_file_ids: payload.media_file_ids || [], ...payload }
    return api.post(`/feed/projects/${projectId}/publish`, body)
  },
  unpublishProject: (projectId) => api.post(`/feed/projects/${projectId}/unpublish`),
  updatePost: (projectId, payload) => api.put(`/feed/projects/${projectId}/post`, payload),
  
  // Comments
  getPostComments: (postId, limit = 20, offset = 0, parent_id = null) => {
    const query = new URLSearchParams()
    query.append('limit', limit)
    query.append('offset', offset)
    if (parent_id !== null && parent_id !== undefined) query.append('parent_id', parent_id)
    return api.get(`/feed/posts/${postId}/comments?${query.toString()}`)
  },
  createComment: (postId, payload) => api.post(`/feed/posts/${postId}/comments`, payload),
  updateComment: (commentId, payload) => api.put(`/feed/comments/${commentId}`, payload),
  deleteComment: (commentId) => api.delete(`/feed/comments/${commentId}`),
  likeComment: (commentId) => api.post(`/feed/comments/${commentId}/like`),
  unlikeComment: (commentId) => api.delete(`/feed/comments/${commentId}/like`),

  getProjectDetail: (projectId) => api.get(`/feed/posts/project/${projectId}`),
  getProjectComments: (postId, limit = 50, offset = 0, parent_id = null) => {
    const query = new URLSearchParams();
    query.append('limit', limit);
    query.append('offset', offset);
    if (parent_id !== null && parent_id !== undefined) query.append('parent_id', parent_id);
    return api.get(`/feed/posts/${postId}/comments?${query.toString()}`);
  },
  likeProject: (postId) => api.post(`/feed/posts/${postId}/like`),
  unlikeProject: (postId) => api.delete(`/feed/posts/${postId}/like`),
  getProjectsByCategory: (category, limit = 20, offset = 0) => {
    const query = new URLSearchParams();
    query.append('category', category);
    query.append('limit', limit);
    query.append('offset', offset);
    return api.get(`/feed/posts?${query.toString()}`);
  },
  getCreatorProjects: (userId, limit = 20, offset = 0) =>
    api.get(`/feed/posts/user/${userId}?limit=${limit}&offset=${offset}`),
  searchUsers: (payload) => {
    const query = new URLSearchParams();
    Object.entries(payload || {}).forEach(([key, value]) => {
      if (value === undefined || value === null) return;
      if (key === 'filter' && typeof value === 'object') {
        Object.entries(value).forEach(([fk, fv]) => {
          if (fv !== undefined && fv !== null && fv !== '') query.append(fk, fv);
        });
        return;
      }
      query.append(key, value);
    });
    return api.get(`/feed/users?${query.toString()}`);
  },
};

export const searchAPI = {
  getUserFeed: (params) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        if (Array.isArray(value)) {
          value.forEach(v => query.append(key, v));
        } else {
          query.append(key, value);
        }
      }
    });
    return api.get(`/feed/users?${query.toString()}`);
  },
  searchUsers: (q, page = 1, pageSize = 20) =>
    api.get(`/search/users?q=${encodeURIComponent(q)}&page=${page}&page_size=${pageSize}`),
};

// Relationships (друзья / заявки / блокировки)
export const relationshipsAPI = {
  // заявки в друзья
  sendFriendRequest: (userId) =>
    api.post('/relationships/requests', { user_id: userId }),
  acceptFriendRequest: (userId) =>
    api.post(`/relationships/requests/${userId}/accept`),
  rejectFriendRequest: (userId) =>
    api.post(`/relationships/requests/${userId}/reject`),
  cancelFriendRequest: (userId) =>
    api.delete(`/relationships/requests/${userId}/cancel`),

  // друзья / списки
  getFriends: (offset = 0, limit = 100) =>
    api.get(`/relationships/friends?offset=${offset}&limit=${limit}`),
  removeFriend: (userId) =>
    api.delete(`/relationships/friends/${userId}`),
  getPendingRequests: (offset = 0, limit = 100) =>
    api.get(`/relationships/requests?offset=${offset}&limit=${limit}`),
  getMutualFriends: (userId, offset = 0, limit = 100) =>
    api.get(`/relationships/friends/mutual/${userId}?offset=${offset}&limit=${limit}`),

  // блокировка
  blockUser: (userId) =>
    api.post('/relationships/block', { user_id: userId }),
  unblockUser: (userId) =>
    api.post(`/relationships/unblock/${userId}`),
  getBlockedUsers: (offset = 0, limit = 100) =>
    api.get(`/relationships/blocked?offset=${offset}&limit=${limit}`),

  // статус отношений
  getRelationshipStatus: (userId) =>
    api.get(`/relationships/status/${userId}`),
};

export const chatAPI = {
  getChats: () => api.get('/chats'),

  getMessages: (chatId, limit = 50, offset = 0) =>
    api.get(`/chats/${chatId}/messages?limit=${limit}&offset=${offset}`),

  createChat: (chatData) => api.post('/chat', chatData),

  // FastAPI ожидает повторяющиеся query-параметры: user_ids=1&user_ids=2 (не user_ids[]=…)
  addUsersToChat: (chatId, userIds) => {
    const ids = Array.isArray(userIds) ? userIds : [userIds];
    const qs = ids.map((id) => `user_ids=${encodeURIComponent(id)}`).join('&');
    return api.post(`/chats/${chatId}/users${qs ? `?${qs}` : ''}`);
  },

  // Поиск сообщений в чате
  searchMessages: (chatId, query, limit = 50) =>
    api.get(`/chats/${chatId}/messages/search?query=${encodeURIComponent(query)}&limit=${limit}`),

  // Отправка текстового сообщения (REST, вместо WebSocket)
  sendTextMessage: (chatId, { content, reply_to_message_id = null, forward_message_id = null, message_type = 'text' } = {}) => {
    const body = {
      chat_id: chatId,
      content,
      message_type,
    };

    if (reply_to_message_id) {
      body.reply_to_message_id = reply_to_message_id;
    }
    if (forward_message_id) {
      body.forward_message_id = forward_message_id;
    }

    return api.post(`/chats/${chatId}/messages/text`, body);
  },

  // Отправка медиа-сообщения
  sendMediaMessage: (chatId, formData, { caption = null, reply_to_message_id = null } = {}) => {
    const params = {}
    if (caption) params.caption = caption
    if (reply_to_message_id) params.reply_to_message_id = reply_to_message_id
    return apiFile.post(`/chats/${chatId}/messages/media`, formData, { params })
  },

  // Пересылка сообщений
  forwardMessages: (chatId, { message_ids, target_chat_ids, include_original_info = true }) =>
    api.post(`/chats/${chatId}/messages/forward`, {
      message_ids,
      target_chat_ids,
      include_original_info,
    }),

  // Получение ответов на сообщение
  getMessageReplies: (chatId, messageId, limit = 50, offset = 0) =>
    api.get(`/chats/${chatId}/messages/${messageId}/replies?limit=${limit}&offset=${offset}`),

  // Прочтение
  markChatAsRead: (chatId, messageIds = [], markAll = false) => {
    const params = new URLSearchParams();

    if (Array.isArray(messageIds)) {
      messageIds.forEach((id) => {
        if (id !== undefined && id !== null) {
          params.append('message_ids', String(id));
        }
      });
    }

    params.append('mark_all', markAll ? 'true' : 'false');

    return api.post(`/chats/${chatId}/read`, null, { params });
  },

  markMessageAsRead: (messageId) => api.post(`/messages/${messageId}/read`),

  // Редактирование / удаление сообщений через REST
  editMessage: (chatId, messageId, content) =>
    api.put(`/chats/${chatId}/messages/${messageId}`, { content }),

  deleteMessage: (chatId, messageId) =>
    api.delete(`/chats/${chatId}/messages/${messageId}`),

  // Очистка истории (если реализовано на backend)
  clearChatHistory: (chatId) => api.delete(`/chats/${chatId}/messages`),

  getChatParticipants: (chatId) => api.get(`/chats/${chatId}/participants`),

  removeUserFromChat: (chatId, userId) =>
    api.delete(`/chats/${chatId}/users/${userId}`),

  likeMessage: (chatId, messageId) =>
    api.post(`/chats/${chatId}/messages/${messageId}/like`),

  unlikeMessage: (chatId, messageId) =>
    api.post(`/chats/${chatId}/messages/${messageId}/unlike`),
};

export const channelAPI = {
  getMyChannels: ( limit = 100, offset = 0) => 
    api.get(`/channels/my?limit=${limit}&offset=${offset}`),
  getMyAdminChannels: (limit = 100, offset = 0) =>
    api.get(`/channels/admin/channels?limit=${limit}&offset=${offset}`),
  getProjectChannel: (projectId) => api.get(`/channels/project/${projectId}`),
  createChannel: (payload) => api.post('/channels', payload),
  getChannel: (channelId) => api.get(`/channels/${channelId}`),
  updateChannel: (channelId, payload) => api.put(`/channels/${channelId}`, payload),
  deleteChannel: (channelId) => api.delete(`/channels/${channelId}`),
  subscribe: (channelId) => api.post(`/channels/${channelId}/subscribe`),
  unsubscribe: (channelId) => api.post(`/channels/${channelId}/unsubscribe`),
  getMessages: (channelId, limit = 50, offset = 0) =>
    api.get(`/channels/${channelId}/messages?limit=${limit}&offset=${offset}`),
  sendTextMessage: (channelId, content) =>
    api.post(`/channels/${channelId}/messages/text`, null, {
      params: { content },
    }),
  sendMediaMessage: (channelId, formData, { caption = null } = {}) => {
    const params = {}
    if (caption) params.caption = caption
    return apiFile.post(`/channels/${channelId}/messages/media`, formData, { params })
  },
  likeMessage: (channelId, messageId) =>
    api.post(`/channels/${channelId}/messages/${messageId}/like`),
  unlikeMessage: (channelId, messageId) =>
    api.post(`/channels/${channelId}/messages/${messageId}/unlike`),
};

// Announcements API
export const announcementsAPI = {
  createAnnouncement: (projectId, workspaceId, data) =>
    api.post(`/projects/${projectId}/workspaces/${workspaceId}/announcements`, data),
  getWorkspaceAnnouncements: (projectId, workspaceId, params = {}) => {
    const query = new URLSearchParams();
    if (params.skip !== undefined) query.append('skip', params.skip);
    if (params.limit !== undefined) query.append('limit', params.limit);
    if (params.status) query.append('status', params.status);
    return api.get(`/projects/${projectId}/workspaces/${workspaceId}/announcements?${query.toString()}`);
  },
  getGlobalAnnouncements: (params = {}) => {
    const query = new URLSearchParams();
    if (params.skip !== undefined) query.append('skip', params.skip);
    if (params.limit !== undefined) query.append('limit', params.limit);
    if (params.project_id) query.append('project_id', params.project_id);
    if (params.workspace_id) query.append('workspace_id', params.workspace_id);
    if (params.status) query.append('status', params.status);
    return api.get(`/projects/announcements/feed?${query.toString()}`);
  },
  getAnnouncement: (announcementId) =>
    api.get(`/projects/announcements/${announcementId}`),
  updateAnnouncement: (announcementId, data) =>
    api.patch(`/projects/announcements/${announcementId}`, data),
  deleteAnnouncement: (announcementId) =>
    api.delete(`/projects/announcements/${announcementId}`),
  
  // Applications (Заявки на объявления)
  createApplication: (announcementId, data) =>
    api.post(`/projects/announcements/${announcementId}/applications`, data),
  getAnnouncementApplications: (announcementId, params = {}) => {
    const query = new URLSearchParams();
    if (params.skip !== undefined) query.append('skip', params.skip);
    if (params.limit !== undefined) query.append('limit', params.limit);
    if (params.status) query.append('status', params.status);
    return api.get(`/projects/announcements/${announcementId}/applications?${query.toString()}`);
  },
  getMyApplications: (params = {}) => {
    const query = new URLSearchParams();
    if (params.skip !== undefined) query.append('skip', params.skip);
    if (params.limit !== undefined) query.append('limit', params.limit);
    return api.get(`/projects/applications/my?${query.toString()}`);
  },
  getApplication: (applicationId) =>
    api.get(`/projects/applications/${applicationId}`),
  updateApplication: (applicationId, data) =>
    api.patch(`/projects/applications/${applicationId}`, data),
  deleteApplication: (applicationId) =>
    api.delete(`/projects/applications/${applicationId}`),
  updateApplicationStatus: (applicationId, status) =>
    api.patch(`/projects/applications/${applicationId}/status`, null, { params: { status } }),
  voteApplication: (applicationId, voteType) =>
    api.post(`/projects/applications/${applicationId}/vote`, { vote_type: voteType }),
};

// Files API (Global)
export const filesAPI = {
  uploadFile: (file, fileType, metadata = null, isPublic = false) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('file_type', fileType);
    if (metadata) formData.append('metadata', JSON.stringify(metadata));
    formData.append('public', isPublic);
    return apiFile.post('/files/upload', formData);
  },
  uploadMultipleFiles: (files, fileType, metadata = null, isPublic = false) => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    formData.append('file_type', fileType);
    if (metadata) formData.append('metadata', JSON.stringify(metadata));
    formData.append('public', isPublic);
    return apiFile.post('/files/upload-multiple', formData);
  },
  getFileInfo: (fileId) => api.get(`/files/${fileId}`),
  deleteFile: (fileId) => api.delete(`/files/${fileId}`),
  getFileUrl: (fileId, expiresIn = 3600) => api.get(`/files/${fileId}/url?expires_in=${expiresIn}`),
  getMyFiles: (fileType = null, limit = 100) => {
    const query = new URLSearchParams();
    if (fileType) query.append('file_type', fileType);
    query.append('limit', limit);
    return api.get(`/files/user/my-files?${query.toString()}`);
  },
};

export default api;