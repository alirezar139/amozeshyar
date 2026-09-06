const roleHome: Record<string, string> = {
  admin: '/admin',
  instructor: '/instructor-panel/courses',
  student: '/dashboard',
}

export function getRoleHome(role: string | undefined): string {
  return roleHome[role ?? 'student'] ?? '/dashboard'
}
