const roleHome: Record<string, string> = {
  admin: '/admin',
  student: '/dashboard',
}

export function getRoleHome(role: string | undefined): string {
  return roleHome[role ?? 'student'] ?? '/dashboard'
}
