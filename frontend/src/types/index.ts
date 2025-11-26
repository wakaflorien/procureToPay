export interface User {
  id: number;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  role: 'staff' | 'approver_level_1' | 'approver_level_2' | 'finance' | 'admin';
  department?: string;
  is_superuser?: boolean;
}

export interface RequestItem {
  id?: number;
  name: string;
  description?: string;
  quantity: number;
  unit_price: number;
  total_price?: number;
}

export interface Approval {
  id: number;
  approver: User;
  level: string;
  action: 'approved' | 'rejected' | 'cancelled';
  comments: string;
  created_at: string;
}

export interface PurchaseRequest {
  id: string;
  title: string;
  description: string;
  amount: string;
  status: 'pending' | 'approved' | 'rejected' | 'cancelled';
  created_by: User | string; // User object in detail view, string in list view
  created_at: string;
  updated_at: string;
  proforma?: string;
  purchase_order?: string;
  receipt?: string;
  proforma_data?: ProformaData;
  purchase_order_data?: PurchaseOrderData;
  receipt_data?: ReceiptData;
  receipt_validation_result?: ReceiptValidationResult;
  requires_level_1_approval: boolean;
  requires_level_2_approval: boolean;
  level_1_approved: boolean;
  level_2_approved: boolean;
  items: RequestItem[];
  approvals: Approval[];
  can_be_edited?: boolean;
  can_be_approved?: boolean;
  has_user_approved?: boolean;
  has_user_rejected?: boolean;
  needs_receipt_upload?: boolean;
}

export interface ProformaData {
  vendor?: string;
  amount?: number;
  items?: ProformaItem[];
  terms?: string;
  extracted_text?: string;
  error?: string;
}

export interface ProformaItem {
  name: string;
  quantity: number;
  price?: number;
  unit_price?: number;
  total?: number;
}

export interface PurchaseOrderData {
  po_number?: string;
  request_id?: string;
  vendor?: string;
  amount?: number;
  total_amount?: number;
  items?: RequestItem[];
  terms?: string;
  created_at?: string;
}

export interface ReceiptData {
  vendor?: string;
  amount?: number;
  items?: ProformaItem[];
}

export interface ReceiptValidationResult {
  is_valid: boolean;
  errors?: string[];
  warnings?: string[];
  receipt_data?: ReceiptData;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  password2: string;
  first_name?: string;
  last_name?: string;
  role?: string;
  department?: string;
}

export interface AuthResponse {
  access: string;
  refresh: string;
  user?: User;
}

