import type { ContentType } from '@/types'

/**
 * Generate an OSS image-processing thumbnail URL.
 *
 * - Image: proportional resize via `image/resize,m_lfit`
 * - Video: first-frame snapshot via `video/snapshot`
 * - Document / null URL: returns `null`
 *
 * @see https://help.aliyun.com/zh/oss/user-guide/resize-an-image-based-on-the-specified-height-and-width
 * @see https://help.aliyun.com/zh/oss/user-guide/video-snapshots
 */
export function getThumbnailUrl(
  fileUrl: string | null,
  contentType: ContentType,
  width: number = 400,
  height: number = 400,
): string | null {
  if (!fileUrl) return null

  if (contentType === 'image') {
    return `${fileUrl}?x-oss-process=image/resize,m_lfit,w_${width},h_${height}`
  }

  if (contentType === 'video') {
    return `${fileUrl}?x-oss-process=video/snapshot,t_0,f_jpg,w_${width},h_0,m_fast`
  }

  return null
}
