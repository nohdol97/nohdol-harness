import { request as httpRequest } from "node:http";
import { z } from "zod";
import {
  companyInput,
  detailInput,
  draftInput,
  pauseInput,
  id,
} from "../shared/contracts";

type Method = "GET" | "POST" | "PATCH";
export type Transport = (
  method: Method,
  path: string,
  body?: unknown,
) => Promise<unknown>;
const MAX_BYTES = 2 * 1024 * 1024;
const uuidPath = "[0-9a-f-]{36}";
export function permitted(method: string, path: string): boolean {
  const rules: Record<string, string[]> = {
    GET: [
      "/companies",
      `/companies/${uuidPath}/(?:projects|agents)`,
      `/companies/${uuidPath}/issues\\?limit=100`,
      `/companies/${uuidPath}/heartbeat-runs\\?limit=30&summary=true`,
      `/companies/${uuidPath}/attention\\?limit=50(?:&cursor=[A-Za-z0-9%_.~-]{1,6000})?`,
      `/companies/${uuidPath}/approvals\\?status=pending`,
      `/issues/${uuidPath}`,
      `/issues/${uuidPath}/(?:interactions|approvals|diagnostics/blockers|tree-control/state)`,
      `/issues/${uuidPath}/comments\\?limit=50&order=desc`,
      `/issues/${uuidPath}/documents/[A-Za-z0-9_-]{1,100}`,
      `/approvals/${uuidPath}(?:/issues)?`,
      `/heartbeat-runs/${uuidPath}`,
      "/instance/settings/experimental",
    ],
    POST: [
      `/companies/${uuidPath}/issues`,
      `/agents/${uuidPath}/(?:pause|resume|wakeup)`,
      `/issues/${uuidPath}/comments`,
      `/issues/${uuidPath}/scheduled-retry/retry-now`,
      `/issues/${uuidPath}/interactions/${uuidPath}/(?:respond|accept|reject)`,
      `/approvals/${uuidPath}/(?:approve|reject)`,
    ],
    PATCH: [`/issues/${uuidPath}`],
  };
  return (rules[method] ?? []).some((rule) =>
    new RegExp(`^${rule}$`, "i").test(path),
  );
}
export function createTransport(
  options: { request?: typeof httpRequest; timeoutMs?: number } = {},
): Transport {
  const request = options.request ?? httpRequest;
  return async (method, path, body) => {
    if (!permitted(method, path))
      throw new Error("허용하지 않는 API 요청입니다.");
    return new Promise((resolve, reject) => {
      let done = false;
      const fail = (message: string) => {
        if (!done) {
          done = true;
          clearTimeout(timer);
          reject(new Error(message));
        }
      };
      const timer = setTimeout(() => {
        fail("Paperclip 응답 시간이 초과되었습니다. 다시 확인해 주세요.");
        req.destroy();
      }, options.timeoutMs ?? 8000);
      const payload = body === undefined ? undefined : JSON.stringify(body);
      const req = request(
        {
          hostname: "127.0.0.1",
          port: 3100,
          path: "/api" + path,
          method,
          agent: false,
          headers: {
            Accept: "application/json",
            ...(payload
              ? {
                  "Content-Type": "application/json",
                  "Content-Length": Buffer.byteLength(payload),
                }
              : {}),
          },
        },
        (response) => {
          if (
            !response.statusCode ||
            response.statusCode < 200 ||
            response.statusCode >= 300
          ) {
            fail(
              `Paperclip 요청에 실패했습니다 (HTTP ${response.statusCode ?? 0}). 인증 및 서버 상태를 확인해 주세요.`,
            );
            response.destroy();
            return;
          }
          let size = 0;
          const chunks: Buffer[] = [];
          response.on("data", (chunk: Buffer) => {
            size += chunk.length;
            if (size > MAX_BYTES) {
              fail("Paperclip 응답이 너무 큽니다.");
              response.destroy();
              req.destroy();
              return;
            }
            chunks.push(Buffer.from(chunk));
          });
          response.on("error", () =>
            fail("Paperclip 응답을 읽을 수 없습니다."),
          );
          response.on("aborted", () =>
            fail("Paperclip 연결이 중단되었습니다."),
          );
          response.on("end", () => {
            if (done) return;
            try {
              const result: unknown = JSON.parse(
                Buffer.concat(chunks).toString("utf8"),
              );
              done = true;
              clearTimeout(timer);
              resolve(result);
            } catch {
              fail("Paperclip 응답 형식이 올바르지 않습니다.");
            }
          });
        },
      );
      req.on("error", () =>
        fail(
          "로컬 Paperclip에 연결할 수 없습니다. 컴퓨터에서 Paperclip 실행 상태를 확인해 주세요.",
        ),
      );
      if (payload) req.write(payload);
      req.end();
    });
  };
}

export type Row = Record<string, unknown>;
export function row(value: unknown): Row {
  if (!value || typeof value !== "object" || Array.isArray(value))
    throw new Error("Paperclip 데이터 형식이 올바르지 않습니다.");
  return value as Row;
}
export function rows(value: unknown, limit = 100): Row[] {
  if (!Array.isArray(value))
    throw new Error("Paperclip 목록 형식이 올바르지 않습니다.");
  return value.slice(0, limit).map(row);
}
export function uuid(value: unknown): string {
  return id.parse(value);
}
export function optionalId(value: unknown): string | null {
  return typeof value === "string" && id.safeParse(value).success
    ? value
    : null;
}
export function clean(value: unknown, max = 300): string {
  if (typeof value !== "string") return "";
  return value
    .slice(0, max)
    .replace(/\bBearer\s+[A-Za-z0-9._~+\/-]+/gi, "Bearer [가림]")
    .replace(/\b(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]{12,}/g, "[가림]")
    .replace(
      /((?:api[_-]?key|access[_-]?token|password|secret)\s*[:=]\s*)[^\s,;]+/gi,
      "$1[가림]",
    );
}
function optionalText(value: unknown, max = 100): string | null {
  return typeof value === "string" ? clean(value, max) : null;
}
function projectView(r: Row) {
  return { id: uuid(r.id), name: clean(r.name), status: clean(r.status) };
}
function issueView(r: Row, detail = false) {
  return {
    id: uuid(r.id),
    identifier: clean(r.identifier, 50),
    title: clean(r.title, 200),
    description: detail ? optionalText(r.description, 20000) : null,
    status: clean(r.status, 50),
    priority: clean(r.priority, 50),
    projectId: optionalId(r.projectId),
    assigneeAgentId: optionalId(r.assigneeAgentId),
    updatedAt: optionalText(r.updatedAt),
  };
}
function agentView(r: Row) {
  return {
    id: uuid(r.id),
    name: clean(r.name),
    role: clean(r.role),
    status: clean(r.status, 50),
  };
}
export function member(r: Row, companyId: string) {
  if (r.companyId !== companyId)
    throw new Error("선택한 회사에 속하지 않는 항목입니다.");
  return r;
}

export function createService(transport: Transport = createTransport()) {
  async function companies(input: unknown) {
    z.strictObject({}).parse(input);
    return rows(await transport("GET", "/companies")).map((r) => ({
      id: uuid(r.id),
      name: clean(r.name),
    }));
  }
  async function checkCompany(companyId: string) {
    if (!(await companies({})).some((c) => c.id === companyId))
      throw new Error("회사를 찾을 수 없습니다. 목록을 새로 고쳐 주세요.");
  }
  return {
    companies,
    async board(input: unknown) {
      const { companyId } = companyInput.parse(input);
      await checkCompany(companyId);
      const base = `/companies/${companyId}`;
      const [projects, issues, agents, runs] = await Promise.all([
        transport("GET", `${base}/projects`),
        transport("GET", `${base}/issues?limit=100`),
        transport("GET", `${base}/agents`),
        transport("GET", `${base}/heartbeat-runs?limit=30&summary=true`),
      ]);
      return {
        projects: rows(projects).map((r) => projectView(member(r, companyId))),
        issues: rows(issues).map((r) => issueView(member(r, companyId))),
        agents: rows(agents).map((r) => agentView(member(r, companyId))),
        runs: rows(runs, 30).map((r) => {
          member(r, companyId);
          return {
            id: uuid(r.id),
            agentId: optionalId(r.agentId),
            status: clean(r.status, 50),
            createdAt: optionalText(r.createdAt),
            finishedAt: optionalText(r.finishedAt),
          };
        }),
      };
    },
    async detail(input: unknown) {
      const { companyId, issueId } = detailInput.parse(input);
      await checkCompany(companyId);
      const issue = member(
        row(await transport("GET", `/issues/${issueId}`)),
        companyId,
      );
      if (issue.id !== issueId)
        throw new Error("요청한 이슈와 응답이 다릅니다.");
      const comments = rows(
        await transport(
          "GET",
          `/issues/${issueId}/comments?limit=50&order=desc`,
        ),
        50,
      );
      return {
        issue: issueView(issue, true),
        comments: comments.map((r) => {
          if (r.companyId !== undefined) member(r, companyId);
          if (r.issueId !== undefined && r.issueId !== issueId)
            throw new Error("댓글의 이슈가 일치하지 않습니다.");
          return {
            id: uuid(r.id),
            body: clean(r.body, 10000),
            authorAgentId: optionalId(r.authorAgentId),
            authorType: clean(r.authorType, 50),
            createdAt: optionalText(r.createdAt),
          };
        }),
      };
    },
    async draft(input: unknown) {
      const { companyId, projectId, title, description, operationId } =
        draftInput.parse(input);
      await checkCompany(companyId);
      const project = rows(
        await transport("GET", `/companies/${companyId}/projects`),
      ).find((p) => p.id === projectId);
      if (!project) throw new Error("프로젝트를 찾을 수 없습니다.");
      member(project, companyId);
      const flags = row(
        await transport("GET", "/instance/settings/experimental"),
      );
      if (flags.enableExternalObjects !== false)
        throw new Error(
          "외부 객체 자동 감지가 꺼진 Paperclip에서만 초안을 등록할 수 있습니다.",
        );
      const created = member(
        row(
          await transport("POST", `/companies/${companyId}/issues`, {
            projectId,
            title,
            description,
            priority: "medium",
            status: "backlog",
            assigneeAgentId: null,
            assigneeUserId: null,
            parentId: null,
            watchdog: null,
            executionPolicy: null,
            ...(operationId
              ? {
                  idempotencyKey: "panel-draft:" + operationId,
                  allowDuplicate: true,
                }
              : {}),
          }),
        ),
        companyId,
      );
      if (
        created.projectId !== projectId ||
        created.assigneeAgentId !== null ||
        created.assigneeUserId !== null ||
        created.status !== "backlog" ||
        created.title !== title
      )
        throw new Error(
          "접수된 초안의 프로젝트·담당자·상태·제목이 요청과 다릅니다. 새로 등록하지 말고 목록을 확인하세요.",
        );
      return issueView(created, true);
    },
    async pause(input: unknown) {
      const { companyId, agentId } = pauseInput.parse(input);
      await checkCompany(companyId);
      const agent = rows(
        await transport("GET", `/companies/${companyId}/agents`),
      ).find((a) => a.id === agentId);
      if (!agent) throw new Error("에이전트를 찾을 수 없습니다.");
      member(agent, companyId);
      if (agent.status === "paused") return agentView(agent);
      const result = member(
        row(await transport("POST", `/agents/${agentId}/pause`, {})),
        companyId,
      );
      if (result.id !== agentId)
        throw new Error("요청한 에이전트와 응답이 다릅니다.");
      return agentView(result);
    },
  };
}
