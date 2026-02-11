import { useCallback, useSyncExternalStore } from 'react'

/**
 * Read/write a single URL search param — the URL is the single source of truth.
 *
 * Uses `useSyncExternalStore` to subscribe to `popstate` events (back/forward)
 * and re-render when the URL changes externally.
 *
 * Why not react-router?
 * This app has a single view — no route transitions, no nested layouts, no
 * code-splitting by route. The only URL state is search params (filters, sort,
 * page). Adding react-router for that would pull in a router context, a
 * <BrowserRouter> wrapper, and route definitions — all overhead with no benefit.
 * This hook does the one thing we need: sync a search param with React state.
 */
export function useURLParam(key: string, fallback = '') {
  // 1. SUBSCRIBE — tell React how to listen for URL changes (back/forward).
  //    Returns a cleanup function that removes the listener on unmount.
  const subscribe = useCallback((notify: () => void) => {
    window.addEventListener('popstate', notify)
    return () => window.removeEventListener('popstate', notify)
  }, [])

  // 2. READ — tell React how to get the current value from the URL.
  //    Called on every render and after every popstate event.
  const getSnapshot = useCallback(
    () => new URLSearchParams(window.location.search).get(key) ?? fallback,
    [key, fallback],
  )

  // React re-renders when getSnapshot() returns a different value.
  const value = useSyncExternalStore(subscribe, getSnapshot)

  // 3. WRITE — update the URL and notify all subscribers.
  //    pushState changes the URL without a page reload.
  //    Dispatching popstate tells useSyncExternalStore the URL changed.
  const set = useCallback(
    (v: string) => {
      const params = new URLSearchParams(window.location.search)
      if (v) params.set(key, v)
      else params.delete(key)
      const qs = params.toString()
      window.history.pushState({}, '', qs ? `?${qs}` : window.location.pathname)
      window.dispatchEvent(new PopStateEvent('popstate'))
    },
    [key],
  )

  return [value, set] as const
}
