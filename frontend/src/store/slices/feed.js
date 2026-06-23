import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { feedAPI } from '../../services/api'

export const fetchFeed = createAsyncThunk('feed/fetchFeed', async (params = {}, { rejectWithValue }) => {
  try {
    const response = await feedAPI.getFeed(params)
    return response.data
  } catch (error) {
    return rejectWithValue(error.response?.data || error.message)
  }
})

export const fetchRecommended = createAsyncThunk('feed/fetchRecommended', async (limit = 20, { rejectWithValue }) => {
  try {
    const response = await feedAPI.getRecommended(limit)
    return response.data
  } catch (error) {
    return rejectWithValue(error.response?.data || error.message)
  }
})

export const fetchTrending = createAsyncThunk('feed/fetchTrending', async ({ days = 7, limit = 20 } = {}, { rejectWithValue }) => {
  try {
    const response = await feedAPI.getTrending(days, limit)
    return response.data
  } catch (error) {
    return rejectWithValue(error.response?.data || error.message)
  }
})

export const fetchLikedFeed = createAsyncThunk('feed/fetchLikedFeed', async ({ limit = 20, offset = 0 } = {}, { rejectWithValue }) => {
  try {
    const response = await feedAPI.getLiked(limit, offset)
    return response.data
  } catch (error) {
    return rejectWithValue(error.response?.data || error.message)
  }
})

export const fetchFeedCategories = createAsyncThunk('feed/fetchFeedCategories', async (_, { rejectWithValue }) => {
  try {
    const response = await feedAPI.getCategories()
    return response.data
  } catch (error) {
    return rejectWithValue(error.response?.data || error.message)
  }
})

export const fetchCategoryFeed = createAsyncThunk('feed/fetchCategoryFeed', async ({ category, limit = 20, offset = 0 }, { rejectWithValue }) => {
  try {
    const response = await feedAPI.getProjectsByCategory(category, limit, offset)
    return response.data
  } catch (error) {
    return rejectWithValue(error.response?.data || error.message)
  }
})

export const fetchFeedProjectDetail = createAsyncThunk('feed/fetchProjectDetail', async (projectId, { rejectWithValue }) => {
  try {
    const response = await feedAPI.getProjectDetail(projectId)
    return response.data
  } catch (error) {
    return rejectWithValue(error.response?.data || error.message)
  }
})

export const fetchFeedProjectComments = createAsyncThunk('feed/fetchComments', async ({ postId, limit = 50, offset = 0, parent_id = null }, { rejectWithValue }) => {
  try {
    const response = await feedAPI.getProjectComments(postId, limit, offset, parent_id)
    return { postId, parent_id, payload: response.data }
  } catch (error) {
    return rejectWithValue(error.response?.data || error.message)
  }
})

export const createFeedComment = createAsyncThunk('feed/createComment', async ({ postId, content, parent_id = null }, { rejectWithValue }) => {
  try {
    const response = await feedAPI.createComment(postId, { content, parent_id })
    return { postId, comment: response.data }
  } catch (error) {
    return rejectWithValue(error.response?.data || error.message)
  }
})

export const updateFeedComment = createAsyncThunk('feed/updateComment', async ({ commentId, content }, { rejectWithValue }) => {
  try {
    const response = await feedAPI.updateComment(commentId, { content })
    return response.data
  } catch (error) {
    return rejectWithValue(error.response?.data || error.message)
  }
})

export const deleteFeedComment = createAsyncThunk('feed/deleteComment', async (commentId, { rejectWithValue }) => {
  try {
    await feedAPI.deleteComment(commentId)
    return commentId
  } catch (error) {
    return rejectWithValue(error.response?.data || error.message)
  }
})

export const toggleFeedProjectLike = createAsyncThunk('feed/toggleProjectLike', async ({ projectId, shouldLike }, { rejectWithValue }) => {
  try {
    if (shouldLike) await feedAPI.likeProject(projectId)
    else await feedAPI.unlikeProject(projectId)
    return { projectId, shouldLike }
  } catch (error) {
    return rejectWithValue(error.response?.data || error.message)
  }
})

export const toggleFeedCommentLike = createAsyncThunk('feed/toggleCommentLike', async ({ commentId, shouldLike }, { rejectWithValue }) => {
  try {
    if (shouldLike) await feedAPI.likeComment(commentId)
    else await feedAPI.unlikeComment(commentId)
    return { commentId, shouldLike }
  } catch (error) {
    return rejectWithValue(error.response?.data || error.message)
  }
})

export const fetchFeedUsers = createAsyncThunk('feed/fetchUsers', async (payload, { rejectWithValue }) => {
  try {
    const response = await feedAPI.searchUsers(payload)
    return response.data
  } catch (error) {
    return rejectWithValue(error.response?.data || error.message)
  }
})

export const fetchCreatorFeed = createAsyncThunk('feed/fetchCreatorFeed', async ({ userId, limit = 20, offset = 0 }, { rejectWithValue }) => {
  try {
    const response = await feedAPI.getCreatorProjects(userId, limit, offset)
    return response.data
  } catch (error) {
    return rejectWithValue(error.response?.data || error.message)
  }
})

const normalizeFeedItems = (data) => {
  if (!data) return []
  if (Array.isArray(data)) return data
  if (Array.isArray(data.items)) return data.items
  if (Array.isArray(data.comments)) return data.comments
  return []
}

const feedSlice = createSlice({
  name: 'feed',
  initialState: {
    items: [],
    categories: [],
    selectedProject: null,
    detailLoading: false,
    detailError: null,
    commentsByProject: {},
    repliesByProject: {}, // { [projectId]: { [parentId]: [...] } }
    users: [],
    isLoading: false,
    commentsLoading: false,
    usersLoading: false,
    error: null,
  },
  reducers: {
    clearFeedError: (state) => {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchFeed.pending, (state) => {
        state.isLoading = true
        state.error = null
      })
      .addCase(fetchFeed.fulfilled, (state, action) => {
        state.isLoading = false
        state.items = normalizeFeedItems(action.payload)
      })
      .addCase(fetchFeed.rejected, (state, action) => {
        state.isLoading = false
        state.error = action.payload
      })
      .addCase(fetchRecommended.fulfilled, (state, action) => {
        state.items = normalizeFeedItems(action.payload)
      })
      .addCase(fetchTrending.fulfilled, (state, action) => {
        const rows = normalizeFeedItems(action.payload)
        state.items = rows.map((x) => x.project || x)
      })
      .addCase(fetchLikedFeed.fulfilled, (state, action) => {
        state.items = normalizeFeedItems(action.payload)
      })
      .addCase(fetchCategoryFeed.fulfilled, (state, action) => {
        state.items = normalizeFeedItems(action.payload)
      })
      .addCase(fetchFeedCategories.fulfilled, (state, action) => {
        state.categories = Array.isArray(action.payload) ? action.payload : []
      })
      .addCase(fetchFeedProjectDetail.pending, (state) => {
        state.detailLoading = true
        state.detailError = null
        state.selectedProject = null
      })
      .addCase(fetchFeedProjectDetail.fulfilled, (state, action) => {
        state.detailLoading = false
        state.selectedProject = action.payload
        state.detailError = null
      })
      .addCase(fetchFeedProjectDetail.rejected, (state, action) => {
        state.detailLoading = false
        state.selectedProject = null
        state.detailError = action.payload
      })
      .addCase(fetchFeedProjectComments.pending, (state) => {
        state.commentsLoading = true
      })
      .addCase(fetchFeedProjectComments.fulfilled, (state, action) => {
        state.commentsLoading = false
        const items = normalizeFeedItems(action.payload.payload)
        const pid = String(action.payload.postId)
        const parentId = action.payload.parent_id
        if (parentId != null && parentId !== undefined) {
          if (!state.repliesByProject[pid]) state.repliesByProject[pid] = {}
          state.repliesByProject[pid][String(parentId)] = items
        } else {
          state.commentsByProject[pid] = items
        }
      })
      .addCase(fetchFeedProjectComments.rejected, (state, action) => {
        state.commentsLoading = false
        state.error = action.payload
      })
      .addCase(createFeedComment.fulfilled, (state, action) => {
        const key = String(action.payload.postId)
        const comment = action.payload.comment
        if (comment.parent_id != null && comment.parent_id !== undefined) {
          if (!state.repliesByProject[key]) state.repliesByProject[key] = {}
          const pid = String(comment.parent_id)
          const prev = state.repliesByProject[key][pid] || []
          state.repliesByProject[key][pid] = [comment, ...prev]
          const parent = (state.commentsByProject[key] || []).find((c) => c.id === comment.parent_id)
          if (parent) parent.replies_count = (parent.replies_count || 0) + 1
        } else {
          const prev = state.commentsByProject[key] || []
          state.commentsByProject[key] = [comment, ...prev]
        }
      })
      .addCase(updateFeedComment.fulfilled, (state, action) => {
        const upd = (c) => (c.id === action.payload.id ? action.payload : c)
        Object.keys(state.commentsByProject).forEach((projectId) => {
          state.commentsByProject[projectId] = (state.commentsByProject[projectId] || []).map(upd)
        })
        Object.keys(state.repliesByProject).forEach((projectId) => {
          Object.keys(state.repliesByProject[projectId] || {}).forEach((parentId) => {
            state.repliesByProject[projectId][parentId] = (state.repliesByProject[projectId][parentId] || []).map(upd)
          })
        })
      })
      .addCase(deleteFeedComment.fulfilled, (state, action) => {
        const deletedId = action.payload
        Object.keys(state.commentsByProject).forEach((projectId) => {
          const roots = state.commentsByProject[projectId] || []
          let parentForDecrement = null
          Object.keys(state.repliesByProject[projectId] || {}).forEach((parentId) => {
            const replies = state.repliesByProject[projectId][parentId] || []
            if (replies.some((r) => r.id === deletedId)) parentForDecrement = roots.find((c) => String(c.id) === parentId)
            state.repliesByProject[projectId][parentId] = replies.filter((r) => r.id !== deletedId)
          })
          if (parentForDecrement) parentForDecrement.replies_count = Math.max(0, (parentForDecrement.replies_count || 0) - 1)
          state.commentsByProject[projectId] = roots.filter((c) => c.id !== deletedId)
        })
      })
      .addCase(toggleFeedProjectLike.fulfilled, (state, action) => {
        const updateItem = (item) => {
          if (String(item.id) !== String(action.payload.projectId)) return item
          const prev = !!item.is_liked_by_user
          const next = action.payload.shouldLike
          let likes = Number(item.likes_count || 0)
          if (next && !prev) likes += 1
          if (!next && prev) likes = Math.max(0, likes - 1)
          return { ...item, is_liked_by_user: next, likes_count: likes }
        }
        state.items = state.items.map(updateItem)
        if (state.selectedProject && String(state.selectedProject.id) === String(action.payload.projectId)) {
          state.selectedProject = updateItem(state.selectedProject)
        }
      })
      .addCase(toggleFeedCommentLike.fulfilled, (state, action) => {
        const upd = (c) => {
          if (String(c.id) !== String(action.payload.commentId)) return c
          const prev = !!c.is_liked_by_user
          const next = action.payload.shouldLike
          let likes = Number(c.likes_count || 0)
          if (next && !prev) likes += 1
          if (!next && prev) likes = Math.max(0, likes - 1)
          return { ...c, is_liked_by_user: next, likes_count: likes }
        }
        Object.keys(state.commentsByProject).forEach((projectId) => {
          state.commentsByProject[projectId] = (state.commentsByProject[projectId] || []).map(upd)
        })
        Object.keys(state.repliesByProject).forEach((projectId) => {
          Object.keys(state.repliesByProject[projectId] || {}).forEach((parentId) => {
            state.repliesByProject[projectId][parentId] = (state.repliesByProject[projectId][parentId] || []).map(upd)
          })
        })
      })
      .addCase(fetchFeedUsers.pending, (state) => {
        state.usersLoading = true
      })
      .addCase(fetchFeedUsers.fulfilled, (state, action) => {
        state.usersLoading = false
        state.users = Array.isArray(action.payload?.profiles) ? action.payload.profiles : []
      })
      .addCase(fetchFeedUsers.rejected, (state, action) => {
        state.usersLoading = false
        state.error = action.payload
      })
      .addCase(fetchCreatorFeed.fulfilled, (state, action) => {
        state.items = normalizeFeedItems(action.payload)
      })
  },
})

export const { clearFeedError } = feedSlice.actions
export default feedSlice.reducer
