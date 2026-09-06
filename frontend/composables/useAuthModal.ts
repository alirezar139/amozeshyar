/**
 * Shared, SSR-safe modal state for both login and register — one glass
 * dialog, switchable between modes, so "sign up instead" doesn't need to
 * close one modal and open a different one.
 */
export function useAuthModal() {
  const isOpen = useState('auth-modal-open', () => false)
  const mode = useState<'login' | 'register'>('auth-modal-mode', () => 'login')

  return {
    isOpen,
    mode,
    openLogin: () => {
      mode.value = 'login'
      isOpen.value = true
    },
    openRegister: () => {
      mode.value = 'register'
      isOpen.value = true
    },
    close: () => (isOpen.value = false),
  }
}
