// store/slices/viewedProfile.js
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { profileAPI } from '../../services/api';

export const fetchViewedProfile = createAsyncThunk(
  'viewedProfile/fetchViewedProfile',
  async (user_id, { rejectWithValue }) => {
    try {
      if (!user_id) {
        return rejectWithValue('No user_id provided');
      }
      const response = await profileAPI.getUserProfile(user_id);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

const viewedProfileSlice = createSlice({
  name: 'viewedProfile',
  initialState: {
    profile: null,
    isLoading: false,
    error: null,
  },
  reducers: {
    clearViewedProfile: (state) => {
      state.profile = null;
      state.isLoading = false;
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchViewedProfile.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchViewedProfile.fulfilled, (state, action) => {
        state.isLoading = false;
        state.profile = action.payload;
        state.error = null;
      })
      .addCase(fetchViewedProfile.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      });
  },
});

export const { clearViewedProfile } = viewedProfileSlice.actions;
export default viewedProfileSlice.reducer;