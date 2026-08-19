let authCleanup = null

export function registerAuthCleanup(cleanup) {
  authCleanup = cleanup
}

export function invalidateAuthSession() {
  if (authCleanup) {
    authCleanup()
    return
  }

  localStorage.removeItem('token')
  localStorage.removeItem('refreshToken')
}
