// 移动端类型定义 — 与 Web 端保持一致，便于后续共享

export interface User {
  id: number
  username: string
  email: string | null
  real_name: string | null
  role: UserRole
  org_id: number | null
}

export type UserRole = 'super_admin' | 'admin' | 'manager' | 'operator' | 'viewer'

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface Ingredient {
  id: number
  name: string
  code: string
  category_id: number | null
  category_name?: string
  supplier_id: number | null
  supplier_name?: string
  unit: string
  current_stock: number
  safety_stock: number
  specification: string | null
  is_active: boolean
  org_id: number | null
}

export interface Supplier {
  id: number
  name: string
  code: string
  contact_person: string | null
  phone: string | null
  email: string | null
  address: string | null
  status: 'active' | 'blacklisted' | 'suspended'
  rating: number
  org_id: number | null
}

export interface StockIn {
  id: number
  batch_no: string
  ingredient_id: number
  ingredient_name?: string
  quantity: number
  unit_price: number
  total_price: number
  supplier_id: number | null
  supplier_name?: string
  production_date: string | null
  expiry_date: string | null
  remark: string | null
  created_at: string
}

export interface StockOut {
  id: number
  ingredient_id: number
  ingredient_name?: string
  quantity: number
  unit_price: number
  total_price: number
  purpose: string | null
  department: string | null
  remark: string | null
  created_at: string
}

export interface TraceRecord {
  trace_code: string
  ingredient_name: string | null
  supplier_name: string | null
  batch_no: string | null
  production_date: string | null
  expiry_date: string | null
  test_report: string | null
  quarantine_cert: string | null
  created_at: string
}
