import { configureStore } from '@reduxjs/toolkit';
import authReducer from './slices/auth';
import profileSlice from './slices/profile';
import chatReducer from './slices/chatSlice';
import projectsReducer from './slices/projects';
import feedReducer from './slices/feed';
import viewedProfileReducer from './slices/viewedProfile';
import { enableMapSet } from 'immer'

enableMapSet()

export const store = configureStore({
  reducer: {
    auth: authReducer,
    profile: profileSlice,
    viewedProfile: viewedProfileReducer,
    chat: chatReducer,
    projects: projectsReducer,
    feed: feedReducer,
  },
  devTools: process.env.NODE_ENV !== 'production',
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // ИГНОРИРУЕМ Map/Set В СОСТОЯНИИ
        ignoredActions: ['chat/userTyping', 'chat/userStopTyping'],
        ignoredPaths: ['chat.typingUsers', 'chat.onlineUsers'],
      },
    }),
})

export default store;
