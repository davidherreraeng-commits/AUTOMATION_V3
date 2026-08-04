import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import api from "../api/axiosConfig";

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadCurrentUser = useCallback(async () => {
    try {
      const response = await api.get("/auth/me");
      setUser(response.data);
      return response.data;
    } catch (error) {
      if (error.response?.status !== 401) {
        console.error("No fue posible recuperar la sesión:", error);
      }
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCurrentUser();
  }, [loadCurrentUser]);

  useEffect(() => {
    const handleUnauthorized = () => setUser(null);
    window.addEventListener("rpa:unauthorized", handleUnauthorized);
    return () => {
      window.removeEventListener("rpa:unauthorized", handleUnauthorized);
    };
  }, []);

  const login = useCallback(async ({ username, password }) => {
    const response = await api.post("/auth/login", {
      username,
      password,
    });
    setUser(response.data.user);
    return response.data.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } finally {
      setUser(null);
    }
  }, []);

  const changePassword = useCallback(
    async ({ currentPassword, newPassword }) => {
      const response = await api.post("/auth/change-password", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setUser(response.data);
      return response.data;
    },
    [],
  );

  const value = useMemo(
    () => ({
      user,
      loading,
      isAuthenticated: Boolean(user),
      login,
      logout,
      changePassword,
      refreshSession: loadCurrentUser,
    }),
    [
      user,
      loading,
      login,
      logout,
      changePassword,
      loadCurrentUser,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
