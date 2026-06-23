
// store/slices/authSlice.js
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { authAPI } from '../../services/api';
// Импортируем из ПРАВИЛЬНОГО файла
import { websocketService } from '../../services/websocket';

export const fetchAuth = createAsyncThunk(
  'auth/fetchAuth',
  async (credentials, { rejectWithValue }) => {
    try {
      const response = await authAPI.login(credentials);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

const authSlice = createSlice({
  name: 'auth',
  initialState: {
    user: null,
    token: localStorage.getItem('token'),
    isAuth: !!localStorage.getItem('token'),
    isLoading: false,
    error: null,
  },
  reducers: {
    logout: (state) => {
      state.user = null;
      state.token = null;
      state.isAuth = false;
      // Отключаем WebSocket при выходе
      websocketService.disconnect();
      localStorage.removeItem('token');
      localStorage.removeItem('userData');
    },
    clearError: (state) => {
      state.error = null;
    },
    setAuth: (state) => {
      state.isAuth = !!state.token;
    },
    initWebSocket: (state) => {
      // Инициализируем WebSocket если пользователь авторизован
      if (state.isAuth && state.user?.user_id) {
        try {
          websocketService.connect(state.user.user_id);
          console.log('✅ WebSocket initialized for user:', state.user.user_id);
        } catch (error) {
          console.error('❌ Failed to initialize WebSocket:', error);
        }
      }
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchAuth.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchAuth.fulfilled, (state, action) => {
        state.isLoading = false;
        state.isAuth = true;
        state.token = action.payload.access_token;
        state.user = { user_id: action.payload.user_id };
        localStorage.setItem('token', action.payload.access_token);
        
        // Автоматически инициализируем WebSocket после успешного входа
        if (action.payload.user_id) {
          setTimeout(() => {
            websocketService.connect(action.payload.user_id);
          }, 1000);
        }
      })
      .addCase(fetchAuth.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      });
  },
});

export const { logout, clearError, setAuth, initWebSocket } = authSlice.actions;

// СЕЛЕКТОРЫ
export const selectIsAuth = (state) => state?.auth?.isAuth ?? false;
export const selectUser = (state) => state?.auth?.user ?? null;
export const selectUserId = (state) => state?.auth?.user?.user_id ?? null;
export const selectToken = (state) => state?.auth?.token ?? null;
export const selectAuthLoading = (state) => state?.auth?.isLoading ?? false;
export const selectAuthError = (state) => state?.auth?.error ?? null;

export default authSlice.reducer;