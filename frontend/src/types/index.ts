export interface User {
  id: number
  name: string
  avatar_url: string | null
  role: 'employee' | 'reviewer' | 'admin'
  feishu_open_id: string
  created_at: string
}

export interface TokenOut {
  access_token: string
  token_type: string
  user: User
}

export type ContentStatus = 'pending' | 'approved' | 'rejected'
export type ContentType = 'image' | 'video' | 'document'

export interface Content {
  id: number
  title: string
  description: string | null
  tags: string[]
  content_type: ContentType
  status: ContentStatus
  file_key: string
  file_url: string | null
  file_size: number | null
  ai_summary: string | null
  ai_keywords: string[]
  uploaded_by: number
  created_at: string
  updated_at: string
}

export interface ContentCreate {
  title: string
  description?: string
  tags: string[]
  content_type: ContentType
}

export interface ContentListOut {
  total: number
  items: Content[]
}

export interface AuditLog {
  id: number
  content_id: number
  auditor_id: number
  audit_status: string
  audit_comments: string | null
  audit_time: string
}

export interface SearchResultItem {
  content: Content
  score: number
}
