import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import Header from '../../ui/Header';
import ProjectWorkspace from './Project/ProjectWorkspace';
import {
  fetchProject,
  fetchTasks,
  fetchWorkspaceParticipants,
  setCurrentWorkspace,
} from '../../store/slices/projects';

export default function WorkspaceDetail() {
  const { projectId, workspaceId } = useParams();
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const {
    currentProject,
    currentWorkspace,
    tasks,
    isLoading,
    workspaceLoading,
    taskLoading,
    error,
  } = useSelector((state) => state.projects);

  // Загружаем проект
  useEffect(() => {
    if (projectId) {
      dispatch(fetchProject(projectId));
    }
  }, [dispatch, projectId]);

  // Выбираем текущее рабочее пространство из проекта
  useEffect(() => {
    if (!currentProject?.workspaces || !workspaceId) return;

    const workspace =
      currentProject.workspaces.find(              
        (w) => String(w.id) === String(workspaceId)
      ) || null;      

    if (workspace) {
      dispatch(setCurrentWorkspace(workspace));
    }
  }, [currentProject, workspaceId, dispatch]);

  // Загружаем задачи рабочей области
  useEffect(() => {
    if (!workspaceId) return;
    if (!projectId) return;
    dispatch(fetchTasks({ projectId, workspaceId, params: {} }));
  }, [dispatch, projectId, workspaceId]);

  // Загружаем участников workspace (backend: GET /projects/{project_id}/workspaces/{workspace_id}/participants)
  useEffect(() => {
    if (!workspaceId) return;
    if (!projectId) return;
    dispatch(fetchWorkspaceParticipants({ projectId, workspaceId }));
  }, [dispatch, projectId, workspaceId]);

  const loading = isLoading || workspaceLoading || taskLoading;

  // Состояние загрузки
  if (loading && !currentProject) {
    return (
      <Header>
        <div className="max-w-6xl mx-auto">
          <div className="text-center py-8 text-gray-400">
            <p>Загрузка рабочего пространства...</p>
          </div>
        </div>
      </Header>
    );
  }

  // Обработка ошибок
  if (error) {
    return (
      <Header>
        <div className="max-w-6xl mx-auto">
          <div className="text-center py-8 text-red-400">
            <p>Ошибка загрузки рабочего пространства</p>
            <p className="text-sm mt-2">
              {typeof error === 'string'
                ? error
                : error.detail || 'Попробуйте обновить страницу'}
            </p>
            <button
              onClick={() => navigate(`/projects/${projectId}`)}
              className="mt-4 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
            >
              Вернуться к проекту
            </button>
          </div>
        </div>
      </Header>
    );
  }

  if (!currentProject) {
    return (
      <Header>
        <div className="max-w-6xl mx-auto">
          <div className="text-center py-8 text-gray-400">
            <p>Проект не найден</p>
            <button
              onClick={() => navigate('/projects')}
              className="mt-4 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
            >
              Вернуться к проектам
            </button>
          </div>
        </div>
      </Header>
    );
  }

  if (!currentWorkspace) {
    return (
      <Header>
        <div className="max-w-6xl mx-auto">
          <div className="text-center py-8 text-gray-400">
            <p>Рабочее пространство не найдено</p>
            <button
              onClick={() => navigate(`/projects/${projectId}`)}
              className="mt-4 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
            >
              Вернуться к проекту
            </button>
          </div>
        </div>
      </Header>
    );
  }

  return (
    <Header>
      <div className=" mx-auto py-6">
        <ProjectWorkspace
          workspace={currentWorkspace}
          project={currentProject}
          tasks={tasks}
        />
      </div>
    </Header>
  );
}

