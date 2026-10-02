import axios from 'axios';

const defaultHost = (typeof window !== 'undefined' && window.location && window.location.hostname)
    ? window.location.hostname
    : '136.234.4.160';

const instance = axios.create({
    baseURL: import.meta.env.VITE_API_URL || `http://${defaultHost}:8000`
});

instance.interceptors.request.use(async (config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = token;
    }
    return config;
});

instance.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            localStorage.removeItem('token');
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

export default instance;