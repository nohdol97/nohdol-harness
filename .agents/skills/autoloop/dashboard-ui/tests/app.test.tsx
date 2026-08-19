import { render, screen } from "@testing-library/react";
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
    expect(screen.getByText("Coordination 세부 정보").parentElement).not.toHaveAttribute("open");
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
  it("keeps unavailable cost honest and dependency semantics explicit in technical details", () => {
    const view = render(<TechnicalDetails task={{ ...task, cost_measurement: "unavailable", tasks: [{ id: "T2", ready: false, blocked_reason: "dependency 대기: T1" }], integrations: [{ wave: 1, ok: false, error: "conflict" }] }} />);
    fireEvent.click(view.container.querySelector("summary")!);
    expect(screen.getByText(/측정 안 됨 · unavailable/)).toBeVisible();
    expect(screen.getByText(/conflict/)).toBeVisible();
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
