// Generated from current Python JSON Schema. INTERNAL schemas are not HTTP API contracts.
// UUID/date/date-time are strings on the wire; JSON Schema numeric bounds and cross-field validators still apply.
// Schemaless dictionaries map to unknown. Do not treat static TypeScript types as runtime validation.
export type Decision = {
  /** minimum=1 */
  "expected_revision": number;
  /** minimum=1 */
  "expected_claim_revision": number;
  /** minLength=1, maxLength=150 */
  "request_key": string;
  "status": "CONFIRMED" | "CONFLICT" | "INSUFFICIENT_EVIDENCE" | "PENDING" | "REJECTED" | "DEFERRED";
  "value"?: (Record<string, unknown> | null);
  /** minLength=1, maxLength=2000 */
  "reason": string;
  /** maxItems=100 */
  "evidence_ids": Array<string>;
};

export type NewAsset = {
  /** minLength=1, maxLength=200 */
  "name": string;
  "asset_type"?: "service" | "training" | "application" | "project" | "server" | "container";
  "environment"?: "production" | "staging" | "development" | "unknown";
  "exposure"?: "internet" | "internal" | "development" | "unknown";
  "description"?: (string | null);
  "is_demo"?: boolean;
  /** minLength=1, maxLength=150 */
  "request_key": string;
};

export type NewComponent = {
  /** minLength=1, maxLength=300 */
  "name": string;
  "package_name"?: (string | null);
  "package_identifier_id"?: (string | null);
  "ecosystem"?: (string | null);
  /** maxLength=200 */
  "namespace"?: string;
  "purl"?: (string | null);
  "version"?: (string | null);
  "source_ref"?: (string | null);
  /** minLength=1, maxLength=150 */
  "request_key": string;
};

export type QueryRequest = {
  /** minLength=1, maxLength=2000 */
  "question": string;
  "asset_id"?: (string | null);
  "target"?: (string | null);
  "mode"?: "auto" | "fast" | "deep";
  /** minLength=1, maxLength=150 */
  "request_key": string;
  "realtime"?: boolean;
};

export type UpdateVersion = {
  "version"?: (string | null);
  /** minimum=1 */
  "expected_revision": number;
  /** minLength=1, maxLength=150 */
  "request_key": string;
};

