import { useCallback, useState } from "react";

import { fetchCurrentUser, loginRequest, registerRequest } from "./auth.api.js";

const TOKEN_KEY = "sicons_token";

export function useAuthSession() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(null);

  const login = useCallback(async (credentials) => {
    const data = await loginRequest(credentials);
    localStorage.setItem(TOKEN_KEY, data.access_token);
    setToken(data.access_token);
    setUser(data.usuario);
    return data.usuario;
  }, []);

  const register = useCallback(async (payload) => {
    return registerRequest(payload);
  }, []);

  const loadCurrentUser = useCallback(async (activeToken) => {
    if (!activeToken) return null;
    const currentUser = await fetchCurrentUser(activeToken);
    setUser(currentUser);
    return currentUser;
  }, []);

  const clearSession = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }, []);

  return {
    token,
    user,
    login,
    register,
    loadCurrentUser,
    clearSession,
  };
}
