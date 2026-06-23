import { useEffect, useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { DeadlineCalendar } from "./DeadlineCalendar";
import { FileCard } from "./FileCard";
import { KanbanBoard } from "./KanbanBoard";
import { ProjectChat } from "./ProjectChat";
import { GoPlus } from "react-icons/go";
import { LinksSection } from "./SilkiProj";
import { FiX, FiSettings, FiPlus, FiSearch } from "react-icons/fi";
import {
  fetchProjectFiles,
  uploadProjectFile,
  deleteProjectFile,
  updateWorkspace,
  fetchProject,
  fetchWorkspaceParticipants,
  addWorkspaceParticipants,
} from "../../../store/slices/projects";
import { useUserSearch } from "../../../hooks/useUserSearch";
import { normalizeAssetUrl, projectsAPI } from "../../../services/api";

// Страница рабочего пространства проекта
export default function ProjectWorkspace({
  workspace,
  project,
  tasks = [],
}) {
  const dispatch = useDispatch();
  const fileInputRef = useRef(null);

  const {
    projectFiles = [],
    projectFilesLoading,
    projectFilesError,
    uploadFileLoading,
  } = useSelector((state) => state.projects);
  console.log(projectFiles); // Это массив!

  const projectId = project?.id;
  const workspaceId = workspace?.id;

  useEffect(() => {
    if (!projectId) return;
    if (!workspaceId) return;
    dispatch(
      fetchProjectFiles({
        projectId,
        workspaceId,
        limit: 100,
        offset: 0,
      })
    );
  }, [dispatch, projectId, workspaceId]);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileSelect = async (e) => {
    const input = e.target;
    const selectedFile = input?.files?.[0];
    if (!selectedFile || !projectId || !workspaceId) return;

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("workspace_id", workspaceId);

    try {
      await dispatch(
        uploadProjectFile({ projectId, workspaceId, formData })
      ).unwrap();
      input.value = "";
    } catch (err) {
      console.error("Ошибка загрузки файла:", err);
    }
  };

  const handleDownload = async (file) => {
    if (!file?.id || !projectId || !workspaceId) return;
    try {
      let downloadUrl = normalizeAssetUrl(file.download_url);
      if (!downloadUrl) {
        const { data } = await projectsAPI.getProjectFileDownloadUrl(projectId, workspaceId, file.id);
        downloadUrl = normalizeAssetUrl(data?.url);
      }
      if (!downloadUrl) {
        throw new Error("Download URL is missing");
      }

      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = file.original_filename || "file";
      a.target = "_blank";
      a.rel = "noreferrer";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (err) {
      console.error("Ошибка скачивания файла:", err);
    }
  };

  const handleDelete = async (file) => {
    if (!file?.id || !projectId || !workspaceId) return;
    if (!window.confirm(`Удалить файл «${file.original_filename}»?`)) return;
    try {
      await dispatch(
        deleteProjectFile({ projectId, workspaceId, fileId: file.id })
      ).unwrap();
    } catch (err) {
      console.error("Ошибка удаления файла:", err);
    }
  };
  
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [saving, setSaving] = useState(false);

  const workspaceData = workspace || {
    name: "Рабочее пространство",
    description: "Описание рабочего пространства",
  };

  const projectData = project || {
    name: "Проект",
    description: "Описание проекта",
  };

  const normalizeLink = (item) => {
    if (typeof item === "string") return { name: item, link: item };
    return {
      name: item?.name ?? item?.title ?? "Ссылка",
      link: item?.link ?? item?.url ?? "",
    };
  };

  const workspaceLinksList = (workspace?.links || []).map(normalizeLink).filter((l) => l.link);

  const openSettingsModal = () => {
    setEditName(workspaceData.name);
    setEditDescription(workspaceData.description || "");
    setShowSettingsModal(true);
  };

  const handleSaveSettings = async () => {
    setSaving(true);
    try {
      if (workspaceId) {
        await dispatch(
          updateWorkspace({
            projectId,
            workspaceId,
            workspaceData: { name: editName, description: editDescription || null },
          })
        ).unwrap();
      }
      if (projectId) dispatch(fetchProject(projectId));
      setShowSettingsModal(false);
    } catch (err) {
      console.error("Ошибка сохранения настроек:", err);
    } finally {
      setSaving(false);
    }
  };

  const [showAddLinkForm, setShowAddLinkForm] = useState(false);
  const [newLinkUrl, setNewLinkUrl] = useState("");

  const handleAddWorkspaceLink = async () => {
    const url = newLinkUrl.trim();
    if (!url || !workspaceId) return;
    const current = (workspace?.links || []).map((l) => (typeof l === "string" ? l : l?.link || l?.url)).filter(Boolean);
    const updated = [...current, url];
    try {
      await dispatch(
        updateWorkspace({ projectId, workspaceId, workspaceData: { links: updated } })
      ).unwrap();
      if (projectId) dispatch(fetchProject(projectId));
      setNewLinkUrl("");
      setShowAddLinkForm(false);
    } catch (err) {
      console.error("Ошибка добавления ссылки:", err);
    }
  };

  const handleRemoveWorkspaceLink = async (index) => {
    const current = (workspace?.links || []).map((l) => (typeof l === "string" ? l : l?.link || l?.url)).filter(Boolean);
    const updated = current.filter((_, i) => i !== index);
    try {
      await dispatch(
        updateWorkspace({ projectId, workspaceId, workspaceData: { links: updated } })
      ).unwrap();
      if (projectId) dispatch(fetchProject(projectId));
    } catch (err) {
      console.error("Ошибка удаления ссылки:", err);
    }
  };

  const { profile } = useSelector((state) => state.profile);
  const currentUserId = profile?.user_id;
  const projectParticipant = project?.participants?.find((p) => p.user_id === currentUserId);
  const canManageWorkspace = ["owner", "admin", "editor"].includes(projectParticipant?.status);

  const participants = workspace?.participants || [];

  const [showInviteModal, setShowInviteModal] = useState(false);
  const [selectedUsers, setSelectedUsers] = useState([]);
  const { searchQuery, setSearchQuery, results, isSearching, error: searchError, searchUsers, clearSearch } =
    useUserSearch(currentUserId);

  useEffect(() => {
    if (searchQuery) searchUsers(searchQuery);
  }, [searchQuery, searchUsers]);

  const existingWorkspaceIds = participants.map((p) => p.user_id);
  const projectParticipantsNotInWorkspace =
    project?.participants?.filter((p) => !existingWorkspaceIds.includes(p.user_id)) || [];
  const availableUsers = searchQuery.trim()
    ? results.filter(
        (u) => !existingWorkspaceIds.includes(u.user_id) && projectParticipantsNotInWorkspace.some((pp) => pp.user_id === u.user_id)
      )
    : projectParticipantsNotInWorkspace.map((pp) => ({
        user_id: pp.user_id,
        name: pp.user_profile?.name,
        lastname: pp.user_profile?.lastname,
        username: pp.user_profile?.username,
        avatar_path: pp.user_profile?.avatar_path,
      }));

  const handleAddWorkspaceParticipants = async () => {
    if (selectedUsers.length === 0 || !workspaceId) return;
    try {
      const userIds = selectedUsers.map((u) => u.user_id);
      await dispatch(addWorkspaceParticipants({ projectId, workspaceId, userIds, privileges: [] })).unwrap();
      dispatch(fetchWorkspaceParticipants({ projectId, workspaceId }));
      setSelectedUsers([]);
      setShowInviteModal(false);
      clearSearch();
    } catch (err) {
      console.error("Ошибка приглашения в пространство:", err);
    }
  };

  return (
    <div className="bg-gradient-to-b from-gray-950 via-gray-900 to-black min-h-screen py-4">
      {/* Хедер рабочего пространства */}
      <div className="bg-gray-900/90 rounded-2xl p-6 mb-6 border border-gray-800 shadow-lg shadow-purple-900/20">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">
              Рабочее пространство проекта
            </p>
            <h1 className="text-2xl md:text-3xl font-bold text-white">
              {workspaceData.name}
            </h1>
            <p className="text-gray-400 mt-2 max-w-2xl">
              {workspaceData.description ||
                projectData.description ||
                "Описание рабочего пространства"}
            </p>
          </div>
          <div className="flex flex-wrap gap-3 justify-start md:justify-end">
            {canManageWorkspace && (
              <button
                onClick={() => setShowInviteModal(true)}
                className="bg-purple-600 px-4 py-2 rounded-xl text-white hover:bg-purple-700 transition-colors text-sm flex items-center gap-2"
              >
                <FiPlus size={16} />
                Пригласить в пространство
              </button>
            )}
            <button
              onClick={openSettingsModal}
              className="bg-gray-800 px-4 py-2 rounded-xl text-white hover:bg-gray-700 transition-colors text-sm flex items-center gap-2"
            >
              <FiSettings size={16} />
              Настройки пространства
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Основная колонка */}
        <div className="xl:col-span-2 space-y-6">
          {/* Канбан-доска задач */}
          <KanbanBoard
            tasks={tasks}
            workspaceId={workspaceData.id}
            projectId={project?.id}
            workspace={workspace}
          />

          {/* Файлы проекта */}
          <div className="bg-gray-900/85 rounded-2xl p-6 border border-gray-800">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <h3 className="text-xl text-white font-semibold">
                  Файлы проекта
                </h3>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                onChange={handleFileSelect}
                multiple={false}
              />
              <button
                onClick={handleUploadClick}
                disabled={uploadFileLoading || !projectId}
                className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-gray-800 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed text-xs text-gray-200 transition-colors"
              >
                <GoPlus className="w-4 h-4" />
                {uploadFileLoading ? "Загрузка…" : "Загрузить файл"}
              </button>
            </div>
            {projectFilesError && (
              <p className="text-red-400 text-sm mb-4">
                {typeof projectFilesError === "string"
                  ? projectFilesError
                  : projectFilesError?.detail || "Ошибка загрузки списка файлов"}
              </p>
            )}
            {projectFilesLoading ? (
              <p className="text-gray-400 text-sm">Загрузка файлов…</p>
            ) : !projectFiles || projectFiles.length === 0 ? (
              <p className="text-gray-500 text-sm">Файлов пока нет. Загрузите первый файл.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* ✅ ИСПРАВЛЕНО: projectFiles - это массив, а не объект с полем files */}
                {(projectFiles || []).map((f) => (
                  <FileCard
                    key={f.id}
                    file={f}
                    onDownload={handleDownload}
                    onDelete={handleDelete}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Инструменты и ссылки (workspace: Miro, Figma и т.д.) */}
          <div className="bg-gray-900/85 rounded-2xl p-6 border border-gray-800">
            <LinksSection
              links={workspace?.links || []}
              onAddLink={() => setShowAddLinkForm(true)}
              onRemoveLink={handleRemoveWorkspaceLink}
            />
          </div>
        </div>

        {/* Боковая панель */}
        <div className="space-y-6">
          <ProjectChat workspace={workspace} project={project} />
          <DeadlineCalendar tasks={tasks || []} workspaceId={workspaceId} projectId={projectId} />

        {/* Участники пространства */}
        <div className="bg-gray-900/85 rounded-2xl p-6 border border-gray-800">
          <h3 className="text-xl font-bold text-white mb-4">
            Участники пространства
          </h3>
          {!participants || participants.length === 0 ? (
            <p className="text-sm text-gray-500">
              В это пространство пока никого не пригласили. Добавьте участников проекта.
            </p>
          ) : (
            <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
              {(participants || []).map((participant) => {
                const profile = participant.user_profile || participant;
                const name = `${profile.name || ""} ${
                  profile.lastname || ""
                }`.trim();
                const initials = (profile.name?.[0] || "U").toUpperCase();

                return (
                  <div
                    key={participant.id || profile.user_id}
                    className="flex items-center justify-between bg-gray-800/70 rounded-xl px-3 py-2.5"
                  >
                    <div className="flex items-center gap-3">
                      {normalizeAssetUrl(profile.avatar_url || profile.avatar_path) ? (
                        <img
                          src={normalizeAssetUrl(profile.avatar_url || profile.avatar_path)}
                          alt={name}
                          className="w-8 h-8 rounded-full object-cover"
                        />
                      ) : (
                        <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-white text-sm font-semibold">
                          {initials}
                        </div>
                      )}
                      <div>
                        <p className="text-sm text-white font-medium">
                          {name || "Участник"}
                        </p>
                        {profile.username && (
                          <p className="text-xs text-gray-400">
                            @{profile.username}
                          </p>
                        )}
                      </div>
                    </div>
                    {participant.status && (
                      <span className="text-xs px-2 py-1 rounded-full bg-gray-800 text-gray-300 border border-gray-700">
                        {participant.status === "owner"
                          ? "Владелец"
                          : participant.status === "admin"
                          ? "Администратор"
                          : participant.status === "editor"
                          ? "Редактор"
                          : "Участник"}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          )}
</div>
        </div>
      </div>
      

      {/* Модальное окно настроек workspace */}
      {showSettingsModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 rounded-2xl border border-gray-700 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-700 flex items-center justify-between sticky top-0 bg-gray-900 z-10">
              <h2 className="text-xl font-bold text-white">
                Настройки пространства
              </h2>
              <button
                onClick={() => setShowSettingsModal(false)}
                className="p-2 hover:bg-gray-800 rounded-lg text-gray-400 hover:text-white"
              >
                <FiX size={20} />
              </button>
            </div>

            <div className="p-6 space-y-6">
              <div>
                <label className="block text-gray-300 text-sm font-medium mb-2">
                  Название пространства
                </label>
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-white"
                />
              </div>
              <div>
                <label className="block text-gray-300 text-sm font-medium mb-2">
                  Описание
                </label>
                <textarea
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  rows={3}
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-white resize-none"
                />
              </div>
            </div>

            <div className="p-6 border-t border-gray-700 flex gap-3">
              <button
                onClick={handleSaveSettings}
                disabled={saving}
                className="flex-1 px-4 py-3 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-xl font-medium"
              >
                {saving ? "Сохранение…" : "Сохранить"}
              </button>
              <button
                onClick={() => setShowSettingsModal(false)}
                className="px-4 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-xl"
              >
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Модалка приглашения в пространство */}
      {showInviteModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 rounded-2xl border border-gray-700 w-full max-w-md max-h-[90vh] overflow-hidden flex flex-col">
            <div className="p-6 border-b border-gray-700 flex items-center justify-between">
              <h3 className="text-lg font-bold text-white">Пригласить в пространство</h3>
              <button
                onClick={() => {
                  setShowInviteModal(false);
                  setSelectedUsers([]);
                  clearSearch();
                }}
                className="p-2 hover:bg-gray-800 rounded-lg text-gray-400 hover:text-white"
              >
                <FiX size={20} />
              </button>
            </div>
            <div className="p-4 border-b border-gray-700">
              <div className="relative">
                <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                <input
                  type="text"
                  placeholder="Поиск участников проекта..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm"
                />
              </div>
              <p className="text-gray-500 text-xs mt-1">Только участники проекта</p>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {isSearching && <p className="text-gray-400 text-sm">Поиск...</p>}
              {searchError && <p className="text-red-400 text-sm">{searchError}</p>}
              {availableUsers.length === 0 ? (
                <p className="text-gray-500 text-sm">
                  {projectParticipantsNotInWorkspace.length === 0
                    ? "Все участники проекта уже в пространстве"
                    : "Никого не найдено"}
                </p>
              ) : (
                <div className="space-y-1">
                  {availableUsers.map((user) => {
                    const isSelected = selectedUsers.some((u) => u.user_id === user.user_id);
                    const name = `${user.name || ""} ${user.lastname || ""}`.trim() || "Участник";
                    return (
                      <div
                        key={user.user_id}
                        onClick={() => {
                          if (isSelected) {
                            setSelectedUsers((prev) => prev.filter((u) => u.user_id !== user.user_id));
                          } else {
                            setSelectedUsers((prev) => [...prev, user]);
                          }
                        }}
                        className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
                          isSelected ? "bg-purple-900/40" : "hover:bg-gray-800"
                        }`}
                      >
                        {normalizeAssetUrl(user.avatar_url || user.avatar_path) ? (
                          <img src={normalizeAssetUrl(user.avatar_url || user.avatar_path)} alt={name} className="w-9 h-9 rounded-full object-cover" />
                        ) : (
                          <div className="w-9 h-9 rounded-full bg-purple-600 flex items-center justify-center text-white text-sm font-semibold">
                            {(user.name?.[0] || "U").toUpperCase()}
                          </div>
                        )}
                        <div className="flex-1 min-w-0">
                          <p className="text-white text-sm font-medium truncate">{name}</p>
                          {user.username && <p className="text-gray-400 text-xs">@{user.username}</p>}
                        </div>
                        {isSelected && <span className="text-purple-400 text-sm">✓</span>}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
            <div className="p-4 border-t border-gray-700 flex gap-3">
              <button
                onClick={handleAddWorkspaceParticipants}
                disabled={selectedUsers.length === 0}
                className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-xl text-sm font-medium"
              >
                Пригласить {selectedUsers.length > 0 ? `(${selectedUsers.length})` : ""}
              </button>
              <button
                onClick={() => {
                  setShowInviteModal(false);
                  setSelectedUsers([]);
                  clearSearch();
                }}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-xl text-sm"
              >
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Модалка добавления ссылки (Инструменты и ссылки) */}
      {showAddLinkForm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 rounded-2xl border border-gray-700 w-full max-w-md p-6">
            <h3 className="text-lg font-bold text-white mb-4">Добавить ссылку</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-gray-400 text-sm mb-1">URL (Miro, Figma и т.д.)</label>
                <input
                  type="url"
                  value={newLinkUrl}
                  onChange={(e) => setNewLinkUrl(e.target.value)}
                  placeholder="https://..."
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm"
                />
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button
                onClick={handleAddWorkspaceLink}
                disabled={!newLinkUrl.trim()}
                className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-xl text-sm"
              >
                Добавить
              </button>
              <button
                onClick={() => {
                  setShowAddLinkForm(false);
                  setNewLinkUrl("");
                }}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-xl text-sm"
              >
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}