/**
 * Auth state store. Access token held in memory only — never localStorage.
 * Refresh token is in an httpOnly cookie managed by the backend.
 */

import { create } from "zustand";
import type { User } from "@/api/auth";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  currentOrgId: string | null;
  isAuthenticated: boolean;

  setAuth: (user: User, token: string) => void;
  setAccessToken: (token: string) => void;
  setCurrentOrg: (orgId: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  currentOrgId: null,
  isAuthenticated: false,

  setAuth: (user, token) =>
    set({ user, accessToken: token, isAuthenticated: true }),

  setAccessToken: (token) => set({ accessToken: token }),

  setCurrentOrg: (orgId) => set({ currentOrgId: orgId }),

  logout: () =>
    set({
      user: null,
      accessToken: null,
      currentOrgId: null,
      isAuthenticated: false,
    }),
}));
