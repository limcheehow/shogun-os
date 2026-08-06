export type StatusLevel = 'online' | 'degraded' | 'offline' | 'unknown' | 'pending';

export type DepartmentKey =
  | 'hr'
  | 'finance'
  | 'crm'
  | 'marketing'
  | 'compliance'
  | 'support'
  | 'engineering'
  | 'projects'
  | 'product'
  | 'procurement';

export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url?: string | null;
  first_login: boolean;
  must_change_password: boolean;
  company_id?: string | null;
  role?: string;
}

export interface Company {
  id: string;
  name: string;
  logo_url?: string | null;
  timezone: string;
}

export interface ProviderConfig {
  provider?: string;
  api_key?: string;
  subdomain?: string;
  base_url?: string;
  extra?: Record<string, string>;
}

export interface Department {
  key: DepartmentKey;
  name: string;
  persona: string;
  description: string;
  color: string;
  icon: string;
  active: boolean;
  status: StatusLevel;
  gateway_status?: StatusLevel;
  provider_status?: StatusLevel;
  provider_config?: ProviderConfig;
  profile_name?: string;
}

export interface OnboardingState {
  step: number;
  selected_departments: DepartmentKey[];
  company?: Partial<Company>;
  department_configs?: Partial<Record<DepartmentKey, ProviderConfig>>;
  completed: boolean;
  public_url?: string | null;
  subdomain?: string | null;
  go_live?: {
    ok?: boolean;
    public_url?: string | null;
    subdomain?: string | null;
    message?: string | null;
    tunnel?: Record<string, unknown>;
  };
}

export interface BrainPage {
  slug: string;
  title: string;
  type?: string;
  summary?: string;
  updated_at?: string;
  content?: string;
  tags?: string[];
}

export interface BrainLink {
  slug: string;
  title?: string;
  link_type?: string;
}

export interface DocumentArtifact {
  id: string;
  name: string;
  mime_type?: string;
  size_bytes?: number;
  created_at?: string;
  updated_at?: string;
  url?: string;
  preview_url?: string;
  description?: string;
}

export interface ChatToolCall {
  id: string;
  name: string;
  arguments?: unknown;
  result?: unknown;
  status?: 'running' | 'done' | 'error';
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  created_at?: string;
  tool_calls?: ChatToolCall[];
  streaming?: boolean;
}

export interface AuthResponse {
  access_token: string;
  token_type?: string;
  user: User;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
}

export interface ConnectionTestResult {
  ok: boolean;
  message: string;
  details?: Record<string, unknown>;
}

export const DEPARTMENT_CATALOG: Record<
  DepartmentKey,
  Omit<Department, 'active' | 'status' | 'gateway_status' | 'provider_status' | 'provider_config'>
> = {
  hr: {
    key: 'hr',
    name: 'HR',
    persona: 'Jinzai',
    description: 'People ops, leave, recruitment, and policy guidance.',
    color: '#ec4899',
    icon: 'Users',
    profile_name: 'hr-manager',
  },
  finance: {
    key: 'finance',
    name: 'Finance',
    persona: 'Koku',
    description: 'Budgets, expenses, grants, and financial reporting.',
    color: '#10b981',
    icon: 'Wallet',
    profile_name: 'finance-manager',
  },
  crm: {
    key: 'crm',
    name: 'CRM',
    persona: 'Eigyo',
    description: 'Pipeline, accounts, and sales intelligence.',
    color: '#3b82f6',
    icon: 'Handshake',
    profile_name: 'crm-manager',
  },
  marketing: {
    key: 'marketing',
    name: 'Marketing',
    persona: 'Kokuchi',
    description: 'Campaigns, content, and brand messaging.',
    color: '#f59e0b',
    icon: 'Megaphone',
    profile_name: 'marketing-manager',
  },
  compliance: {
    key: 'compliance',
    name: 'Compliance',
    persona: 'Junshu',
    description: 'Policies, audits, and regulatory tracking.',
    color: '#8b5cf6',
    icon: 'Shield',
    profile_name: 'compliance-manager',
  },
  support: {
    key: 'support',
    name: 'Support',
    persona: 'Shien',
    description: 'Tickets, SLAs, and customer success workflows.',
    color: '#06b6d4',
    icon: 'LifeBuoy',
    profile_name: 'customer-support',
  },
  engineering: {
    key: 'engineering',
    name: 'Engineering',
    persona: 'Gijutsu',
    description: 'Codebase ops, deployments, and technical delivery.',
    color: '#6366f1',
    icon: 'Code2',
    profile_name: 'engineering-manager',
  },
  projects: {
    key: 'projects',
    name: 'Projects',
    persona: 'Keikaku',
    description: 'Delivery plans, scrum cadences, and milestones.',
    color: '#f97316',
    icon: 'Kanban',
    profile_name: 'project-manager',
  },
  product: {
    key: 'product',
    name: 'Product',
    persona: 'Seihin',
    description: 'Roadmaps, research, and product decisions.',
    color: '#14b8a6',
    icon: 'Boxes',
    profile_name: 'product-manager',
  },
  procurement: {
    key: 'procurement',
    name: 'Procurement',
    persona: 'Chotatsu',
    description: 'Purchase orders, vendors, and contract lifecycle.',
    color: '#ef4444',
    icon: 'Package',
    profile_name: 'procurement-manager',
  },
};

export const DEPARTMENT_KEYS = Object.keys(DEPARTMENT_CATALOG) as DepartmentKey[];

// ─── Dashboard Types ───

export interface DashboardTab {
  id: string;
  label: string;
  icon: string;
}

// ─── Staff Management Types ───

export interface StaffAssignment {
  department: string;
  title: string;
  department_name?: string;
  department_id?: number;
  user_id?: number;
  id?: number;
}

export interface StaffMember {
  id: number;
  email: string;
  name: string;
  role: 'admin' | 'hr_manager' | 'user';
  first_login: boolean;
  is_temporary_password: boolean;
  created_at?: string;
  assignments: StaffAssignment[];
  phone?: string;
  slack_user_id?: string;
  telegram_user_id?: string;
  employee_id?: string;
  manager_name?: string;
  manager_id?: number;
  avatar_url?: string;
  source?: string;
  last_synced_at?: string;
}

export interface AccessInfo {
  role: string;
  assigned_departments: { department: string; title: string; department_name: string }[];
  has_access: boolean;
}

export interface CreateStaffPayload {
  email: string;
  name: string;
  role: string;
  assignments: { department: string; title: string }[];
  phone?: string;
  slack_user_id?: string;
  telegram_user_id?: string;
  employee_id?: string;
  manager_email?: string;
}

export interface DashboardConfig {
  enabled: boolean;
  tabs: DashboardTab[];
}

export interface ManagerEntry {
  owner: string;
  salesMTD: number;
  salesQTD: number;
  salesYTD: number;
  deals: number;
  wonDeals: number;
  pipelineValue: number;
  weightedPipeline: number;
  closeThisMonth: number;
  closeThisQ: number;
  closeNextQ: number;
  closeThisYear: number;
  winRate: number;
}

export interface PartnerStatsEntry {
  partner: string;
  booking: number;
  dealsWon: number;
  pipelineDeals: number;
  pipelineValue: number;
  winRate: number;
  avgDealSize: number;
  primaryOwner: string;
}

export interface FunnelEntry {
  stage: string;
  count: number;
  value: number;
}

export interface MonthEntry {
  month: string;
  value: number;
}

export interface PriorityEntry {
  priority: string;
  count: number;
}

export interface ProductEntry {
  product: string;
  value: number;
  count: number;
}

export interface ManagerRiskEntry {
  owner: string;
  atRiskDeals: number;
  atRiskValue: number;
}

export interface PartnerRiskEntry {
  partner: string;
  atRiskDeals: number;
  atRiskValue: number;
  primaryOwner: string;
}

export interface DealRow {
  slug: string;
  title: string;
  customer: string;
  amount: number;
  stage: string;
  priority: string;
  owner: string;
  partner: string | null;
  closeDate: string;
  winProbability: number;
  daysInStage: number;
  hot: boolean;
}

export interface CeoDashboardStats {
  salesMTD: number;
  salesQTD: number;
  salesYTD: number;
  totalPipelineValue: number;
  weightedPipelineValue: number;
  pipelineCoverage: number;
  winRate: number;
  avgDealSize: number;
  salesCycleDays: number;
  totalActiveDeals: number;
  hotDeals: number;
  warmDeals: number;
  coldDeals: number;
  wonDeals: number;
  byManager: ManagerEntry[];
  byPartner: PartnerStatsEntry[];
  byStage: FunnelEntry[];
  byMonth: MonthEntry[];
  byPriority: PriorityEntry[];
  wonByMonth: MonthEntry[];
  byProduct: ProductEntry[];
  atRiskByManager: ManagerRiskEntry[];
  atRiskByPartner: PartnerRiskEntry[];
  byManagerByPartner: { owner: string; partner: string; deals: number }[];
  topDeals: DealRow[];
}

export const TIMEZONES = [
  'Asia/Kuala_Lumpur',
  'Asia/Singapore',
  'Asia/Jakarta',
  'Asia/Bangkok',
  'Asia/Hong_Kong',
  'Asia/Tokyo',
  'Asia/Shanghai',
  'Asia/Kolkata',
  'Australia/Sydney',
  'Europe/London',
  'Europe/Berlin',
  'America/New_York',
  'America/Los_Angeles',
  'America/Chicago',
  'UTC',
];

// ─── Finance Dashboard Types ───

export interface FinanceRiskAlert {
  type: 'concentration' | 'overrun' | 'ar_overdue';
  level: 'warning' | 'critical';
  message: string;
}

export interface FinanceTrendPoint {
  month: string;
  revenue?: number;
  opex?: number;
  net?: number;
  cash?: number;
  netFlow?: number;
}

export interface BankAccount {
  name: string;
  currency: string;
  balance: number;
  balance_myr: number;
  last_reconciled?: string;
}

export interface FxPosition {
  currency: string;
  long: number;
  short: number;
  net: number;
  bnm_fea_compliant: boolean;
}

export interface Forecast13wScenario {
  week: string;
  inflow: number;
  outflow: number;
  net: number;
  cumulative: number;
}

export interface ArAgingBuckets {
  bucket_0_30: number;
  bucket_31_60: number;
  bucket_61_90: number;
  bucket_90_plus: number;
}

export interface DunningItem {
  invoice_no: string;
  customer: string;
  due_date: string;
  amount: number;
  aging_days: number;
  bucket: '0-30' | '31-60' | '61-90' | '90+';
  dunning_status: string;
}

export interface ApBillItem {
  bill_no: string;
  vendor: string;
  due_date: string;
  amount: number;
  match_status: 'Matched' | 'PO Mismatch' | 'Missing GRN';
  approval_status: 'Pending' | 'Approved' | 'Paid' | 'On Hold';
}

export interface BvaDeptItem {
  department: string;
  budget_ytd: number;
  actual_ytd: number;
  variance: number;
  variance_pct: number;
}

export interface UnitEconomics {
  gross_margin_pct: number;
  contribution_margin_pct: number;
  cac: number;
  ltv: number;
  ltv_cac_ratio: number;
}

export interface ClientConcentrationItem {
  name: string;
  revenue_ytd: number;
  revenue_pct: number;
}

export interface CloseChecklistItem {
  id: string;
  label: string;
  completed: boolean;
}

export interface StatutoryItem {
  name: string;
  due_date: string;
  status: 'Pending' | 'Submitted' | 'Overdue';
  amount?: number;
}

export interface SstReadiness {
  draft_status: string;
  taxable_sales: number;
  sst_liability: number;
}

export interface Cp58Item {
  contractor_name: string;
  ic_or_reg: string;
  total_paid_ytd: number;
  threshold_exceeded: boolean;
}

export interface WhtQueueItem {
  vendor: string;
  country: string;
  payment_amount: number;
  wht_rate: number;
  wht_amount: number;
  section: string;
}

export interface ExpenseClaimItem {
  employee: string;
  claim_date: string;
  amount: number;
  category: string;
  receipt_attached: boolean;
  sst_compliant: boolean;
  policy_exceeded: boolean;
  audit_status: 'Approved' | 'Flagged' | 'Rejected';
}

export interface FinanceDashboardStats {
  // Tab 1 — Executive Pulse
  totalLiquidCash: number;
  netMonthlyBurn: number;
  cashRunwayMonths: number;
  runwayStatus: 'healthy' | 'caution' | 'critical' | 'unknown';
  revenueMTD: number;
  revenueYTD: number;
  grossMargin: number;
  ebitdaMargin: number;
  unpaidStatutory: number;
  riskAlerts: FinanceRiskAlert[];
  revenueOpexTrend: FinanceTrendPoint[];
  cashFlowTrend: FinanceTrendPoint[];
  // Tab 2 — Cash & Runway
  bankAccounts: BankAccount[];
  fxPositions: FxPosition[];
  forecast13w: { conservative: Forecast13wScenario[]; expected: Forecast13wScenario[]; optimistic: Forecast13wScenario[] };
  fixedOpex: number;
  variableOpex: number;
  // Tab 3 — AR & AP
  totalAR: number;
  arOverdue30: number;
  dso: number;
  totalAP: number;
  apOverdue: number;
  dpo: number;
  arAging: ArAgingBuckets;
  dunningQueue: DunningItem[];
  apBills: ApBillItem[];
  // Tab 4 — BvA & Unit Economics
  bvaDepartments: BvaDeptItem[];
  unitEconomics: UnitEconomics;
  clientConcentration: ClientConcentrationItem[];
  // Tab 5 — Close & Tax
  closeChecklist: CloseChecklistItem[];
  statutorySchedule: StatutoryItem[];
  sstReadiness: SstReadiness;
  cp58Register: Cp58Item[];
  whtQueue: WhtQueueItem[];
  expenseClaimAudit: ExpenseClaimItem[];
}

// ─── Procurement Dashboard Types ───

export type ProcurementRiskAlertType = 'safety_breach' | 'dead_stock' | 'lead_time_delay';

export interface ProcurementRiskAlert {
  type: ProcurementRiskAlertType;
  level: 'warning' | 'critical';
  message: string;
}

export interface InventoryValuationByCategory {
  category: string;
  value: number;
}

export interface ProcurementSpendTrendPoint {
  month: string;
  spend?: number;
  budget?: number;
}

export interface SkuItem {
  sku: string;
  item_name: string;
  category: string;
  unit_cost: number;
  current_qty: number;
  safety_reorder_point: number;
  location_bin: string;
  status: 'In Stock' | 'Low Stock' | 'Out of Stock' | 'Overstocked';
}

export interface AbcParetoClass {
  class_label: 'A' | 'B' | 'C';
  sku_count: number;
  sku_pct: number;
  capital_value: number;
  value_pct: number;
}

export interface ExecutiveApprovalRow {
  po_number: string;
  vendor: string;
  order_date: string;
  total_amount: number;
  requester_dept: string;
  threshold_myr: number;
  approval_status: 'Pending Executive Approval' | 'Approved' | 'Rejected' | 'Clarification Requested';
}

export interface DeadSlowStockItem {
  sku: string;
  item_name: string;
  category: string;
  current_qty: number;
  days_since_last_movement: number;
  months_of_cover: number;
  total_tied_value: number;
  action_recommendation: '25% Promo Discount' | 'Vendor Clearance Return' | 'Bundle Promo with Top SKU' | 'Scrap / Write-off';
}

export interface WarehouseBinCapacity {
  location: string;
  used: number;
  capacity: number;
  utilisation_pct: number;
}

export interface StockMovementEntry {
  timestamp: string;
  sku: string;
  item_name: string;
  movement_type: '+ Receive' | '- Issue' | '~ Adjustment' | '! Damage' | '↺ Return';
  quantity: number;
  reference_id: string;
  location_id: string;
  actor: string;
}

export interface MovementTypeDistribution {
  movement_type: string;
  count: number;
  quantity: number;
}

export interface PoPipelineStage {
  stage: string;
  count: number;
  value: number;
}

export interface PurchaseOrderRow {
  po_number: string;
  vendor: string;
  order_date: string;
  expected_delivery: string;
  total_amount: number;
  fulfillment_status: 'Draft' | 'Pending Approval' | 'Issued to Vendor' | 'Partially Received' | 'Fully Received & Billed';
  approval_status: 'Draft' | 'Pending Approval' | 'Approved' | 'Issued' | 'Cancelled';
}

export interface VendorScorecardRow {
  vendor: string;
  preferred_category: string;
  ytd_spend: number;
  on_time_delivery_rate: number;
  quality_acceptance_rate: number;
  sla_status: 'Top Tier' | 'Satisfactory' | 'Under Review';
}

export interface VendorSpendShare {
  vendor: string;
  spend: number;
  spend_pct: number;
}

export interface AccountingBridgeStatus {
  enabled: boolean;
  provider: 'Bukku' | 'QBO' | 'Xero' | 'None';
  connected: boolean;
  last_sync?: string;
}

export interface PoBillConversionRow {
  po_number: string;
  vendor: string;
  date_received: string;
  total_amount: number;
  sync_status: 'Ready to Sync' | 'Synced to Bukku' | 'Sync Error';
}

export interface GlValuationReconciliationRow {
  account_code: string;
  physical_stock_value: number;
  gl_book_value: number;
  variance: number;
  variance_pct: number;
  reconciliation_status: 'Reconciled' | 'Variance Flagged';
}

// Tab 6 — Purchase Requisitions (PR)
export interface PurchaseRequisition {
  pr_number: string;
  requester: string;
  department: string;
  item_description: string;
  category: string;
  estimated_amount: number;
  priority: 'Low' | 'Medium' | 'High' | 'Urgent';
  status: 'Draft' | 'Pending Approval' | 'Approved' | 'Converted to RFQ/PO' | 'Rejected';
  created_at: string;
  justification?: string;
}

// Tab 7 — RFQ & Vendor Sourcing
export interface RfqVendorQuote {
  vendor: string;
  unit_price: number;
  total_amount: number;
  lead_time_days: number;
  payment_terms: string;
  sla_status: string;
  selected?: boolean;
}

export interface RfqComparison {
  rfq_id: string;
  pr_number: string;
  item_description: string;
  category: string;
  target_qty: number;
  budget_myr: number;
  status: 'Open Sourcing' | 'Vendor Selected' | 'PO Issued';
  quotes: RfqVendorQuote[];
}

// Tab 8 — Barcode Tagging & Scan Counter
export interface BarcodeStockUnit {
  barcode_id: string;
  sku: string;
  item_name: string;
  serial_no: string;
  location_bin: string;
  status: 'In Store' | 'Issued' | 'Returned' | 'Quarantine';
  assigned_to?: string;
  last_scan_timestamp: string;
}

export interface BarcodeBatchLog {
  batch_id: string;
  action_type: 'GRN Receipt Tagging' | 'Stock Issuance (Scan OUT)' | 'Stock Return (Scan IN)';
  reference_id: string;
  actor: string;
  timestamp: string;
  total_items: number;
  units: BarcodeStockUnit[];
}

// Tab 9 — 3-Way Match Verification
export interface ThreeWayMatchItem {
  match_id: string;
  po_number: string;
  grn_number: string;
  invoice_number: string;
  vendor: string;
  po_amount: number;
  grn_received_amount: number;
  invoice_amount: number;
  variance_amount: number;
  variance_pct: number;
  match_status: '100% Match' | 'Within Tolerance' | 'Variance Exceeded';
  ap_approval_status: 'Pending AP Review' | 'Approved for Payment' | 'Flagged to Procurement';
}

export interface ProcurementDashboardStats {
  // Tab 1 — Executive Procurement & Reorder Pulse
  totalInventoryValuation: number;
  totalActiveSkus: number;
  lowStockAlerts: number;
  deadSlowStockCapital: number;
  openPoCount: number;
  openPoValue: number;
  procurementSpendMtd: number;
  procurementSpendBudgetMtd: number;
  riskAlerts: ProcurementRiskAlert[];
  valuationByCategory: InventoryValuationByCategory[];
  spendVsBudgetTrend: ProcurementSpendTrendPoint[];
  // Tab 2 — Inventory Catalog & Dead/Slow Stock
  skuCatalog: SkuItem[];
  deadSlowStock: DeadSlowStockItem[];
  warehouseBinCapacity: WarehouseBinCapacity[];
  // Tab 3 — Stock Movement Audit Log
  stockMovements: StockMovementEntry[];
  movementTypeDistribution: MovementTypeDistribution[];
  shrinkageFlagItems: string[];
  // Tab 4 — Purchase Orders & Vendor Scorecard
  poPipeline: PoPipelineStage[];
  activePurchaseOrders: PurchaseOrderRow[];
  executiveApprovalQueue: ExecutiveApprovalRow[];
  vendorScorecard: VendorScorecardRow[];
  vendorSpendConcentration: VendorSpendShare[];
  // Tab 5 — Accounting Bridge & Valuation Reconciliation
  accountingBridge: AccountingBridgeStatus;
  poBillConversionQueue: PoBillConversionRow[];
  glValuationReconciliation: GlValuationReconciliationRow[];
  // Tab 6 — Purchase Requisitions (PR)
  purchaseRequisitions?: PurchaseRequisition[];
  // Tab 7 — RFQ & Vendor Sourcing
  rfqComparisons?: RfqComparison[];
  // Tab 8 — Barcode Tagging & Scan Counter
  barcodeBatches?: BarcodeBatchLog[];
  // Tab 9 — 3-Way Match Verification
  threeWayMatches?: ThreeWayMatchItem[];
}
