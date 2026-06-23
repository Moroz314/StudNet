import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { profileAPI } from '../../services/api';


export const fetchProfile = createAsyncThunk(
  'profile/fetchProfile',
  async (user_id, { rejectWithValue }) => {  
    try {
      // Если user_id передан, получаем профиль другого пользователя
      // Если нет - получаем свой профиль
      let response;
      if (user_id) {
        response = await profileAPI.getUserProfile(user_id);
      } else {
        response = await profileAPI.getProfile();
      }
      return response.data;
    } catch (error) {
      return rejectWithValue({
        status: error.response?.status ?? error.status,
        detail: error.response?.data?.detail ?? error.response?.data,
        message: error.message,
      });
    }
  }
);

export const createProfile = createAsyncThunk(
  'profile/createProfile',
  async (profileData, { rejectWithValue }) => {
    try {
      const response = await profileAPI.createProf(profileData);
      console.log(response, 'awefawfawefaw')
      return response.data;
    } catch (error) {
      return rejectWithValue(error.data || error.message);
    }
  }
);

export const uploadAvatar = createAsyncThunk(
  'profile/uploadAvatar',
  async (avatarData, { rejectWithValue }) => {
    try {
      const response = await profileAPI.UploadAvatar(avatarData);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.data || error.message);
    }
  }
);

const profileSlice = createSlice({
  name: 'profile',
  initialState: {
    profile: null,
    isLoading: false,
    error: null,
    avatarUploading: false,
  },
  reducers: {
    clearProfileError: (state) => {
      state.error = null;
    },
    updateProfileLocal: (state, action) => {
      if (state.profile) {
        state.profile = { ...state.profile, ...action.payload };
      }
    },
    // Добавьте этот редюсер для очистки профиля
    clearProfile: (state) => {
      state.profile = null;
      state.isLoading = false;
      state.error = null;
      state.avatarUploading = false;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchProfile.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchProfile.fulfilled, (state, action) => {
        state.isLoading = false;
        state.profile = action.payload;
        state.error = null;
      })
      .addCase(fetchProfile.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })
      .addCase(createProfile.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(createProfile.fulfilled, (state, action) => {
        state.isLoading = false;
        state.profile = action.payload;
        state.error = null;
      })
      .addCase(createProfile.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })
      .addCase(uploadAvatar.pending, (state) => {
        state.avatarUploading = true;
        state.error = null;
      })
      .addCase(uploadAvatar.fulfilled, (state, action) => {
        state.avatarUploading = false;
        if (state.profile) {
          const avatarUrl = action.payload?.avatar_url || action.payload?.avatar_path || action.payload?.path || action.payload?.url || action.payload?.avatarUrl || null;
          if (avatarUrl) {
            state.profile.avatar_url = avatarUrl;
            state.profile.avatar_path = avatarUrl;
          }
          if (action.payload?.file_id) {
            state.profile.avatar_file_id = action.payload.file_id;
          }
        }
        state.error = null;
      })
      .addCase(uploadAvatar.rejected, (state, action) => {
        state.avatarUploading = false;
        state.error = action.payload;
      });
  },
});

// Обновите экспорт, добавив clearProfile
export const { 
  clearProfileError, 
  updateProfileLocal,
  clearProfile // Добавьте это
} = profileSlice.actions;

export default profileSlice.reducer;