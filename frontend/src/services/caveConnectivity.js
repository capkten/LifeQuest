export function createCaveConnectivity({ target = globalThis?.window } = {}) {
  const online = () => typeof globalThis?.navigator?.onLine === 'boolean' ? globalThis.navigator.onLine : true

  return {
    isOnline: online,
    subscribe(listener) {
      if (!target?.addEventListener) return () => {}
      const handleOnline = () => listener(true)
      const handleOffline = () => listener(false)
      target.addEventListener('online', handleOnline)
      target.addEventListener('offline', handleOffline)
      return () => {
        target.removeEventListener('online', handleOnline)
        target.removeEventListener('offline', handleOffline)
      }
    },
  }
}

export const defaultCaveConnectivity = createCaveConnectivity()
