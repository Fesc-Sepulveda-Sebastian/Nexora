export type UserRole = 'marca' | 'creador' | 'administrador';

export interface User {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  privacy_status: string;
  profile?: Profile;
  created_at: string;
}

export interface Profile {
  id: string;
  user_id: string;
  display_name: string;
  bio?: string;
  location_declared?: string;
  niche?: string;
  languages?: string;
  avatar_url?: string;
  portfolio_samples?: string;
  verified_reviews_count: number;
  average_rating: number;
  current_media_kit_version: number;
}

export interface DeliverableItem {
  format: string; // Reel, Story, TikTok, Post, Video
  qty: number;
  specs: string;
}

export interface SelectionCriteria {
  min_followers: number;
  location?: string;
  platforms: string[];
}

export interface Campaign {
  id: string;
  brand_id: string;
  title: string;
  objective: string;
  niche: string;
  status: 'Borrador' | 'Publicada' | 'En_Ejecucion' | 'Cerrada' | 'Cancelada';
  version_id: number;
  start_date?: string;
  end_date?: string;
  compensation_type: 'pago_fijo' | 'canje' | 'hibrido' | 'comision';
  budget: number;
  compensation_notes?: string;
  deliverables?: DeliverableItem[];
  selection_criteria?: SelectionCriteria;
  total_cost?: number;
  attributable_benefit?: number;
  created_at: string;
  updated_at: string;
}

export interface Application {
  id: string;
  campaign_id: string;
  creator_id: string;
  creative_proposal: string;
  media_kit_snapshot_version: number;
  media_kit_data?: string;
  status: 'Recibida' | 'En_Revision' | 'Aceptada' | 'Rechazada';
  idempotency_key?: string;
  evidences?: DeliverableEvidence[];
  created_at: string;
  updated_at: string;
}

export interface DeliverableEvidence {
  id: string;
  application_id: string;
  deliverable_name: string;
  file_url: string;
  file_hash_sha256: string;
  file_size_mb: number;
  external_live_url?: string;
  status: 'Pendiente' | 'En_Revision' | 'Aprobado' | 'Rechazado';
  review_notes?: string;
  submitted_at: string;
  reviewed_at?: string;
}

export interface CollaborationAgreement {
  id: string;
  application_id: string;
  campaign_id: string;
  brand_id: string;
  creator_id: string;
  version_id: number;
  scope_description: string;
  deliverables_terms: string;
  compensation_amount: number;
  deadline: string;
  brand_accepted: boolean;
  brand_accepted_at?: string;
  creator_accepted: boolean;
  creator_accepted_at?: string;
  status: 'Acuerdo_Pendiente' | 'En_Ejecucion' | 'En_Revision' | 'Cerrada' | 'Disputa';
  created_at: string;
  updated_at: string;
}

export interface MetricSnapshot {
  plataforma: string;
  cuenta_id: string;
  periodo: string;
  fecha_captura_utc: string;
  estado: string;
  esquema_version: string;
  fuente_origen: string;
  followers_count: number;
  engagement: {
    interactions: number;
    reach_or_impressions: number;
    formula_string: string;
    calculated_percentage: number;
  };
  avg_impressions: number;
  avg_video_views?: number;
  top_locations: Array<{ city: string; pct: number }>;
  authenticity_notice: string;
}

export interface MediaKitData {
  creator_id: string;
  display_name: string;
  bio?: string;
  location_declared?: string;
  niche?: string;
  languages: string;
  avatar_url?: string;
  version: number;
  verified_reviews_count: number;
  average_rating: number;
  portfolio_samples: any[];
  connected_metrics: MetricSnapshot[];
  declared_metrics: any[];
  generated_at_utc: string;
}

export interface MatchCriterion {
  criterion: string;
  detail: string;
  weight_score: number;
}

export interface CreatorRecommendation {
  creator_id: string;
  display_name: string;
  niche: string;
  location_declared: string;
  avatar_url?: string;
  average_rating: number;
  total_score: number;
  matching_criteria: MatchCriterion[];
  rule_version: string;
}

export interface Message {
  id: string;
  collaboration_id: string;
  sender_id: string;
  sender_name?: string;
  recipient_id: string;
  content: string;
  is_read: boolean;
  created_at: string;
}

export interface ROICalculatorResult {
  roi_percentage: number;
  total_cost: number;
  attributable_benefit: number;
  net_profit: number;
  currency: string;
  cost_source: string;
  benefit_source: string;
  calculated_at_utc: string;
  disclaimer: string;
}
