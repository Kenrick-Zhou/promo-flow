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
export type ContentType = 'image' | 'video'
export type AiStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface Content {
  id: number
  title: string | null
  description: string | null
  tags: string[]
  content_type: ContentType
  status: ContentStatus
  file_key: string
  file_url: string | null
  file_size: number | null
  ai_summary: string | null
  ai_keywords: string[]
  ai_status: AiStatus
  ai_error: string | null
  ai_processed_at: string | null
  uploaded_by: number
  uploaded_by_name: string
  category_id: number | null
  category_name: string | null
  primary_category_name: string | null
  created_at: string
  updated_at: string
}

export interface ContentCreate {
  description?: string
  tag_names: string[]
  content_type: ContentType
  category_id: number
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

// ============================================================
// System Management Types (categories, tags)
// ============================================================

export interface Category {
  id: number
  name: string
  description: string
  parent_id: number | null
  sort_order: number
  created_at: string
  updated_at: string
}

export interface CategoryTree {
  id: number
  name: string
  description: string
  parent_id: number | null
  sort_order: number
  children: CategoryTree[]
  created_at: string
  updated_at: string
}

export interface CategoryCreate {
  name: string
  description: string
  parent_id?: number | null
  sort_order?: number
}

export interface CategoryUpdate {
  name?: string
  description?: string
  sort_order?: number
}

export interface Tag {
  id: number
  name: string
  is_system: boolean
  sort_order: number
  created_at: string
}

export interface TagCreate {
  name: string
  is_system?: boolean
  sort_order?: number
}

export interface TagUpdate {
  name?: string
  is_system?: boolean
  sort_order?: number
}

export interface TagReorderItem {
  id: number
  sort_order: number
}
