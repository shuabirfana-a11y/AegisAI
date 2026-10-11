/** Exercise the unmodified frontend API client against the owned TCP test server. */
import assert from 'node:assert/strict';
import { InvestigationApiClient } from '../../../frontend/contracts/investigations.ts';

const base = new URL(process.env.AEGIS_PROBE_BASE);
assert.equal(base.protocol, 'http:');
assert.equal(base.hostname, '127.0.0.1');
const client = new InvestigationApiClient(base.href, () => process.env.AEGIS_ASSET_TOKEN);
const request = JSON.parse(process.env.AEGIS_PROBE_BODY);
const id = process.env.AEGIS_PROBE_ID;
const created = await client.create(request, request.idempotency_key);
assert.equal(created.investigation_id, id);
assert.equal(created.reused, true);
assert.equal(created.is_mock, true);
assert.equal((await client.status(id)).overall_status, 'SUCCEEDED');
assert.equal((await client.trace(id)).agent_runs.length, 3);
const artifacts = await client.artifacts(id);
assert.ok(artifacts.investigation && artifacts.verification && artifacts.analysis);
assert.equal((await client.integration(id)).status, 'PASS');
const answer = await client.answer(id);
assert.equal(answer.answer_status, 'COMPLETE');
assert.equal(answer.fact_origin, 'FROZEN_GATE_CONTEXT');
assert.ok(answer.citations.length > 0);
assert.deepEqual(await client.answer(id), answer);
assert.equal((await client.history({ limit: 1, status: 'SUCCEEDED' })).items[0].investigation_id, id);
assert.equal((await client.cancel(id)).cancel_requested, false);
process.stdout.write(JSON.stringify({ transport: 'LOOPBACK_HTTP', client: 'existing-typescript-client',
  operations: 8, answer_status: answer.answer_status, data_origin: 'SYNTHETIC_TEST', benchmark: false }));
