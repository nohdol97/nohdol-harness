import { render, screen, within } from "@testing-library/react";
import { fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { App } from "../src/App";
import { filterAndSort, summaryCounts } from "../src/App";
import { listTasks } from "../src/api";
import { AgentTimeline, Coordination, HandoffStrip, TechnicalDetails } from "../src/visualizations";

describe("simplified operator workspace", () => {
  const task = { slug: "sample", status: "running" as const, phase: "dispatching", attention_reason: "정상 실행", test_outcome: "green", open_items: 2, updated_relative: "10초 전" };
  it("shows ordered recorded handoffs without a graph fallback", () => {
    render(<HandoffStrip events={[{ ts: "2026-08-19T10:02:00", event: "task_complete", task_id: "T2" }, { ts: "2026-08-19T10:01:00", event: "task_dispatch", task_id: "T2" }]} />);
    expect(screen.getAllByText(/T2 task dispatch/).length).toBeGreaterThan(1);
    expect(screen.getAllByText(/T2 task 완료/).length).toBeGreaterThan(1);
    expect(screen.queryByText("Task DAG")).not.toBeInTheDocument();
  });
  it("preserves overlapping time positions and stacks them in one axis", () => {
    const { rerender } = render(<AgentTimeline agents={[
      { id: "a", task_id: "T1", status: "running", started_at: "2026-08-19T10:00:00", finished_at: "2026-08-19T10:10:00" },
      { id: "b", task_id: "T2", status: "running", started_at: "2026-08-19T10:05:00", finished_at: "2026-08-19T10:15:00" },
      { id: "c", task_id: "T3", status: "complete", started_at: "2026-08-19T10:15:00", finished_at: "2026-08-19T10:20:00" }
    ]} />);
    const track = screen.getByLabelText("단일 agent 실행 시간축");
    const segments = Array.from(track.querySelectorAll<HTMLElement>(".agent-segment"));
    expect(track).toHaveAttribute("data-mode", "time");
    expect(track).toHaveAttribute("data-layers", "2");
    expect(segments.map((item) => [item.style.left, item.style.width, item.dataset.layer])).toEqual([
      ["0%", "50%", "0"], ["25%", "50%", "1"], ["75%", "25%", "0"]
    ]);
    rerender(<AgentTimeline agents={[{ id: "a", task_id: "T1", status: "running", started_at: "broken", wave: 2 }, { id: "b", task_id: "T2", status: "complete", wave: 3 }]} />);
    expect(screen.getByLabelText("단일 agent 실행 시간축")).toHaveAttribute("data-mode", "order");
  });
  it("keeps coordination and execution data collapsed by default", () => {
    render(<><Coordination task={{ ...task, events: [{ ts: "now", event: "task_complete", task_id: "T1" }], dispatches: [{ wave: 1, task_ids: ["T1"] }], tasks: [{ id: "T2", ready: false, blocked_reason: "dependency 대기: T1" }] }} /><TechnicalDetails task={{ ...task, total_cost_usd: 2.5, cost_measurement: "partial", integrations: [{ wave: 1, ok: false, failure_stage: "apply" }] }} /></>);
    expect(screen.getByText(/dispatch wave 1/)).toBeVisible();
    expect(screen.getByText("실행 세부 정보").parentElement).not.toHaveAttribute("open");
    expect(screen.getByText("협업 세부 정보").parentElement).not.toHaveAttribute("open");
  });
  it("keeps the first detail viewport limited to operator facts", () => {
    render(<App initialTasks={[task]} />);
    expect(screen.getByText("작업을 선택하세요")).toBeVisible();
  });
  it("retains filters, sorting, and attention summary", () => {
    const tasks = [{ ...task, slug: "done", status: "done" as const, attention_rank: 3, tracking: "structured" as const, provenance: "recorded" as const }, { ...task, slug: "blocked", status: "blocked" as const, attention_rank: 0, tracking: "unstructured" as const, provenance: "demo" as const }];
    expect(filterAndSort(tasks, { query: "", status: "all", tracking: "all", provenance: "all", sort: "attention" }).map((item) => item.slug)).toEqual(["blocked", "done"]);
    expect(summaryCounts(tasks)).toEqual({ total: 2, running: 0, attention: 1, done: 1, unstructured: 1 });
  });
  it("normalizes corrupt API arrays and invalid statuses", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ tasks: [{ slug: "bad", status: "other", agents: {}, dispatches: "bad" }] }) }));
    await expect(listTasks()).resolves.toMatchObject({ tasks: [{ status: "unknown", agents: [], dispatches: [] }] });
  });
  it("uses Light for an invalid stored theme and offers all themes", () => {
    vi.spyOn(Storage.prototype, "getItem").mockReturnValue("invalid");
    render(<App initialTasks={[]} />);
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(screen.getAllByText("System").length).toBeGreaterThan(0);
  });
  it("presents expanded execution details as labelled human-readable sections", () => {
    const view = render(<TechnicalDetails task={{ ...task, cost_measurement: "unavailable", agents: [{ id: "agent-1", task_id: "T2", role: "implementer", status: "running", requested_engine: "codex", effective_engine: "claude", engine_fallback: "writer safety" }], tasks: [{ id: "T2", ready: false, blocked_reason: "dependency 대기: T1" }], integrations: [{ wave: 1, task_ids: ["T1", "T2"], ok: false, error: "conflict", target_fast_forward: false }], worktrees: [{ task_id: "T2", path: "/tmp/task-t2", base_commit: "abc123", commit: "def456", cleanup: "pending" }], diagnostics: ["event 일부를 읽지 못했습니다"] }} />);
    fireEvent.click(view.container.querySelector("summary")!);
    const detail = within(view.container);
    expect(detail.getByText("측정되지 않음")).toBeVisible();
    expect(detail.getByRole("heading", { name: "에이전트" })).toBeVisible();
    expect(detail.getAllByText("T2").length).toBeGreaterThan(0);
    expect(detail.getByText("Codex 요청 → Claude 실행")).toBeVisible();
    expect(detail.getByText("안전 규칙에 따라 실행 환경 변경: writer safety")).toBeVisible();
    expect(detail.getByRole("heading", { name: "통합 결과" })).toBeVisible();
    expect(detail.getByText("충돌로 통합하지 못함")).toBeVisible();
    expect(detail.getByRole("heading", { name: "작업 공간" })).toBeVisible();
    expect(detail.getAllByText("정리 대기").length).toBeGreaterThan(0);
    expect(detail.getByRole("heading", { name: "확인할 문제" })).toBeVisible();
    expect(detail.queryByText("Integrations")).not.toBeInTheDocument();
    expect(detail.queryByText("Worktrees")).not.toBeInTheDocument();
  });
  it("shows role, tier, reported model, and engine in order without inventing a CLI model", () => {
    const view = render(<TechnicalDetails task={{ ...task, agents: [
      { id: "agent-1", task_id: "T1", role: "reviewer", status: "complete", model_tier: "design", requested_model: "design-current", effective_model: "design-current", model_source: "tier_override", requested_engine: "codex", effective_engine: "codex" },
      { id: "agent-2", task_id: "T2", role: "explorer", status: "running", model_tier: "explore", requested_model: "", effective_model: "", model_source: "cli_default_unreported", requested_engine: "claude", effective_engine: "claude" },
      { id: "agent-3", task_id: "T3", role: "implementer", status: "pending", requested_engine: "codex", effective_engine: "codex" },
    ] }} />);
    fireEvent.click(view.container.querySelector("summary")!);
    const cards = Array.from(view.container.querySelectorAll<HTMLElement>(".detail-card"));
    expect(Array.from(cards[0].querySelectorAll("dt")).map((node) => node.textContent)).toEqual(["역할", "티어", "모델", "엔진", "에이전트 ID"]);
    expect(within(cards[0]).getByText("설계")).toBeVisible();
    expect(within(cards[0]).getByText("design-current · tier 선택")).toBeVisible();
    expect(within(cards[0]).getByText("Codex 요청 → Codex 실행")).toBeVisible();
    expect(within(cards[1]).getByText("CLI 기본값 · 미보고")).toBeVisible();
    expect(within(cards[2]).getAllByText("—")).toHaveLength(2);
    expect(cards[2].textContent).not.toContain("Codex · 미보고");
  });
  it("uses mobile master-detail state and contains no unsafe sink wording", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => task }));
    const view = render(<App initialTasks={[task]} />);
    fireEvent.click(Array.from(view.container.querySelectorAll("button")).find((button) => button.textContent?.includes("sample"))!);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(view.container.querySelector("main")?.className).toContain("detail-open");
    fireEvent.click(Array.from(view.container.querySelectorAll("button")).find((button) => button.textContent?.includes("목록으로"))!);
    expect(String(HandoffStrip) + String(Coordination) + String(TechnicalDetails)).not.toMatch(/dangerouslySetInnerHTML|innerHTML|DOMParser|insertAdjacentHTML|srcdoc|direct message|reasoning|chat/);
  });
});
