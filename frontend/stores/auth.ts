import { defineStore } from 'pinia'

interface AuthUser {
  id: number
  email: string
  first_name: string
  last_name: string
  role: 'student' | 'instructor' | 'admin'
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    // Access token lives only in memory (not localStorage) so an XSS bug
    // can't read it off disk; the refresh token never reaches JS at all —
    // it's an httpOnly cookie set by the backend.
    accessToken: null as string | null,
    user: null as AuthUser | null,
  }),

  getters: {
    isAuthenticated: (state) => !!state.accessToken,
    isInstructor: (state) => state.user?.role === 'instructor',
    isAdmin: (state) => state.user?.role === 'admin',
  },

  actions: {
    setSession(accessToken: string, user: AuthUser) {
      this.accessToken = accessToken
      this.user = user
    },
    clearSession() {
      this.accessToken = null
      this.user = null
    },
  },
})
