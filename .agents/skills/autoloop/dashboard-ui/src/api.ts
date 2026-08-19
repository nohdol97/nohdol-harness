import type { DashboardTask, TaskListResponse } from "./types";

const array = <T>(value: unknown): T[] => Array.isArray(value) ? value as T[] : [];
function task(value: unknown): DashboardTask {
  const item = (value && typeof value === "object" ? value : {}) as Partial<DashboardTask>;
  const statuses = new Set(["running", "done", "blocked", "stalled", "exhausted", "stopped", "cost", "error", "interrupted", "unknown"]);
  const tracking = item.tracking === "structured" ? "structured" : "unstructured";
  const provenance = item.provenance === "demo" ? "demo" : "recorded";
  return {
    ...item,
    slug: String(item.slug ?? ""),
    status: statuses.has(String(item.status)) ? item.status as DashboardTask["status"] : "unknown",
    tracking,
    provenance,
    attention_rank: Number.isFinite(Number(item.attention_rank)) ? Number(item.attention_rank) : 4,
    diagnostics: array<string>(item.diagnostics),
    tasks: array(item.tasks), agents: array(item.agents), worktrees: array(item.worktrees),
    integrations: array(item.integrations), dispatches: array(item.dispatches), events: array(item.events), iterations: array(item.iterations),
    dag: item.dag && typeof item.dag === "object" && !Array.isArray(item.dag) ? item.dag : {}
  };
}
async function read(path: string): Promise<unknown> { const response = await fetch(path, { headers: { Accept: "application/json" } }); if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); }
export async function listTasks(): Promise<TaskListResponse> { const value = await read("/api/tasks") as { tasks?: unknown; generated_at?: string }; return { tasks: array(value.tasks).map(task), generated_at: value.generated_at }; }
export async function getTask(slug: string): Promise<DashboardTask> { return task(await read(`/api/tasks/${encodeURIComponent(slug)}`)); }
