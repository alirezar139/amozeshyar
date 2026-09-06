/**
 * Shared, SSR-safe modal state (useState) so the header, footer, or any
 * other button can open the same login dialog without prop-drilling —
 * clicking "ورود" opens this instead of navigating to a full page.
 */
export function useLoginModal() {
  const isOpen = useState('login-modal-open', () => false)
  return {
    isOpen,
    open: () => (isOpen.value = true),
    close: () => (isOpen.value = false),
  }
}
