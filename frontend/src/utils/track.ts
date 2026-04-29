/**
 * Umami 自定义事件埋点封装。
 *
 * 脚本由 `index.html` 注入，runtime 通过 `window.umami.track()` 上报。
 * 当脚本未加载（被屏蔽 / 网络失败 / 本地开发未注入）时静默失败。
 */

import { useAuthStore } from '@/store/auth'

declare global {
  interface Window {
    umami?: {
      track: (eventName: string, eventData?: Record<string, unknown>) => void
    }
  }
}

export type TrackEvent =
  | { name: 'home_visit'; data: BaseUserData }
  | { name: 'upload_click'; data: BaseUserData & { file_count: number } }
  | {
      name: 'upload_success'
      data: BaseUserData & { file_count: number }
    }
  | {
      name: 'search'
      data: BaseUserData & { query: string; result_count: number }
    }
  | {
      name: 'content_view' | 'content_download'
      data: BaseUserData & {
        tab: string
        content_id: number
        content_title: string
        content_type: string
      }
    }

interface BaseUserData {
  user_name: string
}

/** 获取当前登录用户名，未登录返回 'anonymous'。 */
export function getCurrentUserName(): string {
  return useAuthStore.getState().user?.name ?? 'anonymous'
}

/**
 * 上报自定义事件。
 *
 * 使用类型联合保证事件名与属性 schema 匹配。
 * 容错：脚本未加载或上报抛错均静默忽略。
 */
export function track<E extends TrackEvent>(name: E['name'], data: E['data']): void {
  try {
    window.umami?.track(name, data as unknown as Record<string, unknown>)
  } catch {
    // Swallow analytics errors — they must never affect the app.
  }
}
