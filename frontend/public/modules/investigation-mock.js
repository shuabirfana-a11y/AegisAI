/**
 * Mock 驱动：用交接包 10 个场景的历史合成测试回执（MOCK_ONLY）模拟调查生命周期。
 * 仅用于本机演示与前端状态验收；不冒充真实后端执行，不对真实网络失败静默回退。
 * 数据来源：AegisAI_FRONTEND_HANDOFF_PACKAGE/mock（已复制到 public/mock）。
 */
import { InvestigationApiError } from './investigation-client.js';

export const MOCK_SCENARIOS = [
  'PASS', 'ORCHESTRATION_FAILED', 'SYNTHETIC_STOP', 'CANCELLED', 'DEADLINE_EXCEEDED',
  'FAILED', 'REPLAN_REQUIRED', 'PLANNING_FAILED', 'HUMAN_REVIEW_REQUIRED', 'PASS_WITH_WARNINGS'
];

const RUN_ID_STAGES = { planner_run_id: 'PLANNING', investigation_run_id: 'INVESTIGATING', verification_run_id: 'VERIFYING', analysis_run_id: 'ANALYZING' };
const AGENT_OF_STAGE = { INVESTIGATING: 'investigation_agent', VERIFYING: 'verification_agent', ANALYZING: 'security_analysis_agent' };
const loads = new Map();

async function loadJson(basePath, name, fetchImpl) {
  const key = basePath + '/' + name;
  if (!loads.has(key)) {
    const pending = (async () => {
      let response;
      try { response = await fetchImpl(`${basePath}/${name}.json`); }
      catch { throw new InvestigationApiError(`Mock 数据 ${name}.json 不可读取。`, { kind: 'network' }); }
      if (!response.ok) throw new InvestigationApiError(`Mock 数据 ${name}.json 返回 HTTP ${response.status}。`, { status: response.status, kind: 'invalid_response' });
      try { return await response.json(); }
      catch { throw new InvestigationApiError(`Mock 数据 ${name}.json 不是合法 JSON。`, { kind: 'invalid_response' }); }
    })();
    loads.set(key, pending);
    pending.catch(() => loads.delete(key));
  }
  return loads.get(key);
}

/** 读取三个联动文件并按场景校验根 ID 一致性；不一致时抛错，不做拼接。 */
export async function loadMockSources({ basePath = '/mock', fetchImpl = globalThis.fetch, scenario = 'PASS' } = {}) {
  const [investigation, trace, answer] = await Promise.all([
    loadJson(basePath, 'investigation-demo', fetchImpl),
    loadJson(basePath, 'agent-trace-demo', fetchImpl),
    loadJson(basePath, 'answer-demo', fetchImpl)
  ]);
  const sources = {
    request: investigation?.scenarios?.[scenario]?.request,
    status: investigation?.scenarios?.[scenario]?.status,
    trace: trace?.scenarios?.[scenario],
    answer: answer?.scenarios?.[scenario],
    meta: {
      api_status: investigation?.api_status, fixture_label: investigation?.fixture_label,
      data_origin: investigation?.data_origin, notice: investigation?.notice, captured_at: investigation?.captured_at
    }
  };
  if (!sources.status || !sources.trace || !sources.answer) {
    throw new InvestigationApiError(`Mock 场景 ${scenario} 在联动文件中不完整；不混合其他场景数据。`, { kind: 'invalid_response' });
  }
  const roots = [sources.status.logical_investigation_id, sources.trace.logical_investigation_id, sources.answer.logical_investigation_id];
  if (new Set(roots).size !== 1) {
    throw new InvestigationApiError(`Mock 场景 ${scenario} 的根调查 ID 不一致；fixture 校验失败。`, { kind: 'invalid_response' });
  }
  if (sources.trace.integration_result_id && sources.answer.integration_result_id && sources.trace.integration_result_id !== sources.answer.integration_result_id) {
    throw new InvestigationApiError(`Mock 场景 ${scenario} 的 Gate 引用不一致；fixture 校验失败。`, { kind: 'invalid_response' });
  }
  return sources;
}

/** 独立 Gate 示例：join_with_five_demo_files=false，只能单独展示，不并入任何场景。 */
export async function loadIndependentGate({ basePath = '/mock', fetchImpl = globalThis.fetch } = {}) {
  const file = await loadJson(basePath, 'integration-result-independent', fetchImpl);
  const entry = file?.cases?.[0];
  if (!entry?.result) throw new InvestigationApiError('独立 Gate 示例文件缺少 result。', { kind: 'invalid_response' });
  return { notice: file.notice, joinWithScenario: file.join_with_five_demo_files === true, label: file.fixture_label, apiStatus: file.api_status, result: entry.result, dataOrigin: entry.data_origin };
}

export function createMockInvestigationClient({ scenario = 'PASS', basePath = '/mock', fetchImpl = globalThis.fetch } = {}) {
  let activeScenario = scenario;
  let state = null;

  function stagePlan(sources) {
    const stages = [];
    for (const event of sources.trace.events) if (!stages.includes(event.stage)) stages.push(event.stage);
    return stages;
  }

  function created(sources) { return sources.trace.events[0]?.at || sources.status.updated_at; }

  /** 阶段存在且已达到才视为已发生；场景没有的阶段永远保持 null。 */
  function reachedStage(stages, index, stage) {
    const at = stages.indexOf(stage);
    return at >= 0 && index >= at;
  }

  function snapshot(progress, extra = {}) {
    const { sources, stages, baseRevision } = state;
    const index = Math.min(progress, stages.length) - 1;
    const currentStage = index >= 0 ? stages[index] : 'CREATED';
    const lastEvent = [...sources.trace.events].reverse().find(event => stages.indexOf(event.stage) <= index);
    const runIds = Object.fromEntries(Object.entries(RUN_ID_STAGES)
      .map(([key, stage]) => [key, reachedStage(stages, index, stage) ? sources.status[key] ?? null : null]));
    const value = {
      investigation_id: sources.status.logical_investigation_id,
      logical_investigation_id: sources.status.logical_investigation_id,
      created_at: created(sources), updated_at: lastEvent?.at || created(sources),
      finished_at: null, cancel_requested: false, recovery_required: false,
      warnings: [], error_code: null, ...runIds,
      current_stage: currentStage, overall_status: 'RUNNING', status: currentStage,
      revision: baseRevision + progress, ...extra
    };
    if (progress < stages.length) return value;
    return {
      ...value, ...sources.status,
      current_stage: sources.status.current_stage, overall_status: sources.status.overall_status,
      status: sources.status.current_stage, revision: baseRevision + stages.length,
      updated_at: sources.status.updated_at, finished_at: sources.status.updated_at,
      cancel_requested: sources.status.cancel_requested === true || value.cancel_requested === true,
      warnings: [...(sources.status.warnings || [])]
    };
  }

  function cancelledSnapshot() {
    const { sources, stages, baseRevision } = state;
    const lastEvent = sources.trace.events[sources.trace.events.length - 1];
    const at = lastEvent?.at || sources.status.updated_at;
    return {
      investigation_id: sources.status.logical_investigation_id,
      logical_investigation_id: sources.status.logical_investigation_id,
      created_at: created(sources), updated_at: at, finished_at: at,
      cancel_requested: true, recovery_required: false, warnings: [], error_code: 'CANCELLED',
      current_stage: 'CANCELLED', overall_status: 'CANCELLED', status: 'CANCELLED',
      planner_run_id: null, investigation_run_id: null, verification_run_id: null, analysis_run_id: null,
      revision: baseRevision + stages.length + 1
    };
  }

  async function setScenario(name) {
    if (!MOCK_SCENARIOS.includes(name)) throw new InvestigationApiError(`未知 Mock 场景：${name}。`, { kind: 'invalid_request' });
    const sources = await loadMockSources({ basePath, fetchImpl, scenario: name });
    const stages = stagePlan(sources);
    activeScenario = name;
    state = { sources, stages, baseRevision: Math.max(1, sources.status.revision - stages.length), progress: 0, cancelRequested: false, cancelWait: 0 };
    return state;
  }

  function ensureId(id) {
    if (id !== state.sources.status.logical_investigation_id) {
      throw new InvestigationApiError('Mock 模式下仅能读取当前场景的调查 ID。', { status: 404, kind: 'http', code: 'INVESTIGATION_NOT_FOUND' });
    }
  }

  return {
    isMock: true,
    scenarios: MOCK_SCENARIOS,
    setScenario,
    async info() {
      if (!state) await setScenario(activeScenario);
      return { scenario: activeScenario, question: state.sources.request?.planner_input?.query?.question || null, ...state.sources.meta };
    },
    async create(request, idempotencyKey, signal) {
      if (!state) await setScenario(activeScenario);
      state.progress = 0; state.cancelRequested = false; state.cancelWait = 0;
      return {
        ...snapshot(0), reused: false, persistence: 'STORED', execution_backend: 'IN_PROCESS_BOUNDED_WORKER',
        model_provider: 'mock', is_mock: true, mock_scenario: activeScenario
      };
    },
    async status(id, signal) {
      if (!state) await setScenario(activeScenario);
      ensureId(id);
      if (state.progress >= state.stages.length) return snapshot(state.stages.length);
      if (state.cancelRequested) {
        state.cancelWait += 1;
        if (state.cancelWait >= 2) { state.progress = state.stages.length; return cancelledSnapshot(); }
        return snapshot(Math.max(state.progress, 1), { cancel_requested: true, error_code: null });
      }
      state.progress += 1;
      return snapshot(state.progress);
    },
    async cancel(id, signal) {
      if (!state) await setScenario(activeScenario);
      ensureId(id);
      if (state.progress >= state.stages.length) return snapshot(state.stages.length);
      state.cancelRequested = true; state.cancelWait = 0;
      return snapshot(Math.max(state.progress, 1), { cancel_requested: true });
    },
    async trace(id, signal) {
      if (!state) await setScenario(activeScenario);
      ensureId(id);
      const { sources, stages, baseRevision, progress } = state;
      const index = Math.min(progress, stages.length) - 1;
      const terminal = progress >= stages.length;
      const ids = { PLANNING: sources.status.planner_run_id, INVESTIGATING: sources.status.investigation_run_id, VERIFYING: sources.status.verification_run_id, ANALYZING: sources.status.analysis_run_id, INTEGRATING: sources.status.integration_result_id };
      const included = sources.trace.events.filter(event => stages.indexOf(event.stage) <= index);
      const latest = new Map();
      for (const event of included) latest.set(event.stage, event);
      const runs = new Map(sources.trace.agent_runs.map(run => [run.run_id, run]));
      const stageOfRun = new Map(Object.entries(RUN_ID_STAGES).map(([key, stage]) => [sources.status[key], stage]));
      return {
        schema_version: 'investigation-trace-v1',
        investigation_id: id, logical_investigation_id: sources.status.logical_investigation_id,
        original_question: sources.trace.original_question,
        planner: reachedStage(stages, index, 'PLANNING') ? sources.trace.planner : null,
        events: included.map(event => ({ ...event })),
        stages: [...latest.values()].map(event => {
          const runId = reachedStage(stages, index, event.stage) ? ids[event.stage] ?? null : null;
          const run = runs.get(runId);
          return {
            agent: AGENT_OF_STAGE[event.stage] || null, stage: event.stage,
            status: run ? run.status : event.code, time: event.at, run_id: runId,
            artifact_ids: (run?.artifact_references || []).map(ref => ref.artifact_id)
          };
        }),
        agent_runs: sources.trace.agent_runs
          .filter(run => stageOfRun.has(run.run_id) && reachedStage(stages, index, stageOfRun.get(run.run_id)))
          .map(run => ({ ...run, tool_calls: [...(run.tool_calls || [])] })),
        integration_result_id: reachedStage(stages, index, 'INTEGRATING') ? sources.trace.integration_result_id : null,
        integration_status: reachedStage(stages, index, 'INTEGRATING') ? sources.trace.integration_status : null,
        answer_id: reachedStage(stages, index, 'COMPOSING') || terminal ? sources.trace.answer_id : null,
        warnings: terminal ? [...(sources.trace.warnings || [])] : [],
        unresolved_items: terminal ? [...(sources.trace.unresolved_items || [])] : [],
        error_code: terminal ? sources.trace.error_code : null,
        historical_snapshot: true, revision: baseRevision + progress, mock_scenario: activeScenario
      };
    },
    async artifacts(id, signal) {
      if (!state) await setScenario(activeScenario);
      ensureId(id);
      return {
        investigation_id: id, revision: state.baseRevision + state.progress,
        investigation: null, verification: null, analysis: null,
        content_trust_level: 'UNTRUSTED_EXTERNAL_CONTENT', projection_version: 'investigation-api-public-v1',
        mock_missing: '该 Mock 场景未提供 Artifact 回执；缺失表示尚未产生或该阶段没有执行。'
      };
    },
    async integration(id, signal) {
      if (!state) await setScenario(activeScenario);
      ensureId(id);
      throw new InvestigationApiError('Mock 场景只提供 Trace/Answer 中的 Gate 状态与引用，未包含完整 Gate 回执。', { status: 409, kind: 'http', code: 'MOCK_GATE_NOT_INCLUDED' });
    },
    async answer(id, signal) {
      if (!state) await setScenario(activeScenario);
      ensureId(id);
      if (state.progress < state.stages.length) {
        throw new InvestigationApiError('Mock 调查仍在回放中，答案尚未产生。', { status: 409, kind: 'http', code: 'RESULT_NOT_READY', retryable: true, retryAfter: 1 });
      }
      return { ...state.sources.answer, mock_scenario: activeScenario };
    },
    async history(options = {}, signal) {
      const items = [];
      for (const name of MOCK_SCENARIOS) {
        const sources = await loadMockSources({ basePath, fetchImpl, scenario: name });
        items.push({
          ...sources.status,
          investigation_id: sources.status.logical_investigation_id,
          status: sources.status.current_stage,
          created_at: created(sources),
          finished_at: sources.status.updated_at,
          original_question: sources.request?.planner_input?.query?.question || sources.trace.original_question,
          answer_id: sources.trace.answer_id,
          integration_result_id: sources.trace.integration_result_id,
          mock_scenario: name
        });
      }
      const filtered = options.status ? items.filter(item => item.overall_status === options.status) : items;
      const sort = options.sort === 'created_asc' ? 'created_asc' : 'created_desc';
      const direction = sort === 'created_desc' ? -1 : 1;
      filtered.sort((left, right) => direction * String(left.created_at).localeCompare(String(right.created_at)) || left.mock_scenario.localeCompare(right.mock_scenario));
      const offset = Math.max(0, Number(options.offset) || 0);
      const limit = Math.min(100, Math.max(1, Number(options.limit) || 20));
      return { items: filtered.slice(offset, offset + limit), total: filtered.length, offset, limit, sort, status_filter: options.status || null };
    },
    async openScenario(id) {
      for (const name of MOCK_SCENARIOS) {
        const sources = await loadMockSources({ basePath, fetchImpl, scenario: name });
        if (sources.status.logical_investigation_id === id) {
          await setScenario(name);
          state.progress = state.stages.length;
          return name;
        }
      }
      throw new InvestigationApiError('该 ID 不在 Mock 场景中。', { status: 404, kind: 'http', code: 'INVESTIGATION_NOT_FOUND' });
    }
  };
}