import type { NavigateFunction, To } from 'react-router-dom'

export function navigateBack(navigate: NavigateFunction, fallbackTo: To) {
  if (window.history.length > 1) {
    navigate(-1)
    return
  }

  navigate(fallbackTo, { replace: true })
}
