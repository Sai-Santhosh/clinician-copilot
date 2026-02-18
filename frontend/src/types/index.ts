// User types
export interface User {
  id: number;
  email: string;
  role: 'admin' | 'clinician' | 'viewer';
  is_active: boolean;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

// Patient types
export interface Patient {
  id: number;
  name: string;
  external_id?: string;
  dob?: string;
  created_at: string;
}

export interface PatientCreate {
  name: string;
  external_id?: string;
  dob?: string;
}

// Session types
export interface Session {
  id: number;
  patient_id: number;
  created_by_user_id: number;
  transcript_length: number;
  created_at: string;
  has_ai_suggestions: boolean;
  latest_version_id?: number;
  latest_version_status?: string;
}

export interface SessionCreate {
  transcript: string;
}

// Citation types
export interface Citation {
  text: string;
  start_offset?: number;
  end_offset?: number;
}

// SOAP types
export interface SOAPSection {
  content: string;
  citations: Citation[];
}

export interface SOAPNote {
  subjective: SOAPSection;
  objective: SOAPSection;
  assessment: SOAPSection;
  plan: SOAPSection;
}

// Diagnosis types
export interface DiagnosisItem {
  diagnosis: string;
  confidence: number;
  rationale: string;
  citations: Citation[];
}

export interface DiagnosisSuggestion {
  primary?: DiagnosisItem;
  differential: DiagnosisItem[];
}

// Medication types
export interface MedicationItem {
  medication: string;
  education: string;
  warnings: string[];
  citations: Citation[];
}

export interface MedicationEducation {
  medications: MedicationItem[];
  general_guidance?: string;
}

// Safety plan types
export interface SafetyPlanItem {
  item: string;
  completed: boolean;
  notes?: string;
  citations: Citation[];
}

export interface SafetyPlan {
  warning_signs: SafetyPlanItem[];
  coping_strategies: SafetyPlanItem[];
  support_contacts: SafetyPlanItem[];
  professional_contacts: SafetyPlanItem[];
  environment_safety: SafetyPlanItem[];
  reasons_for_living: SafetyPlanItem[];
}

// AI Generation types
export interface GenerateRequest {
  prompt_version?: string;
  model_name?: string;
  mode?: 'full' | 'safe';
  temperature?: number;
}

export interface GenerateResponse {
  ai_suggestion_id: number;
  note_version_id: number;
  injection_detected: boolean;
  safety_mode: boolean;
  warning_message?: string;
  soap: SOAPNote;
  diagnosis: DiagnosisSuggestion;
  medications: MedicationEducation;
  safety_plan: SafetyPlan;
  gemini_latency_ms: number;
}

// Note version types
export interface NoteVersion {
  id: number;
  session_id: number;
  version_number: number;
  status: 'draft' | 'final';
  soap_json?: string;
  dx_json?: string;
  meds_json?: string;
  safety_json?: string;
  ai_suggestion_id?: number;
  created_by_user_id: number;
  created_at: string;
}

export interface NoteVersionUpdate {
  soap_json?: string;
  dx_json?: string;
  meds_json?: string;
  safety_json?: string;
}

// AI Suggestion types
export interface AiSuggestion {
  id: number;
  session_id: number;
  model_name: string;
  prompt_version: string;
  injection_flag: boolean;
  safety_mode: boolean;
  gemini_latency_ms?: number;
  created_at: string;
}

// Audit log types
export interface AuditLog {
  id: number;
  actor_user_id: number;
  action: string;
  entity_type: string;
  entity_id: number;
  before_hash?: string;
  after_hash?: string;
  metadata_json?: string;
  created_at: string;
}

// API response types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
}
