export const API_CONFIG = {
  BASE_URL: process.env.NEXT_PUBLIC_API_URL!,
  ENDPOINTS: {
    LOGIN: "/auth/login",
    REGISTER: "/auth/register",
    ANALYTICS: "/admin/analytics", 
    LOGS: "/admin/logs",         
    HEALTH: "/health",
    USERS_SEARCH: "/users/search",
    USER_UPDATE: "/user/update",
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
    const base = getApiUrl(API_CONFIG.ENDPOINTS.USERS_SEARCH)
    return search ? `${base}?query=${encodeURIComponent(search)}` : base
  },

  userUpdate: () => getApiUrl(API_CONFIG.ENDPOINTS.USER_UPDATE),
}