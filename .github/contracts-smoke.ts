import type { JsonValue } from '../frontend/contracts/generated/http-data-columns.js';
import type { JsonValue as HandoffJsonValue } from '../AegisAI_FRONTEND_HANDOFF_PACKAGE/contracts/generated/http-data-columns.js';

const nested: JsonValue = { confirmed: true, items: [null, 1, 'evidence', { child: [false] }] };
const compatible: HandoffJsonValue = nested;
void compatible;
// @ts-expect-error JSON fields cannot contain undefined.
const missing: JsonValue = undefined;
// @ts-expect-error Functions are not JSON values.
const executable: JsonValue = () => 'untrusted';
// @ts-expect-error Date objects must be serialized as strings on the wire.
const date: JsonValue = new Date();
void missing;
void executable;
void date;
