import { useEffect, useMemo, useRef, useState } from "react";
import { getTask, listTasks } from "./api";
import type { DashboardTask, Status } from "./types";
import { AgentTimeline, Coordination, HandoffStrip, TechnicalDetails } from "./visualizations";

const labels: Record<Status, string> = { running: "실행 중", done: "완료", blocked: "사용자 확인 필요", stalled: "정체", exhausted: "반복 소진", stopped: "정지됨", cost: "비용 상한", error: "오류", interrupted: "중단 의심", unknown: "상태 미확인" };
const icons: Record<Status, string> = { running: "▶", done: "✓", blocked: "!", stalled: "!", exhausted: "■", stopped: "■", cost: "!", error: "×", interrupted: "×", unknown: "?" };
export const statusText = (task: DashboardTask) => `${icons[task.status] ?? "?"} ${labels[task.status] ?? task.status}${task.stale ? " · 갱신 지연" : ""}`;

export function filterAndSort(tasks: DashboardTask[], filters: { query: string; status: string; tracking: string; provenance: string; sort: string }) {
  return tasks.filter((task) => {
    if (filters.query && !task.slug.toLocaleLowerCase().includes(filters.query.toLocaleLowerCase())) return false;
    if (filters.status === "attention" && (task.attention_rank ?? 4) > 1) return false;
    if (!["all", "attention"].includes(filters.status) && task.status !== filters.status) return false;
    if (filters.tracking !== "all" && task.tracking !== filters.tracking) return false;
    return filters.provenance === "all" || task.provenance === filters.provenance;
  }).sort((a, b) => {
    if (filters.sort === "name") return a.slug.localeCompare(b.slug);
    if (filters.sort === "updated") return String(b.updated_at).localeCompare(String(a.updated_at));
    return (a.attention_rank ?? 4) - (b.attention_rank ?? 4) || String(b.updated_at).localeCompare(String(a.updated_at)) || a.slug.localeCompare(b.slug);
  });
}

export function summaryCounts(tasks: DashboardTask[]) {
  return { total: tasks.length, running: tasks.filter((task) => task.status === "running").length, attention: tasks.filter((task) => (task.attention_rank ?? 4) <= 1).length, done: tasks.filter((task) => task.status === "done").length, unstructured: tasks.filter((task) => task.tracking === "unstructured").length };
}

function storedTheme() {
  try { const saved = window.localStorage?.getItem("autoloop-theme"); return saved === "light" || saved === "dark" || saved === "system" ? saved : "light"; } catch { return "light"; }
}
function useTheme() {
  const [mode, setMode] = useState(storedTheme);
  useEffect(() => {
    const query = window.matchMedia?.("(prefers-color-scheme: dark)") ?? { matches: false, addEventListener: () => undefined, removeEventListener: () => undefined };
    const apply = () => { document.documentElement.dataset.theme = mode === "system" ? (query.matches ? "dark" : "light") : mode; };
    apply(); query.addEventListener("change", apply);
    try { window.localStorage?.setItem("autoloop-theme", mode); } catch { /* optional browser storage */ }
    return () => query.removeEventListener("change", apply);
  }, [mode]);
  return [mode, setMode] as const;
}

export function App({ initialTasks }: { initialTasks?: DashboardTask[] }) {
  const [tasks, setTasks] = useState<DashboardTask[]>(initialTasks ?? []);
  const [selected, setSelected] = useState<DashboardTask | null>(null);
  const selectedRef = useRef<string | null>(null);
  const [filters, setFilters] = useState({ query: "", status: "all", tracking: "all", provenance: "all", sort: "attention" });
  const [paused, setPaused] = useState(false);
  const [message, setMessage] = useState("준비됨");
  const [theme, setTheme] = useTheme();
  const refresh = async () => {
    try {
      const next = await listTasks();
      setTasks(next.tasks);
      const slug = selectedRef.current;
      if (slug && !next.tasks.some((item) => item.slug === slug)) { selectedRef.current = null; setSelected(null); setMessage("선택한 작업이 목록에서 사라졌습니다."); }
      else if (slug) { setSelected(await getTask(slug)); setMessage("상세 정보를 새로고침했습니다."); }
      else setMessage("목록을 새로고침했습니다.");
    } catch { setMessage("새로고침에 실패했습니다. loop 상태와는 별개입니다."); }
  };
  useEffect(() => { if (!initialTasks) void refresh(); }, [initialTasks]);
  useEffect(() => { if (paused) return; const id = window.setInterval(() => void refresh(), 5000); return () => clearInterval(id); }, [paused]);
  const visible = useMemo(() => filterAndSort(tasks, filters), [tasks, filters]);
  const counts = summaryCounts(tasks);
  const update = (field: keyof typeof filters) => (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setFilters({ ...filters, [field]: event.target.value });
  const select = async (summary: DashboardTask) => { selectedRef.current = summary.slug; setSelected(summary); try { setSelected(await getTask(summary.slug)); } catch { setMessage("상세 정보를 불러오지 못했습니다."); } };
  const back = () => { selectedRef.current = null; setSelected(null); };
  return <>
    <a className="skip" href="#main">본문으로 건너뛰기</a>
    <header><div><h1>autoloop 운영 대시보드</h1><p>지금 무엇을 하고 있는지, 정상인지, 확인할 일이 있는지 살펴보세요.</p></div><div className="toolbar">
      <label>테마 <select aria-label="테마" value={theme} onChange={(event) => setTheme(event.target.value as "light" | "dark" | "system")}><option value="light">Light</option><option value="system">System</option><option value="dark">Dark</option></select></label>
      <button onClick={() => setPaused(!paused)} aria-pressed={paused}>{paused ? "자동 갱신 재개" : "자동 갱신 일시정지"}</button><button onClick={() => void refresh()}>지금 새로고침</button>
    </div></header>
    <main id="main" className={selected ? "detail-open" : ""}><p className="sr-only" role="status" aria-live="polite">{message}</p>
      <section className="overview" aria-label="운영 개요"><div><strong>{counts.running}</strong><span>실행 중</span></div><div><strong>{counts.attention}</strong><span>확인 필요</span></div><div><strong>{counts.done}</strong><span>완료</span></div><p>{message}</p></section>
      <div className="filters"><label>검색 <input type="search" value={filters.query} onChange={update("query")} /></label><label>상태 필터 <select value={filters.status} onChange={update("status")}><option value="all">전체</option><option value="attention">주의 필요</option><option value="running">실행 중</option><option value="done">완료</option><option value="blocked">사용자 확인 필요</option><option value="stalled">정체</option><option value="exhausted">반복 소진</option><option value="stopped">정지됨</option><option value="cost">비용 상한</option><option value="error">오류</option><option value="interrupted">중단 의심</option><option value="unknown">상태 미확인</option></select></label><label>tracking 필터 <select value={filters.tracking} onChange={update("tracking")}><option value="all">전체</option><option value="structured">structured</option><option value="unstructured">unstructured</option></select></label><label>provenance 필터 <select value={filters.provenance} onChange={update("provenance")}><option value="all">전체</option><option value="recorded">recorded</option><option value="demo">demo</option></select></label><label>정렬 <select value={filters.sort} onChange={update("sort")}><option value="attention">주의 우선</option><option value="updated">최근 갱신</option><option value="name">이름</option></select></label></div>
      <div className="layout"><aside aria-label="작업 목록"><h2>작업 목록</h2><p>{visible.length}개 결과 · legacy {counts.unstructured}개</p>{visible.map((task) => <button className={`task-card ${selected?.slug === task.slug ? "selected" : ""}`} key={task.slug} onClick={() => void select(task)}><b>{task.slug}</b><span className="status">{statusText(task)}</span><small>{task.attention_reason ?? "상태 확인"} · {task.updated_relative ?? "시각 미확인"}</small></button>)}</aside><article className="detail" aria-live="polite">{selected ? <Detail task={selected} onBack={back} /> : <div className="empty"><h2>작업을 선택하세요</h2><p>주의가 필요한 작업이 먼저 표시됩니다.</p></div>}</article></div>
    </main></>;
}

function Detail({ task, onBack }: { task: DashboardTask; onBack: () => void }) {
  return <><button className="back" onClick={onBack}>← 목록으로</button><header className="detail-head"><h2>{task.slug}</h2><p>{statusText(task)} · {task.phase ?? "단계 미확인"}</p></header><section className="facts"><p><b>주의</b>{task.attention_reason ?? "—"}</p><p><b>최신 test</b>{task.test_outcome ?? "측정 없음"}</p><p><b>남은 항목</b>{task.open_items ?? "—"}</p><p><b>갱신</b>{task.updated_relative ?? "시각 미확인"}<small>{task.updated_at ?? ""}</small></p></section><HandoffStrip events={task.events ?? []} /><AgentTimeline agents={task.agents ?? []} /><Coordination task={task} /><TechnicalDetails task={task} /></>;
}
