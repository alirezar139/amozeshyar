export interface LiveLogEntry {
  id: number
  at: string
  level: 'error' | 'warning'
  kind: 'js' | 'promise' | 'vue' | 'api'
  message: string
  detail?: string
}

/**
 * Errors caught on this page (see plugins/live-log.client.ts). Shown in the corner panel to
 * developers, and attached to support reports so the developer sees what the user saw.
 */
export function useLiveLog() {
  const entries = useState<LiveLogEntry[]>('live-log', () => [])
  return { entries }
}
