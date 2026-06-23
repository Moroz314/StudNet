import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { projectsAPI } from '../../services/api';

export const createProject = createAsyncThunk(
  'projects/createProject',
  async (projectData, { rejectWithValue }) => {
    try {
      const response = await projectsAPI.createProject(projectData);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const fetchProjects = createAsyncThunk(
  'projects/fetchProjects',
  async (params = {}, { rejectWithValue }) => {
    try {
      const response = await projectsAPI.getProjects(params);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const fetchProject = createAsyncThunk(
  'projects/fetchProject',
  async (projectId, { rejectWithValue }) => {
    try {
      const response = await projectsAPI.getProject(projectId);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const updateProject = createAsyncThunk(
  'projects/updateProject',
  async ({ projectId, projectData }, { rejectWithValue }) => {
    try {
      const response = await projectsAPI.updateProject(projectId, projectData);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const deleteProject = createAsyncThunk(
  'projects/deleteProject',
  async (projectId, { rejectWithValue }) => {
    try {
      await projectsAPI.deleteProject(projectId);
      return projectId;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

// Workspace actions
export const createWorkspace = createAsyncThunk(
  'projects/createWorkspace',
  async ({ projectId, workspaceData }, { rejectWithValue }) => {
    try {
      const response = await projectsAPI.createWorkspace(projectId, workspaceData);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const fetchWorkspaces = createAsyncThunk(
  'projects/fetchWorkspaces',
  async (projectId, { rejectWithValue }) => {
    try {
      const response = await projectsAPI.getWorkspaces(projectId);
      return { projectId, workspaces: response.data };
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const updateWorkspace = createAsyncThunk(
  'projects/updateWorkspace',
  async ({ projectId, workspaceId, workspaceData }, { rejectWithValue }) => {
    try {
      const response = await projectsAPI.updateWorkspace(projectId, workspaceId, workspaceData);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const deleteWorkspace = createAsyncThunk(
  'projects/deleteWorkspace',
  async (workspaceId, { rejectWithValue }) => {
    try {
      await projectsAPI.deleteWorkspace(workspaceId);
      return workspaceId;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

// Participant actions
export const addProjectParticipants = createAsyncThunk(
  'projects/addProjectParticipants',
  async ({ projectId, userIds }, { rejectWithValue }) => {
    try {
      const response = await projectsAPI.addProjectParticipants(projectId, userIds);
      return { projectId, participants: response.data };
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

// Invitations (new flow for adding people to project)
export const createProjectInvitations = createAsyncThunk(
  'projects/createProjectInvitations',
  async (
    { projectId, userIds, role = null, permission_level = null, message = null },
    { rejectWithValue }
  ) => {
    try {
      const payload = { user_ids: userIds };
      if (role) payload.role = role;
      if (permission_level) payload.permission_level = permission_level;
      if (message) payload.message = message;
      const response = await projectsAPI.createProjectInvitations(projectId, payload);
      return { projectId, invitations: response.data };
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const fetchProjectParticipants = createAsyncThunk(
  'projects/fetchProjectParticipants',
  async (projectId, { rejectWithValue }) => {
    try {
      const response = await projectsAPI.getProjectParticipants(projectId);
      return { projectId, participants: response.data };
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const updateParticipantStatus = createAsyncThunk(
  'projects/updateParticipantStatus',
  async ({ projectId, participantUserId, status }, { rejectWithValue }) => {
    try {
      const response = await projectsAPI.updateParticipantStatus(projectId, participantUserId, status);
      return { projectId, participant: response.data };
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const addWorkspaceParticipants = createAsyncThunk(
  'projects/addWorkspaceParticipants',
  async ({ projectId, workspaceId, userIds, privileges = [] }, { rejectWithValue }) => {
    try {
      const response = await projectsAPI.addWorkspaceParticipants(projectId, workspaceId, userIds, privileges);
      return { workspaceId, participants: response.data };
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const fetchWorkspaceParticipants = createAsyncThunk(
  'projects/fetchWorkspaceParticipants',
  async ({ projectId, workspaceId }, { rejectWithValue }) => {
    try {
      const response = await projectsAPI.getWorkspaceParticipants(projectId, workspaceId);
      return { workspaceId, participants: response.data };
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const removeWorkspaceParticipant = createAsyncThunk(
  'projects/removeWorkspaceParticipant',
  async ({ projectId, workspaceId, participantUserId }, { rejectWithValue }) => {
    try {
      await projectsAPI.removeWorkspaceParticipant(projectId, workspaceId, participantUserId);
      return { workspaceId, participantUserId };
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const leaveProject = createAsyncThunk(
  'projects/leaveProject',
  async (projectId, { rejectWithValue }) => {
    try {
      await projectsAPI.leaveProject(projectId);
      return projectId;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

// Task actions
export const createTask = createAsyncThunk(
  'projects/createTask',
  async ({ projectId, workspaceId, taskData }, { rejectWithValue }) => {
    try {
      const response = await projectsAPI.createTask(projectId, workspaceId, taskData);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const fetchTasks = createAsyncThunk(
  'projects/fetchTasks',
  async ({ projectId, workspaceId, params }, { rejectWithValue }) => {
    try {
      const response = await projectsAPI.getTasks(projectId, workspaceId, params);
      return { workspaceId, tasks: response.data };
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const fetchTask = createAsyncThunk(
  'projects/fetchTask',
  async ({ projectId, workspaceId, taskId }, { rejectWithValue }) => {
    try {
      const response = await projectsAPI.getTask(projectId, workspaceId, taskId);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const updateTask = createAsyncThunk(
  'projects/updateTask',
  async ({ projectId, workspaceId, taskId, taskData }, { rejectWithValue }) => {
    try {
      const response = await projectsAPI.updateTask(projectId, workspaceId, taskId, taskData);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const deleteTask = createAsyncThunk(
  'projects/deleteTask',
  async ({ projectId, workspaceId, taskId }, { rejectWithValue }) => {
    try {
      await projectsAPI.deleteTask(projectId, workspaceId, taskId);
      return { workspaceId, taskId };
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const fetchUpcomingDeadlines = createAsyncThunk(
  'projects/fetchUpcomingDeadlines',
  async ({ projectId, workspaceId, days_ahead }, { rejectWithValue }) => {
    try {
      const response = await projectsAPI.getUpcomingDeadlines(projectId, workspaceId, days_ahead);
      return { workspaceId, deadlines: response.data };
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const fetchTaskComments = createAsyncThunk(
  'projects/fetchTaskComments',
  async ({ projectId, workspaceId, taskId, limit, offset }, { rejectWithValue }) => {
    try {
      const response = await projectsAPI.getTaskComments(projectId, workspaceId, taskId, limit, offset);
      return { workspaceId, taskId, comments: response.data };
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const addTaskComment = createAsyncThunk(
  'projects/addTaskComment',
  async ({ projectId, workspaceId, taskId, commentData }, { rejectWithValue }) => {
    try {
      const response = await projectsAPI.addTaskComment(projectId, workspaceId, taskId, commentData);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const updateTaskComment = createAsyncThunk(
  'projects/updateTaskComment',
  async ({ projectId, workspaceId, commentId, commentData }, { rejectWithValue }) => {
    try {
      const response = await projectsAPI.updateTaskComment(projectId, workspaceId, commentId, commentData);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const deleteTaskComment = createAsyncThunk(
  'projects/deleteTaskComment',
  async ({ projectId, workspaceId, commentId }, { rejectWithValue }) => {
    try {
      await projectsAPI.deleteTaskComment(projectId, workspaceId, commentId);
      return { workspaceId, commentId };
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const fetchWorkspaceStatistics = createAsyncThunk(
  'projects/fetchWorkspaceStatistics',
  async ({ projectId, workspaceId, startDate, endDate }, { rejectWithValue }) => {
    try {
      const response = await projectsAPI.getWorkspaceStatistics(projectId, workspaceId, startDate, endDate);
      return { workspaceId, statistics: response.data };
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const fetchStatisticsHistory = createAsyncThunk(
  'projects/fetchStatisticsHistory',
  async ({ projectId, workspaceId, days }, { rejectWithValue }) => {
    try {
      const response = await projectsAPI.getStatisticsHistory(projectId, workspaceId, days);
      return { workspaceId, history: response.data };
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

// Project Files (S3) actions
export const fetchProjectFiles = createAsyncThunk(
  'projects/fetchProjectFiles',
  async ({ projectId, workspaceId, limit = 100, offset = 0 }, { rejectWithValue }) => {
    try {
      const response = await projectsAPI.listProjectFiles(projectId, workspaceId, {
        limit,
        offset,
      });
      return { projectId, workspaceId, files: response.data?.files ?? [] };
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const uploadProjectFile = createAsyncThunk(
  'projects/uploadProjectFile',
  async ({ projectId, workspaceId, formData }, { rejectWithValue }) => {
    try {
      const response = await projectsAPI.uploadProjectFile(projectId, workspaceId, formData);
      return { projectId, file: response.data };
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const deleteProjectFile = createAsyncThunk(
  'projects/deleteProjectFile',
  async ({ projectId, workspaceId, fileId }, { rejectWithValue }) => {
    try {
      await projectsAPI.deleteProjectFile(projectId, workspaceId, fileId);
      return { projectId, fileId };
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

const projectsSlice = createSlice({
  name: 'projects',
  initialState: {
    projects: [],
    currentProject: null,
    workspaces: [],
    currentWorkspace: null,
    tasks: [],
    currentTask: null,
    taskComments: [],
    taskCommentsLoading: false,
    projectFiles: [],
    projectFilesLoading: false,
    projectFilesError: null,
    uploadFileLoading: false,
    isLoading: false,
    error: null,
    createLoading: false,
    workspaceLoading: false,
    taskLoading: false,
    invitationLoading: false,
  },
  reducers: {
    clearProjectsError: (state) => {
      state.error = null;
    },
    clearCurrentProject: (state) => {
      state.currentProject = null;
    },
    setCurrentWorkspace: (state, action) => {
      state.currentWorkspace = action.payload;
    },
    clearCurrentTask: (state) => {
      state.currentTask = null;
    },
    clearTaskComments: (state) => {
      state.taskComments = [];
    },
    clearProjectFiles: (state) => {
      state.projectFiles = [];
    },
  },
  extraReducers: (builder) => {
    builder
      // Create project
      .addCase(createProject.pending, (state) => {
        state.createLoading = true;
        state.error = null;
      })
      .addCase(createProject.fulfilled, (state, action) => {
        state.createLoading = false;
        // Преобразуем ProjectResponse в ProjectListResponse для списка
        const projectListItem = {
          id: action.payload.id,
          name: action.payload.name,
          description: action.payload.description,
          status: action.payload.status,
          created_at: action.payload.created_at,
          updated_at: action.payload.updated_at,
          participant_count:
            action.payload.participants_count ??
            action.payload.participants?.length ??
            0,
          unread_messages_count: 0
        };
        state.projects.unshift(projectListItem);
        state.error = null;
      })
      .addCase(createProject.rejected, (state, action) => {
        state.createLoading = false;
        state.error = action.payload;
      })
      // Fetch projects
      .addCase(fetchProjects.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchProjects.fulfilled, (state, action) => {
        state.isLoading = false;
        state.projects = action.payload;
        state.error = null;
      })
      .addCase(fetchProjects.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })
      // Fetch single project
      .addCase(fetchProject.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchProject.fulfilled, (state, action) => {
        state.isLoading = false;
        // Preserve participants list if it was loaded separately
        const prev = state.currentProject;
        if (prev?.id && prev.id === action.payload?.id && Array.isArray(prev.participants)) {
          state.currentProject = { ...action.payload, participants: prev.participants };
        } else {
          state.currentProject = action.payload;
        }
        state.error = null;
      })
      .addCase(fetchProject.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })
      // Update project
      .addCase(updateProject.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(updateProject.fulfilled, (state, action) => {
        state.isLoading = false;
        const index = state.projects.findIndex(p => p.id === action.payload.id);
        if (index !== -1) {
          // Преобразуем ProjectResponse в ProjectListResponse для списка
          state.projects[index] = {
            id: action.payload.id,
            name: action.payload.name,
            description: action.payload.description,
            status: action.payload.status,
            created_at: action.payload.created_at,
            updated_at: action.payload.updated_at,
            participant_count:
              action.payload.participants_count ??
              action.payload.participants?.length ??
              0,
            unread_messages_count: state.projects[index].unread_messages_count || 0
          };
        }
        if (state.currentProject?.id === action.payload.id) {
          state.currentProject = action.payload;
        }
        state.error = null;
      })
      .addCase(updateProject.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })
      // Delete project
      .addCase(deleteProject.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(deleteProject.fulfilled, (state, action) => {
        state.isLoading = false;
        state.projects = state.projects.filter(p => p.id !== action.payload);
        if (state.currentProject?.id === action.payload) {
          state.currentProject = null;
        }
        state.error = null;
      })
      .addCase(deleteProject.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })
      // Create workspace
      .addCase(createWorkspace.pending, (state) => {
        state.workspaceLoading = true;
        state.error = null;
      })
      .addCase(createWorkspace.fulfilled, (state, action) => {
        state.workspaceLoading = false;
        if (state.currentProject) {
          state.currentProject.workspaces = state.currentProject.workspaces || [];
          state.currentProject.workspaces.push(action.payload);
        }
        state.workspaces.push(action.payload);
        state.error = null;
      })
      .addCase(createWorkspace.rejected, (state, action) => {
        state.workspaceLoading = false;
        state.error = action.payload;
      })
      // Fetch workspaces
      .addCase(fetchWorkspaces.pending, (state) => {
        state.workspaceLoading = true;
        state.error = null;
      })
      .addCase(fetchWorkspaces.fulfilled, (state, action) => {
        state.workspaceLoading = false;
        state.workspaces = action.payload.workspaces;
        if (state.currentProject?.id === action.payload.projectId) {
          state.currentProject.workspaces = action.payload.workspaces;
        }
        state.error = null;
      })
      .addCase(fetchWorkspaces.rejected, (state, action) => {
        state.workspaceLoading = false;
        state.error = action.payload;
      })
      // Update workspace
      .addCase(updateWorkspace.pending, (state) => {
        state.workspaceLoading = true;
        state.error = null;
      })
      .addCase(updateWorkspace.fulfilled, (state, action) => {
        state.workspaceLoading = false;
        const index = state.workspaces.findIndex(w => w.id === action.payload.id);
        if (index !== -1) {
          state.workspaces[index] = action.payload;
        }
        if (state.currentProject?.workspaces) {
          const wsIndex = state.currentProject.workspaces.findIndex(w => w.id === action.payload.id);
          if (wsIndex !== -1) {
            state.currentProject.workspaces[wsIndex] = action.payload;
          }
        }
        if (state.currentWorkspace?.id === action.payload.id) {
          state.currentWorkspace = action.payload;
        }
        state.error = null;
      })
      .addCase(updateWorkspace.rejected, (state, action) => {
        state.workspaceLoading = false;
        state.error = action.payload;
      })
      // Delete workspace
      .addCase(deleteWorkspace.pending, (state) => {
        state.workspaceLoading = true;
        state.error = null;
      })
      .addCase(deleteWorkspace.fulfilled, (state, action) => {
        state.workspaceLoading = false;
        state.workspaces = state.workspaces.filter(w => w.id !== action.payload);
        if (state.currentProject?.workspaces) {
          state.currentProject.workspaces = state.currentProject.workspaces.filter(w => w.id !== action.payload);
        }
        if (state.currentWorkspace?.id === action.payload) {
          state.currentWorkspace = null;
        }
        state.error = null;
      })
      .addCase(deleteWorkspace.rejected, (state, action) => {
        state.workspaceLoading = false;
        state.error = action.payload;
      })
      // Add project participants
      .addCase(addProjectParticipants.fulfilled, (state, action) => {
        if (state.currentProject?.id === action.payload.projectId) {
          state.currentProject.participants = [
            ...(state.currentProject.participants || []),
            ...action.payload.participants
          ];
        }
        state.error = null;
      })
      .addCase(addProjectParticipants.rejected, (state, action) => {
        state.error = action.payload;
      })
      // Create project invitations
      .addCase(createProjectInvitations.pending, (state) => {
        state.invitationLoading = true;
        state.error = null;
      })
      .addCase(createProjectInvitations.fulfilled, (state) => {
        state.invitationLoading = false;
        state.error = null;
      })
      .addCase(createProjectInvitations.rejected, (state, action) => {
        state.invitationLoading = false;
        state.error = action.payload;
      })
      // Fetch project participants
      .addCase(fetchProjectParticipants.fulfilled, (state, action) => {
        if (state.currentProject?.id === action.payload.projectId) {
          state.currentProject.participants = action.payload.participants;
        }
        state.error = null;
      })
      .addCase(fetchProjectParticipants.rejected, (state, action) => {
        state.error = action.payload;
      })
      // Update participant status
      .addCase(updateParticipantStatus.fulfilled, (state, action) => {
        if (state.currentProject?.id === action.payload.projectId && state.currentProject.participants) {
          const index = state.currentProject.participants.findIndex(
            p => p.user_id === action.payload.participant.user_id
          );
          if (index !== -1) {
            state.currentProject.participants[index] = action.payload.participant;
          }
        }
        state.error = null;
      })
      .addCase(updateParticipantStatus.rejected, (state, action) => {
        state.error = action.payload;
      })
      // Add workspace participants
      .addCase(addWorkspaceParticipants.fulfilled, (state, action) => {
        if (state.currentProject?.workspaces) {
          const workspace = state.currentProject.workspaces.find(w => w.id === action.payload.workspaceId);
          if (workspace) {
            workspace.participants = [
              ...(workspace.participants || []),
              ...action.payload.participants
            ];
          }
        }
        state.error = null;
      })
      .addCase(addWorkspaceParticipants.rejected, (state, action) => {
        state.error = action.payload;
      })
      // Fetch workspace participants
      .addCase(fetchWorkspaceParticipants.fulfilled, (state, action) => {
        if (state.currentProject?.workspaces) {
          const workspace = state.currentProject.workspaces.find(w => w.id === action.payload.workspaceId);
          if (workspace) {
            workspace.participants = action.payload.participants;
          }
        }
        state.error = null;
      })
      .addCase(fetchWorkspaceParticipants.rejected, (state, action) => {
        state.error = action.payload;
      })
      // Remove workspace participant
      .addCase(removeWorkspaceParticipant.fulfilled, (state, action) => {
        if (state.currentProject?.workspaces) {
          const workspace = state.currentProject.workspaces.find(w => w.id === action.payload.workspaceId);
          if (workspace && workspace.participants) {
            workspace.participants = workspace.participants.filter(
              p => p.user_id !== action.payload.participantUserId
            );
          }
        }
        state.error = null;
      })
      .addCase(removeWorkspaceParticipant.rejected, (state, action) => {
        state.error = action.payload;
      })
      // Leave project
      .addCase(leaveProject.fulfilled, (state, action) => {
        state.projects = state.projects.filter(p => p.id !== action.payload);
        if (state.currentProject?.id === action.payload) {
          state.currentProject = null;
        }
        state.error = null;
      })
      .addCase(leaveProject.rejected, (state, action) => {
        state.error = action.payload;
      })
      // Task reducers
      .addCase(createTask.pending, (state) => {
        state.taskLoading = true;
        state.error = null;
      })
      .addCase(createTask.fulfilled, (state, action) => {
        state.taskLoading = false;
        if (state.currentWorkspace?.id === action.payload.workspace_id) {
          state.tasks = [...(state.tasks || []), action.payload];
        }
        if (state.currentProject?.workspaces) {
          const workspace = state.currentProject.workspaces.find(w => w.id === action.payload.workspace_id);
          if (workspace) {
            workspace.tasks = [...(workspace.tasks || []), action.payload];
          }
        }
        state.error = null;
      })
      .addCase(createTask.rejected, (state, action) => {
        state.taskLoading = false;
        state.error = action.payload;
      })
      .addCase(fetchTasks.pending, (state) => {
        state.taskLoading = true;
        state.error = null;
      })
      .addCase(fetchTasks.fulfilled, (state, action) => {
        state.taskLoading = false;
        state.tasks = action.payload.tasks;
        if (state.currentProject?.workspaces) {
          const workspace = state.currentProject.workspaces.find(w => w.id === action.payload.workspaceId);
          if (workspace) {
            workspace.tasks = action.payload.tasks;
          }
        }
        state.error = null;
      })
      .addCase(fetchTasks.rejected, (state, action) => {
        state.taskLoading = false;
        state.error = action.payload;
      })
      .addCase(fetchTask.fulfilled, (state, action) => {
        state.currentTask = action.payload;
        state.error = null;
      })
      .addCase(fetchTask.rejected, (state, action) => {
        state.error = action.payload;
      })
      .addCase(updateTask.fulfilled, (state, action) => {
        const index = state.tasks.findIndex(t => t.id === action.payload.id);
        if (index !== -1) {
          state.tasks[index] = action.payload;
        }
        if (state.currentProject?.workspaces) {
          const workspace = state.currentProject.workspaces.find(w => w.id === action.payload.workspace_id);
          if (workspace) {
            const taskIndex = workspace.tasks?.findIndex(t => t.id === action.payload.id);
            if (taskIndex !== -1) {
              workspace.tasks[taskIndex] = action.payload;
            }
          }
        }
        if (state.currentTask?.id === action.payload.id) {
          state.currentTask = action.payload;
        }
        state.error = null;
      })
      .addCase(updateTask.rejected, (state, action) => {
        state.error = action.payload;
      })
      .addCase(deleteTask.fulfilled, (state, action) => {
        state.tasks = state.tasks.filter(t => t.id !== action.payload.taskId);
        if (state.currentProject?.workspaces) {
          const workspace = state.currentProject.workspaces.find(w => w.id === action.payload.workspaceId);
          if (workspace && workspace.tasks) {
            workspace.tasks = workspace.tasks.filter(t => t.id !== action.payload.taskId);
          }
        }
        if (state.currentTask?.id === action.payload.taskId) {
          state.currentTask = null;
        }
        state.error = null;
      })
      .addCase(deleteTask.rejected, (state, action) => {
        state.error = action.payload;
      })
      .addCase(fetchUpcomingDeadlines.fulfilled, (state, action) => {
        state.upcomingDeadlines = action.payload.deadlines;
        state.error = null;
      })
      .addCase(fetchUpcomingDeadlines.rejected, (state, action) => {
        state.error = action.payload;
      })
      .addCase(fetchTaskComments.fulfilled, (state, action) => {
        state.taskCommentsLoading = false;
        state.taskComments = action.payload.comments;
        state.error = null;
      })
      .addCase(fetchTaskComments.pending, (state) => {
        state.taskCommentsLoading = true;
        state.error = null;
      })
      .addCase(fetchTaskComments.rejected, (state, action) => {
        state.taskCommentsLoading = false;
        state.error = action.payload;
      })
      .addCase(addTaskComment.fulfilled, (state, action) => {
        state.taskComments = [...(state.taskComments || []), action.payload];
        state.error = null;
      })
      .addCase(addTaskComment.rejected, (state, action) => {
        state.error = action.payload;
      })
      .addCase(updateTaskComment.fulfilled, (state, action) => {
        const index = state.taskComments.findIndex(c => c.id === action.payload.id);
        if (index !== -1) {
          state.taskComments[index] = action.payload;
        }
        state.error = null;
      })
      .addCase(updateTaskComment.rejected, (state, action) => {
        state.error = action.payload;
      })
      .addCase(deleteTaskComment.fulfilled, (state, action) => {
        state.taskComments = state.taskComments.filter(c => c.id !== action.payload.commentId);
        state.error = null;
      })
      .addCase(deleteTaskComment.rejected, (state, action) => {
        state.error = action.payload;
      })
      .addCase(fetchWorkspaceStatistics.fulfilled, (state, action) => {
        state.workspaceStatistics = action.payload.statistics;
        state.error = null;
      })
      .addCase(fetchWorkspaceStatistics.rejected, (state, action) => {
        state.error = action.payload;
      })
      .addCase(fetchStatisticsHistory.fulfilled, (state, action) => {
        state.statisticsHistory = action.payload.history;
        state.error = null;
      })
      .addCase(fetchStatisticsHistory.rejected, (state, action) => {
        state.error = action.payload;
      })
      // Project Files
      .addCase(fetchProjectFiles.pending, (state) => {
        state.projectFilesLoading = true;
        state.projectFilesError = null;
      })
      .addCase(fetchProjectFiles.fulfilled, (state, action) => {
        state.projectFilesLoading = false;
        const files = action.payload?.files;
        state.projectFiles = Array.isArray(files) ? files : [];
        state.projectFilesError = null;
      })
      .addCase(fetchProjectFiles.rejected, (state, action) => {
        state.projectFilesLoading = false;
        state.projectFilesError = action.payload;
      })
      .addCase(uploadProjectFile.pending, (state) => {
        state.uploadFileLoading = true;
      })
      .addCase(uploadProjectFile.fulfilled, (state, action) => {
        state.uploadFileLoading = false;
        state.projectFiles = [action.payload.file, ...(state.projectFiles || [])];
      })
      .addCase(uploadProjectFile.rejected, (state, action) => {
        state.uploadFileLoading = false;
        state.projectFilesError = action.payload;
      })
      .addCase(deleteProjectFile.fulfilled, (state, action) => {
        state.projectFiles = (state.projectFiles || []).filter(
          (f) => f.id !== action.payload.fileId
        );
      })
      .addCase(deleteProjectFile.rejected, (state, action) => {
        state.projectFilesError = action.payload;
      });
  },
});

export const { clearProjectsError, clearCurrentProject, setCurrentWorkspace, clearCurrentTask, clearTaskComments, clearProjectFiles } = projectsSlice.actions;

export default projectsSlice.reducer;
