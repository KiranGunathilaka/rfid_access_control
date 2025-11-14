export const API_CONFIG = {
  BASE_URL: "http://localhost:5000/api",
  // BASE_URL: "https://rgcbmt33-5000.asse.devtunnels.ms/api",
  // BASE_URL: "http://localhost:5000/api",
  ENDPOINTS: {
    LOGIN: "/auth/login",
    REGISTER: "/auth/register",
    ANALYTICS: "/admin/analytics",
    LOGS: "/admin/logs",
    HEALTH: "/health",
    USERS: "/user",
  },
}

export const getApiUrl = (endpoint: string) => {
  return `${API_CONFIG.BASE_URL}${endpoint}`
}

export const apiUrls = {
  login: () => getApiUrl(API_CONFIG.ENDPOINTS.LOGIN),
  register: () => getApiUrl(API_CONFIG.ENDPOINTS.REGISTER),
  analytics: () => getApiUrl(API_CONFIG.ENDPOINTS.ANALYTICS),
  logs: () => getApiUrl(API_CONFIG.ENDPOINTS.LOGS),
  health: () => getApiUrl(API_CONFIG.ENDPOINTS.HEALTH),
  users: (search?: string) => {
    const url = getApiUrl(API_CONFIG.ENDPOINTS.USERS);
    return search ? `${url}?search=${encodeURIComponent(search)}` : url;
  },
}
