import { useEffect } from 'react'
import { useThemeStore, type ThemeMode } from '@/store/theme'

function applyTheme(mode: ThemeMode) {
  const root = document.documentElement
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches

  if (mode === 'dark' || (mode === 'system' && prefersDark)) {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }
}

export function useTheme() {
  const { mode, setMode } = useThemeStore()

  useEffect(() => {
    applyTheme(mode)

    if (mode !== 'system') return

    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const listener = (e: MediaQueryListEvent) => {
      if (e.matches) document.documentElement.classList.add('dark')
      else document.documentElement.classList.remove('dark')
    }
    mq.addEventListener('change', listener)
    return () => mq.removeEventListener('change', listener)
  }, [mode])

  return { mode, setMode }
}
