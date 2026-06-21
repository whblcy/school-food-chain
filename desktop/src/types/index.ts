// API 类型定义 — 与后端 schemas.py 对齐

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
  blacklist_reason: string | null
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
  batch_number: string | null
  inspector1_id: number | null
  inspector2_id: number | null
  operator_id: number | null
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
  operator_id: number | null
  remark: string | null
  created_at: string
}

export interface InventoryCheck {
  id: number
  ingredient_id: number
  ingredient_name?: string
  system_stock: number
  actual_stock: number
  difference: number
  operator_id: number | null
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

export interface AuditLog {
  id: number
  user_id: number | null
  username: string | null
  action: string
  target_type: string | null
  target_id: number | null
  ip_address: string | null
  user_agent: string | null
  old_value: Record<string, unknown> | null
  new_value: Record<string, unknown> | null
  created_at: string
}

export interface MonthlySummary {
  year: number
  month: number
  total_in: number
  total_out: number
  balance: number
}

export interface YearlyTrendItem {
  month: number
  in_amount: number
  out_amount: number
}

export interface GovDashboard {
  school_count: number
  today_stock_in: number
  today_stock_out: number
  low_stock_alert: number
  supplier_count: number
  active_supplier_count: number
  weekly_trend: Array<{
    date: string
    stock_in: number
    stock_out: number
  }>
}

export interface PaginatedResponse<T> {
  total: number
  items: T[]
}

// 报表聚合类型
export interface StockSummaryItem {
  category: string | null
  count: number
  total_stock: number
}

export interface LowStockItem {
  id: number
  name: string
  code: string | null
  unit: string | null
  current: number
  safety: number
  current_stock: number
  safety_stock: number
}

export interface CategoryBreakdownItem {
  category: string | null
  amount: number
}

// 组织/学校
export interface Org {
  id: number
  name: string
  code: string | null
  address: string | null
  contact_person: string | null
  contact_phone: string | null
  org_type: string | null
  is_active: boolean
}

export interface GovSchoolListItem {
  id: number
  name: string
  code: string | null
  ingredient_count: number
  today_purchase: number
  low_stock_count: number
  address?: string | null
  contact_person?: string | null
  contact_phone?: string | null
}

export interface GovSchoolDetail {
  school: GovSchoolListItem
  ingredients: Array<{
    name: string
    current_stock: number
    safety_stock: number
    status: string
  }>
  ingredient_total: number
  recent_stock_in: Array<{
    batch_no: string
    ingredient_name: string
    quantity: number
    total_price: number
  }>
  recent_inventory_checks: Array<Record<string, unknown>>
}

export interface GovAlert {
  id?: number
  type: string
  level: 'warning' | 'critical'
  title: string
  message: string
  school_name?: string | null
  created_at: string
}

// 用户扩展（含组织信息）
export interface UserWithOrg extends User {
  org_name?: string | null
  phone?: string | null
  is_active?: boolean
  last_login?: string | null
}
