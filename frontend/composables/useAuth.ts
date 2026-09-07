export function useAuth() {
  const { request } = useApi()
  const authStore = useAuthStore()

  async function login(email: string, password: string, captchaPassToken: string) {
    const data = await request<{ access: string }>('/auth/login/', {
      method: 'POST',
      body: { email, password, captcha_pass_token: captchaPassToken },
    })
    // The access token must be in the store before this next call, since
    // useApi() reads it from here to build the Authorization header.
    authStore.accessToken = data.access
    const user = await request<any>('/auth/me/')
    authStore.setSession(data.access, user)
  }

  async function register(payload: {
    email: string
    password: string
    first_name: string
    last_name: string
    role: 'student' | 'instructor'
    interests?: string
  }) {
    // RegisterView logs the new account straight in and returns the same
    // shape LoginView would — no captcha here, that gate is specific to
    // the login form (see backend RegisterView docstring).
    const data = await request<{ access: string }>('/auth/register/', { method: 'POST', body: payload })
    authStore.accessToken = data.access
    const user = await request<any>('/auth/me/')
    authStore.setSession(data.access, user)
  }

  async function logout() {
    await request('/auth/logout/', { method: 'POST' }).catch(() => {})
    authStore.clearSession()
  }

  return { login, register, logout }
}
