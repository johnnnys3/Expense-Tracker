import { useCallback, useState } from "react";
import { apiFetch } from "../api";

export function useAuth() {
  const [token, setToken] = useState(localStorage.getItem("token"));

  const login = useCallback(async (email, password) => {
    const body = await apiFetch("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    localStorage.setItem("token", body.access_token);
    setToken(body.access_token);
  }, []);

  const register = useCallback(async (email, password) => {
    const body = await apiFetch("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    localStorage.setItem("token", body.access_token);
    setToken(body.access_token);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    setToken(null);
  }, []);

  return { token, login, register, logout };
}
