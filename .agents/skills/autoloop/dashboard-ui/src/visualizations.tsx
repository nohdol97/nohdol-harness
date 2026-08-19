import type { Agent, DashboardTask, Event } from "./types";

const text = (value: unknown) => value === null || value === undefined || value === "" ? "—" : String(value);
const eventLabel: Record<string, string> = { task_dispatch: "task dispatch", task_complete: "task 완료", task_failed: "task 실패" };

export function HandoffStrip({ events }: { events: Event[] }) {
  const ordered = [...events].filter((event) => ["task_dispatch", "task_complete", "task_failed"].includes(event.event ?? "")).sort((a, b) => String(a.ts).localeCompare(String(b.ts)));
  return <section><h3>T 핸드오프</h3>{ordered.length ? <><div className="handoff" aria-label="기록된 task handoff 흐름">{ordered.map((event, index) => <span className="handoff-chip" key={`${event.ts}-${index}`}>{text(event.task_id)} {eventLabel[event.event ?? ""] ?? text(event.event)}</span>)}</div><ol className="sr-only">{ordered.map((event, index) => <li key={`text-${index}`}>{text(event.task_id)} {eventLabel[event.event ?? ""] ?? text(event.event)} · {text(event.ts)}</li>)}</ol></> : <p className="muted">기록된 task event가 없습니다.</p>}</section>;
}

export function AgentTimeline({ agents }: { agents: Agent[] }) {
  const points = agents.map((agent) => ({ start: Date.parse(agent.started_at ?? ""), end: Date.parse(agent.finished_at ?? "") }));
  const timed = agents.length > 0 && points.every((point) => Number.isFinite(point.start) && Number.isFinite(point.end) && point.end >= point.start);
  const min = timed ? Math.min(...points.map((point) => point.start)) : 0;
  const max = timed ? Math.max(...points.map((point) => point.end)) : 1;
  let occupied = 0;
  const positions = agents.map((agent, index) => {
    const rawLeft = timed ? ((points[index].start - min) / Math.max(max - min, 1)) * 100 : ((Number(agent.wave) || index) / Math.max(agents.length, 1)) * 100;
    const rawWidth = timed ? Math.max(((points[index].end - points[index].start) / Math.max(max - min, 1)) * 100, 12) : Math.max(18, 88 / Math.max(agents.length, 1));
    const left = Math.min(Math.max(rawLeft, occupied), 88);
    const width = Math.min(rawWidth, 100 - left);
    occupied = left + width + 1;
    return { left, width };
  });
  return <section><h3>한 줄 실행 시간축</h3><p className="muted">{timed ? "기록된 시간축" : "기록된 wave / 순서 축"}</p><div className="agent-track" aria-label="한 줄 agent 실행 시간축">{agents.length ? agents.map((agent, index) => <span className="agent-segment" style={{ left: `${positions[index].left}%`, width: `${positions[index].width}%` }} key={`${agent.id}-${index}`} title={`${text(agent.task_id)} · ${text(agent.status)}`}>{text(agent.task_id || agent.id)} · {text(agent.status)}</span>) : <span className="muted">agent 기록이 없습니다.</span>}</div><details><summary>Agent 세부 정보</summary><ul>{agents.map((agent, index) => <li key={`agent-${index}`}>{text(agent.task_id || agent.id)} · {text(agent.role)} · {text(agent.requested_engine)} → {text(agent.effective_engine)} · {text(agent.engine_fallback)} · {text(agent.started_at)} → {text(agent.finished_at)}</li>)}</ul></details></section>;
}

export function Coordination({ task }: { task: DashboardTask }) {
  const events = [...(task.events ?? [])].sort((a, b) => String(a.ts).localeCompare(String(b.ts)));
  const waits = (task.tasks ?? []).filter((item) => item.ready === false && item.blocked_reason?.startsWith("dependency 대기:"));
  const fallbacks = (task.dispatches ?? []).filter((item) => item.fallback).length;
  const latest = events.at(-1);
  return <section><h3>Coordination</h3><p>dispatch wave {task.dispatches?.length ?? 0} · event {events.length} · dependency 대기 {waits.length} · fallback {fallbacks}</p><p className="muted">최신: {latest ? `${text(latest.task_id)} ${eventLabel[latest.event ?? ""] ?? text(latest.event)}` : "기록 없음"}</p><details><summary>Coordination 세부 정보</summary><ul>{(task.dispatches ?? []).map((dispatch, index) => <li key={`wave-${index}`}>wave {text(dispatch.wave)}: {dispatch.task_ids?.join(", ") || "—"} · {text(dispatch.started_at)} → {text(dispatch.finished_at)} · {text(dispatch.fallback)}</li>)}{waits.map((item) => <li key={`wait-${item.id}`}>{item.id}: {item.blocked_reason}</li>)}{events.map((event, index) => <li key={`event-${index}`}>{text(event.ts)} · {text(event.task_id)} {eventLabel[event.event ?? ""] ?? text(event.event)}</li>)}</ul></details></section>;
}

export function TechnicalDetails({ task }: { task: DashboardTask }) {
  const measurement = task.cost_measurement ?? "unknown";
  const cost = typeof task.total_cost_usd === "number" && Number.isFinite(task.total_cost_usd) && measurement !== "unknown" && measurement !== "unavailable" ? `$${task.total_cost_usd.toFixed(2)}` : "측정 안 됨";
  return <details><summary>실행 세부 정보</summary><section><h3>비용</h3><p>{cost} · {measurement}</p><h3>Agents</h3><ul>{(task.agents ?? []).map((agent, index) => <li key={`agent-detail-${index}`}>{text(agent.id)} · {text(agent.role)} · {text(agent.requested_engine)} → {text(agent.effective_engine)} · {text(agent.engine_fallback)}</li>)}</ul><h3>Integrations</h3><ul>{(task.integrations ?? []).map((item, index) => <li key={`integration-${index}`}>wave {text(item.wave)} · {item.task_ids?.join(", ")} · {item.ok ? "fan-in 성공" : text(item.failure_stage || item.error || item.status)} · {text(item.commit)} · fast-forward {String(item.target_fast_forward ?? "—")} · {text(item.cleanup)}</li>)}</ul><h3>Worktrees</h3>{(task.worktrees ?? []).map((item, index) => <p key={`worktree-${index}`}>{text(item.task_id)} <code>{text(item.path)}</code> <button onClick={() => void navigator.clipboard?.writeText(item.path ?? "")}>경로 복사</button> · {text(item.base_commit)} · {text(item.commit)} · {text(item.cleanup)}</p>)}<h3>Evidence & logs</h3><pre>{task.carryover || task.log_tail || "기록 없음"}</pre><h3>진단 정보</h3><ul>{(task.diagnostics ?? []).map((item) => <li key={item}>{item}</li>)}</ul></section></details>;
}
