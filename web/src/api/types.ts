export type Band = "High" | "Medium" | "Low";
export type Confidence = "High" | "Medium" | "Low";
export type ComponentKey = "inspection" | "deficiencies" | "maintenance" | "crew" | "audit";

export interface Health {
  status: "ok" | "degraded";
  postgres: "up" | "down";
  qdrant: "up" | "down";
}

export interface Driver {
  component: ComponentKey;
  feature: string;
  owner: string;
  text: string;
  points: number;
  record_ids: string[];
}

export interface Override {
  id: string;
  text: string;
  record_ids: string[];
}

export interface ConfidenceReason {
  check: string;
  text: string;
  level: "high" | "medium" | "low";
}

export interface Feature {
  value: number;
  detail: string;
  record_ids: string[];
  normalized: number;
  points: number;
}

export interface ScoreComponent {
  label: string;
  owner: string;
  max_points: number;
  points: number;
  features: Record<string, Feature>;
}

export interface RankingRow {
  rank: number;
  vessel_id: string;
  vessel_name: string | null;
  score: number;
  band: Band;
  confidence: Confidence;
  overrides: string[];
  drivers: Driver[];
  as_of: string;
  calc_id: string;
}

export interface VesselRisk {
  id: number;
  calc_id: string;
  vessel_id: string;
  vessel_name: string | null;
  created_at: string;
  as_of: string;
  trigger: "upload" | "action" | string;
  trigger_ref: string | null;
  data_version: Record<string, number | null>;
  score: number;
  band: Band;
  confidence: Confidence;
  confidence_reasons: ConfidenceReason[];
  components: Record<ComponentKey, ScoreComponent>;
  overrides: Override[];
  drivers: Driver[];
}

export interface HistoryPoint {
  created_at: string;
  trigger: string;
  trigger_ref: string | null;
  score: number;
  band: Band;
  calc_id: string;
}

export interface ScoreBand {
  score: number;
  band: Band;
}

export interface Readiness {
  before: ScoreBand;
  after: ScoreBand;
  text: string;
}

export type ActionStatus = "open" | "completed" | "superseded";

export interface VesselAction {
  id: number;
  vessel_id: string;
  rule_id: string;
  action_key: string;
  text: string;
  owner: string;
  deadline_days: number;
  deadline_label: string | null;
  due_date: string;
  record_ids: string[];
  resolves: Record<string, string[]>;
  status: ActionStatus;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  completed_by: string | null;
  completion_evidence: string | null;
  readiness: Readiness | null;
}

export interface CompleteActionResult {
  action_id: number;
  readiness: Readiness;
  calc_id: string;
}

export type IssueRecord = Record<string, string | number | null>;

export interface VesselIssues {
  open_deficiencies: IssueRecord[];
  unresolved_audit_findings: IssueRecord[];
  overdue_maintenance: IssueRecord[];
  stale_open_maintenance: IssueRecord[];
  crew_flags: IssueRecord[];
}

export interface UploadRecord {
  id: number;
  batch_id: string;
  table_name: string;
  file_name: string;
  uploaded_by: string;
  created_at: string;
  sha256: string;
  row_count: number;
  rows_added: number;
  rows_changed: number;
  rows_removed: number;
  status: string;
}

export interface UploadedFile {
  upload_id: number;
  table: string;
  file_name: string;
  row_count: number;
  rows_added: number;
  rows_changed: number;
  rows_removed: number;
}

export interface RankingChange {
  vessel_id: string;
  before: ScoreBand | null;
  after: ScoreBand;
}

export interface UploadResult {
  batch_id: string;
  files: UploadedFile[];
  actions: { created?: number; updated?: number; superseded?: number };
  ranking_changes: RankingChange[];
  indexing: "scheduled" | "disabled";
  model: "scheduled";
}

export interface RowError {
  file: string;
  row: number | null;
  column: string | null;
  value: string | null;
  message: string;
}

export interface UploadDiff {
  upload: UploadRecord;
  previous_upload_id: number | null;
  added: string[];
  changed: { key: string; fields: Record<string, { old: string; new: string }> }[];
  removed: string[];
  ranking_changes: RankingChange[];
}

export interface ShortlistStats {
  top_n: number;
  bad_outcomes: number;
  caught: number;
  recall: number | null;
  flags: number;
  precision: number | null;
}

export interface BacktestRankingRow {
  vessel_id: string;
  inspection_id: string;
  inspection_date: string;
  score: number;
  outcome: string;
  bad_outcome: boolean;
  top_driver: string | null;
  rank: number;
  tied_with: number;
  flagged: boolean;
}

export interface BacktestOutcome {
  vessel_id: string;
  inspection_id: string;
  inspection_date: string;
  outcome: string;
  score: number;
  rank: number;
  tied_with: number;
  flagged: boolean;
  round: number;
}

export interface BacktestRound {
  round: number;
  date_range: [string, string];
  flagged: number;
  bad_outcomes: number;
  bad_outcomes_flagged: number;
  ranking: BacktestRankingRow[];
}

export interface Backtest {
  top_n: number;
  components: string[];
  summary: ShortlistStats;
  recall_curve: ShortlistStats[];
  bad_outcomes: BacktestOutcome[];
  rounds: BacktestRound[];
  caveats: string[];
}

export interface ShadowOutcome {
  vessel_id: string;
  inspection_id: string;
  round: number;
  outcome: string;
  probability: number;
  rank: number;
}

export interface ShadowRecall {
  top_n: number;
  bad_outcomes: number;
  caught: number;
  recall: number | null;
}

export interface ShadowCheck {
  bad_outcomes: ShadowOutcome[];
  recall_at_2: ShadowRecall;
  recall_at_3: ShadowRecall;
}

export interface ShadowModelReport {
  model: string;
  role: string;
  features: string[];
  rows: number;
  positives: number;
  coefficients: { feature: string; label: string; coefficient: number }[];
  intercept: number;
  in_sample: ShadowCheck;
  forward: ShadowCheck & { trained_on_rounds_before: number };
  leave_one_vessel_out: ShadowCheck;
  registry: {
    name: string;
    version: string;
    run_id: string;
    trained_at: string;
    trigger: string;
    trigger_ref: string | null;
    model_uri: string;
  };
  current: {
    rank: number;
    vessel_id: string;
    vessel_name: string;
    probability: number;
    margin: number;
    shadow_score: number;
    rule_score: number;
    rule_band: Band;
  }[];
  caveats: string[];
}

export interface RecordField {
  name: string;
  value: string | number | null;
}

export interface RecordDetail {
  evidence_id: string;
  table: string;
  kind: string;
  record_id: string;
  vessel_id: string | null;
  vessel_name: string | null;
  fields: RecordField[];
}

export interface Citation {
  index: number | null;
  evidence_id: string | null;
  label: string | null;
  source_type: "record" | "report" | "vessel_summary" | null;
  table: string | null;
  doc_type: string | null;
  record_id: string | null;
  vessel_id: string | null;
  date: string | null;
  status: string | null;
  category: string | null;
  synthetic: boolean;
  rerank_score: number | null;
  snippet: string;
}

export interface EvidenceQuery {
  q: string;
  source_type?: "record" | "report" | "vessel_summary";
  status?: string;
  from?: string;
  to?: string;
}

export interface EvidenceAnswer {
  vessel_id: string;
  query: string;
  filters: Record<string, string>;
  model: string;
  retrieved: number;
  refused: boolean;
  answer: string;
  citations: Citation[];
  evidence_coverage: number;
}

export interface IndexStatus {
  enabled: boolean;
  provider: string;
  reason: string | null;
  uploads_pending: number;
  collection?: string;
  points?: Record<string, number>;
  store_error?: string;
}
