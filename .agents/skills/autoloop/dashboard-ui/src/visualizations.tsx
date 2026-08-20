import type { Agent, DashboardTask, Event } from "./types";

const text = (value: unknown) => value === null || value === undefined || value === "" ? "—" : String(value);
const eventLabel: Record<string, string> = { task_dispatch: "시작", task_complete: "완료", task_failed: "실패", team_create: "팀 생성", integration_complete: "통합 완료" };
const statusLabel: Record<string, string> = { running: "실행 중", complete: "완료", done: "완료", failed: "실패", blocked: "대기 중", pending: "준비 중", error: "오류" };
const roleLabel: Record<string, string> = { implementer: "구현 담당", reviewer: "검증 담당", architect: "설계 담당", explorer: "조사 담당", integrator: "통합 담당", troubleshooter: "원인 분석 담당", "infra-specialist": "인프라 담당" };
const tierLabel: Record<string, string> = { design: "설계", implement: "구현", explore: "탐색" };
const modelSourceLabel: Record<string, string> = { tier: "tier 선택", tier_override: "tier 선택", uniform: "공통 지정", uniform_override: "공통 지정", explicit: "직접 지정" };
const engineLabel: Record<string, string> = { codex: "Codex", claude: "Claude" };
const cleanupLabel: Record<string, string> = { pending: "정리 대기", complete: "정리 완료", completed: "정리 완료", cleaned: "정리 완료", retained: "유지 중", failed: "정리 실패" };
const costLabel: Record<string, string> = { full: "전체 비용", partial: "일부 비용만 집계", unavailable: "측정되지 않음", unknown: "측정 상태 미확인" };

const labelled = (value: unknown, labels: Record<string, string>) => labels[String(value ?? "").toLowerCase()] ?? text(value);
const formatEngine = (value: unknown) => engineLabel[String(value ?? "").toLowerCase()] ?? text(value);
const formatModel = (agent: Agent) => {
  const requested = String(agent.requested_model ?? "");
  const effective = String(agent.effective_model ?? "");
  const source = String(agent.model_source ?? "");
  if (!effective && source === "cli_default_unreported") return "CLI 기본값 · 미보고";
  if (!effective) return requested ? `${requested} 요청 · 실행 모델 미보고` : "—";
  const model = requested && requested !== effective ? `${requested} 요청 → ${effective} 실행` : effective;
  const sourceLabel = modelSourceLabel[source];
  return sourceLabel ? `${model} · ${sourceLabel}` : model;
};
const formatTime = (value: unknown) => {
  const raw = String(value ?? "");
  const parsed = Date.parse(raw);
  return Number.isFinite(parsed) ? new Intl.DateTimeFormat("ko-KR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(parsed) : text(value);
};
const Field = ({ label, children }: { label: string; children: React.ReactNode }) => <div><dt>{label}</dt><dd>{children}</dd></div>;

export function HandoffStrip({ events }: { events: Event[] }) {
  const lifecycleEvents = ["team_create", "task_dispatch", "task_complete", "task_failed", "integration_complete"];
  const taskEvents = ["task_dispatch", "task_complete", "task_failed"];
  const priority: Record<string, number> = { team_create: 0, task_dispatch: 1, task_complete: 2, task_failed: 2, integration_complete: 3 };
  const seenTaskEvents = new Set<string>();
  const ordered = events.map((event, index) => ({ event, index })).filter(({ event }) => lifecycleEvents.includes(event.event ?? "")).sort((a, b) => String(a.event.ts).localeCompare(String(b.event.ts)) || priority[a.event.event ?? ""] - priority[b.event.event ?? ""] || a.index - b.index).filter(({ event }) => {
    if (!taskEvents.includes(event.event ?? "")) return true;
    const key = `${event.event}\u0000${event.task_id ?? ""}\u0000${event.wave ?? ""}`;
    if (seenTaskEvents.has(key)) return false;
    seenTaskEvents.add(key);
    return true;
  }).map(({ event }) => event);
  const handoffLabel = (event: Event) => {
    if (event.event === "team_create") return eventLabel.team_create;
    if (event.event === "integration_complete") return event.wave === null || event.wave === undefined ? eventLabel.integration_complete : `${event.wave}차 ${eventLabel.integration_complete}`;
    return event.task_id ? `${event.task_id} ${eventLabel[event.event ?? ""] ?? text(event.event)}` : `작업 ${eventLabel[event.event ?? ""] ?? text(event.event)}`;
  };
  return <section><h3>T 핸드오프</h3>{ordered.length ? <><div className="handoff" aria-label="기록된 task handoff 흐름">{ordered.map((event, index) => <span className="handoff-chip" key={`${event.ts}-${index}`}>{handoffLabel(event)}</span>)}</div><ol className="sr-only">{ordered.map((event, index) => <li key={`text-${index}`}>{handoffLabel(event)} · {text(event.ts)}</li>)}</ol></> : <p className="muted">기록된 handoff event가 없습니다.</p>}</section>;
}

export function AgentTimeline({ agents }: { agents: Agent[] }) {
  const points = agents.map((agent) => ({ start: Date.parse(agent.started_at ?? ""), end: Date.parse(agent.finished_at ?? "") }));
  const timed = agents.length > 0 && points.every((point) => Number.isFinite(point.start) && Number.isFinite(point.end) && point.end >= point.start);
  const min = timed ? Math.min(...points.map((point) => point.start)) : 0;
  const max = timed ? Math.max(...points.map((point) => point.end)) : 1;
  const layerByIndex = Array(agents.length).fill(0) as number[];
  const layerEnds: number[] = [];
  if (timed) {
    points.map((point, index) => ({ ...point, index })).sort((a, b) => a.start - b.start || a.end - b.end || a.index - b.index).forEach((point) => {
      const reusable = layerEnds.findIndex((end) => end <= point.start);
      const layer = reusable === -1 ? layerEnds.length : reusable;
      layerByIndex[point.index] = layer;
      layerEnds[layer] = point.end;
    });
  }
  const layers = Math.max(timed ? layerEnds.length : agents.length ? 1 : 0, 1);
  const positions = agents.map((agent, index) => {
    const left = timed ? ((points[index].start - min) / Math.max(max - min, 1)) * 100 : index * (100 / Math.max(agents.length, 1));
    const width = timed ? ((points[index].end - points[index].start) / Math.max(max - min, 1)) * 100 : 100 / Math.max(agents.length, 1);
    return { left, width, layer: timed ? layerByIndex[index] : 0 };
  });
  return <section><h3>단일 실행 시간축</h3><p className="muted">{timed ? `기록된 시간축 · 최대 ${layers}개 동시 실행` : "기록된 wave / 순서 축 · 겹침을 추정하지 않음"}</p><div className="agent-track" aria-label="단일 agent 실행 시간축" data-mode={timed ? "time" : "order"} data-layers={layers} style={{ height: `${layers * 2.55 + .8}rem` }}>{agents.length ? agents.map((agent, index) => <span className="agent-segment" data-layer={positions[index].layer} style={{ left: `${positions[index].left}%`, width: `${positions[index].width}%`, top: `${positions[index].layer * 2.55 + .4}rem` }} key={`${agent.id}-${index}`} title={`${text(agent.task_id)} · ${text(agent.status)}`}>{text(agent.task_id || agent.id)} · {text(agent.status)}</span>) : <span className="muted">agent 기록이 없습니다.</span>}</div></section>;
}

export function Coordination({ task }: { task: DashboardTask }) {
  const waits = (task.tasks ?? []).filter((item) => item.ready === false && item.blocked_reason?.startsWith("dependency 대기:"));
  const fallbacks = (task.dispatches ?? []).filter((item) => item.fallback).length;
  return <section><h3>실행 조율</h3><p>실행 묶음 {task.dispatches?.length ?? 0} · 선행 작업 대기 {waits.length} · 실행 조정 {fallbacks}</p><details><summary>협업 세부 정보</summary><div className="detail-stack"><section className="detail-group"><h4>실행 묶음</h4><div className="detail-cards">{(task.dispatches ?? []).length ? (task.dispatches ?? []).map((dispatch, index) => <article className="detail-card" key={`wave-${index}`}><div className="card-title"><strong>{text(dispatch.wave)}차 실행 묶음</strong><span className="pill">{dispatch.task_ids?.length ?? 0}개 작업</span></div><p>{dispatch.task_ids?.join(", ") || "작업 기록 없음"}</p><p className="muted">{formatTime(dispatch.started_at)} → {formatTime(dispatch.finished_at)}</p>{dispatch.fallback ? <p className="notice">실행 조정: {text(dispatch.fallback)}</p> : null}</article>) : <p className="muted">기록된 실행 묶음이 없습니다.</p>}</div></section><section className="detail-group"><h4>선행 작업 대기</h4>{waits.length ? <ul className="readable-list">{waits.map((item) => <li key={`wait-${item.id}`}><strong>{item.id}</strong><span>{item.blocked_reason}</span></li>)}</ul> : <p className="muted">선행 작업을 기다리는 항목이 없습니다.</p>}</section></div></details></section>;
}

export function TechnicalDetails({ task }: { task: DashboardTask }) {
  const measurement = task.cost_measurement ?? "unknown";
  const cost = typeof task.total_cost_usd === "number" && Number.isFinite(task.total_cost_usd) && measurement !== "unknown" && measurement !== "unavailable" ? `$${task.total_cost_usd.toFixed(2)}` : null;
  return <details className="technical-details"><summary>실행 세부 정보</summary><div className="detail-stack"><section className="detail-group"><h3>비용</h3><div className="cost-summary"><strong>{cost ?? labelled(measurement, costLabel)}</strong><span>{cost ? labelled(measurement, costLabel) : "비용 값을 만들 수 없습니다."}</span></div></section><section className="detail-group"><h3>에이전트</h3><div className="detail-cards">{(task.agents ?? []).length ? (task.agents ?? []).map((agent, index) => <article className="detail-card" key={`agent-detail-${index}`}><div className="card-title"><strong>{text(agent.task_id || agent.id)}</strong><span className="pill">{labelled(agent.status, statusLabel)}</span></div><dl className="detail-fields"><Field label="역할">{labelled(agent.role, roleLabel)}</Field><Field label="티어">{labelled(agent.model_tier, tierLabel)}</Field><Field label="모델">{formatModel(agent)}</Field><Field label="엔진">{formatEngine(agent.requested_engine)} 요청 → {formatEngine(agent.effective_engine)} 실행</Field><Field label="실행 시간">{formatTime(agent.started_at)} → {formatTime(agent.finished_at)}</Field>{agent.id && agent.id !== agent.task_id ? <Field label="에이전트 ID"><code>{agent.id}</code></Field> : null}</dl>{agent.engine_fallback ? <p className="notice">안전 규칙에 따라 실행 환경 변경: {agent.engine_fallback}</p> : null}</article>) : <p className="muted">표시할 에이전트가 없습니다.</p>}</div></section><section className="detail-group"><h3>통합 결과</h3><div className="detail-cards">{(task.integrations ?? []).length ? (task.integrations ?? []).map((item, index) => { const conflict = String(item.error ?? "").toLowerCase().includes("conflict"); const result = item.ok ? "통합 완료" : conflict ? "충돌로 통합하지 못함" : "통합 실패"; return <article className="detail-card" key={`integration-${index}`}><div className="card-title"><strong>{text(item.wave)}차 통합</strong><span className={`pill ${item.ok ? "success" : "warning"}`}>{result}</span></div><p>{item.task_ids?.join(", ") || "대상 작업 기록 없음"}</p><dl className="detail-fields"><Field label="대상 반영">{item.target_fast_forward === true ? "반영 완료" : item.target_fast_forward === false ? "반영되지 않음" : "확인 안 됨"}</Field><Field label="통합 커밋"><code>{text(item.commit)}</code></Field><Field label="정리 상태">{labelled(item.cleanup, cleanupLabel)}</Field>{item.failure_stage || item.error ? <Field label="실패 정보">{text(item.failure_stage || item.error)}</Field> : null}</dl></article>; }) : <p className="muted">통합 기록이 없습니다.</p>}</div></section><section className="detail-group"><h3>작업 공간</h3><div className="detail-cards">{(task.worktrees ?? []).length ? (task.worktrees ?? []).map((item, index) => <article className="detail-card" key={`worktree-${index}`}><div className="card-title"><strong>{text(item.task_id)}</strong><span className="pill">{labelled(item.cleanup, cleanupLabel)}</span></div><div className="path-row"><code>{text(item.path)}</code><button onClick={() => void navigator.clipboard?.writeText(item.path ?? "")}>경로 복사</button></div><dl className="detail-fields"><Field label="시작 커밋"><code>{text(item.base_commit)}</code></Field><Field label="작업 커밋"><code>{text(item.commit)}</code></Field></dl></article>) : <p className="muted">별도 작업 공간 기록이 없습니다.</p>}</div></section><section className="detail-group"><h3>실행 기록</h3><p className="muted">다른 화면에서 가공하지 않은 마지막 기록입니다.</p><pre>{task.carryover || task.log_tail || "기록 없음"}</pre></section><section className="detail-group"><h3>확인할 문제</h3>{(task.diagnostics ?? []).length ? <ul className="readable-list warning-list">{(task.diagnostics ?? []).map((item) => <li key={item}>{item}</li>)}</ul> : <p className="muted">확인할 문제가 기록되지 않았습니다.</p>}</section></div></details>;
}
