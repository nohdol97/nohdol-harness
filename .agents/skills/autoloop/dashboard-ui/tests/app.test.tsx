import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { App, filterAndSort, summaryCounts } from "../src/App";
import { getTask, listTasks } from "../src/api";
import { AgentActivity, CoordinationAndFanIn, CostView, TaskGraph } from "../src/visualizations";

const task = { slug: "blocked-demo", status: "blocked" as const, attention_rank: 0, tracking: "structured" as const, provenance: "demo" as const, updated_at: "2026-08-19T10:00:00" };

describe("operator dashboard", () => {
  it("starts light and ignores an invalid persisted theme", () => {
    vi.spyOn(Storage.prototype, "getItem").mockReturnValue("neon");
    render(<App initialTasks={[]} />);
    expect(screen.getByRole("heading", { name: "autoloop 운영 대시보드" })).toBeVisible();
    expect(document.documentElement.dataset.theme).toBe("light");
  });
  it("follows a System theme media change without a server mutation", () => {
    let listener: (() => void) | undefined;
    const media = { matches: false, addEventListener: (_: string, callback: () => void) => { listener = callback; }, removeEventListener: () => undefined };
    vi.stubGlobal("matchMedia", vi.fn(() => media));
    const view = render(<App initialTasks={[]} />);
    fireEvent.change(view.container.querySelector('select[aria-label="테마"]')!, { target: { value: "system" } });
    media.matches = true; listener?.();
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
  it("filters tracking/provenance and counts attention before metadata", () => {
    const tasks = [task, { ...task, slug: "running-recorded", status: "running" as const, attention_rank: 2, tracking: "unstructured" as const, provenance: "recorded" as const }];
    expect(filterAndSort(tasks, { query: "", status: "all", tracking: "unstructured", provenance: "recorded", sort: "attention" }).map((item) => item.slug)).toEqual(["running-recorded"]);
    expect(summaryCounts(tasks)).toEqual({ total: 2, running: 1, attention: 1, done: 0, unstructured: 1 });
  });
  it("normalizes corrupt API shapes instead of leaking them into components", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ tasks: [{ slug: "bad", status: "made-up", tasks: {}, agents: "bad", dag: [] }] }) }));
    const result = await listTasks();
    expect(result.tasks[0]).toMatchObject({ slug: "bad", status: "unknown", tasks: [], agents: [], dag: {} });
  });
  it("renders dependency fallback and suppresses invalid graph", () => {
    render(<TaskGraph task={{ slug: "structured", status: "running", tracking: "structured", dag: { valid: false, diagnostics: ["cycle"] }, tasks: [{ id: "T2", status: "pending", depends_on: ["T1"], ready: false, blocked_reason: "T1 대기" }] }} />);
    expect(screen.getByText(/정상 graph를 표시할 수 없습니다/)).toBeVisible();
    expect(screen.getByText("키보드용 dependency 관계")).toBeVisible();
  });
  it("renders a valid branching graph with roles and directional rank contract", () => {
    render(<TaskGraph task={{ slug: "graph", status: "running", tracking: "structured", dag: { valid: true, edges: [{ from: "T1", to: "T2" }, { from: "T1", to: "T3" }] }, tasks: [{ id: "T1", owner: "architect", status: "complete", ready: true }, { id: "T2", owner: "implementer", status: "running", depends_on: ["T1"], ready: true }, { id: "T3", owner: "reviewer", status: "pending", depends_on: ["T1"], ready: false, blocked_reason: "T1 대기" }] }} />);
    expect(screen.getByLabelText("방향성 task graph")).toBeVisible();
    expect(screen.getAllByText(/architect/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/reviewer/).length).toBeGreaterThan(0);
  });
  it("uses time bars only for valid agent endpoints and wave columns otherwise", () => {
    const { rerender } = render(<AgentActivity task={{ slug: "time", status: "running", agents: [{ id: "a", started_at: "2026-08-19T10:00:00", finished_at: "2026-08-19T10:01:00", wave: 1 }] }} />);
    expect(screen.getByLabelText("기록된 agent 시간 관계")).toBeVisible();
    rerender(<AgentActivity task={{ slug: "wave", status: "running", agents: [{ id: "a", started_at: "broken", wave: 2 }] }} />);
    expect(screen.getByLabelText("기록된 agent wave 관계")).toBeVisible();
    expect(screen.getAllByText(/기록 순서 1/).length).toBeGreaterThan(1);
  });
  it("is honest about full, partial, and unavailable cost", () => {
    const { rerender } = render(<CostView task={{ slug: "cost", status: "running", total_cost_usd: 2.5, cost_measurement: "full", iterations: [{ cost: 1.2 }] }} />);
    expect(screen.getByText(/\$2.50/)).toBeVisible();
    rerender(<CostView task={{ slug: "cost", status: "running", total_cost_usd: 2.5, cost_measurement: "partial" }} />);
    expect(screen.getByText(/일부 측정/)).toBeVisible();
    rerender(<CostView task={{ slug: "cost", status: "running", cost_measurement: "unavailable" }} />);
    expect(screen.getByText("측정 안 됨")).toBeVisible();
  });
  it("keeps recorded dependency waits separate from dispatches and renders integration without worktree", () => {
    render(<CoordinationAndFanIn task={{ slug: "flow", status: "running", tasks: [{ id: "T1", ready: false, blocked_reason: "dependency 대기: T0" }, { id: "T3", depends_on: ["T1"], ready: true, blocked_reason: "commit hook failed" }], dispatches: [{ wave: 2, task_ids: ["T2", "T3"], started_at: "start", finished_at: "finish", fallback: "agent budget" }], worktrees: [], integrations: [{ wave: 2, task_ids: ["T2"], ok: false, failure_stage: "apply", error: "conflict" }] }} />);
    expect(screen.getByText(/기록된 fallback: agent budget/)).toBeVisible();
    expect(screen.getByText(/tasks: T2, T3/)).toBeVisible();
    expect(screen.getByText(/dependency 대기: T0/)).toBeVisible();
    expect(screen.queryByText(/commit hook failed/)).not.toBeInTheDocument();
    expect(screen.getByText(/apply/)).toBeVisible();
    expect(screen.getByText("writer worktree 기록이 없습니다.")).toBeVisible();
  });
  it("switches mobile master-detail state and returns with Back", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({ ok: true, json: async () => task } as Response);
    const view = render(<App initialTasks={[task]} />);
    fireEvent.click(screen.getByRole("button", { name: /blocked-demo/ }));
    await screen.findByText("← 목록으로");
    expect(view.container.querySelector("main")?.className).toContain("detail-open");
    fireEvent.click(screen.getByText("← 목록으로"));
    expect(view.container.querySelector("main")?.className).not.toContain("detail-open");
  });
  it("contains no unsafe rendering or invented coordination wording", () => {
    const source = String(App) + String(TaskGraph) + String(AgentActivity) + String(CostView) + String(CoordinationAndFanIn);
    for (const forbidden of ["dangerouslySetInnerHTML", "innerHTML", "DOMParser", "insertAdjacentHTML", "srcdoc", "direct message", "reasoning", "chat"]) expect(source).not.toContain(forbidden);
  });
});
