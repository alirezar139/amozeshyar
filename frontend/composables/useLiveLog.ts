export interface LiveLogEntry {
  id: number
  at: string
  level: 'error' | 'warning'
  kind: 'js' | 'promise' | 'vue' | 'api'
  message: string
  detail?: string
}

/** Errors caught on this page in dev mode (see plugins/live-log.client.ts). */
export function useLiveLog() {
  const entries = useState<LiveLogEntry[]>('live-log', () => [])
  return { entries }
}
