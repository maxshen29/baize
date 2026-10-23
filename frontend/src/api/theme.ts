import http from './http'

export function getDefault() {
  return http.get('/theme/default')
}

export function setDefault(theme: string) {
  return http.put('/theme/default', { theme })
}
