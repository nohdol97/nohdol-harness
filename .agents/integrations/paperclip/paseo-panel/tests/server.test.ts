import { test } from "node:test";
import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { PassThrough } from "node:stream";
import { createService, createTransport } from "../server/paperclip";

const company = "11111111-1111-4111-8111-111111111111";
const other = "22222222-2222-4222-8222-222222222222";
const project = "33333333-3333-4333-8333-333333333333";
const issue = "44444444-4444-4444-8444-444444444444";
const agent = "55555555-5555-4555-8555-555555555555";
function fixture(overrides: Record<string, unknown> = {}) {
  const calls: { method: string; path: string; body?: unknown }[] = [];
  const data: Record<string, unknown> = {
    "/instance/settings/experimental": { enableExternalObjects: false },
    "/companies": [{ id: company, name: "회사", secret: "private" }],
    [`/companies/${company}/projects`]: [
      { id: project, companyId: company, name: "프로젝트" },
    ],
    [`/companies/${company}/agents`]: [
      {
        id: agent,
        companyId: company,
        name: "구현",
        status: "running",
        adapterConfig: { token: "private" },
      },
    ],
    [`/companies/${company}/issues?limit=100`]: [
      {
        id: issue,
        companyId: company,
        projectId: project,
        title: "제목",
        status: "backlog",
        priority: "medium",
      },
    ],
    [`/companies/${company}/heartbeat-runs?limit=30&summary=true`]: [
      {
        id: issue,
        companyId: company,
        agentId: agent,
        status: "succeeded",
        resultJson: { secret: "private" },
      },
    ],
    [`/issues/${issue}`]: {
      id: issue,
      companyId: company,
      projectId: project,
      title: "제목",
      description: "<script>alert(1)</script>",
      status: "backlog",
    },
    [`/issues/${issue}/comments?limit=50&order=desc`]: [
      {
        id: issue,
        issueId: issue,
        body: "댓글",
        createdAt: "2026-10-15T00:00:00Z",
        secret: "private",
      },
    ],
    ...overrides,
  };
  const service = createService(async (method, path, body) => {
    calls.push({ method, path, body });
    if (method === "POST" && path.endsWith("/issues"))
      return { id: issue, companyId: company, ...(body as object) };
    if (method === "POST" && path.endsWith("/pause"))
      return { id: agent, companyId: company, name: "구현", status: "paused" };
    if (!(path in data)) throw new Error("Unexpected request: " + path);
    return data[path];
  });
  return { service, calls };
}
test("projects, issues, agents and runs are projected without configs or raw logs", async () => {
  const { service } = fixture();
  assert.deepEqual(await service.companies({}), [
    { id: company, name: "회사" },
  ]);
  const board = await service.board({ companyId: company });
  assert.equal(board.projects[0].id, project);
  assert.equal(board.issues[0].id, issue);
  assert.equal(board.agents[0].status, "running");
  assert.equal(board.runs[0].status, "succeeded");
  assert.ok(!JSON.stringify(board).includes("private"));
});
test("detail and comments use plain bounded strings and omit arbitrary fields", async () => {
  const { service } = fixture();
  const result = await service.detail({ companyId: company, issueId: issue });
  assert.equal(result.issue.description, "<script>alert(1)</script>");
  assert.equal(result.comments[0].body, "댓글");
  assert.ok(!JSON.stringify(result).includes("private"));
});
test("draft is unassigned backlog and never wakes or resumes an agent", async () => {
  const { service, calls } = fixture();
  await service.draft({
    companyId: company,
    projectId: project,
    title: " 작업 ",
    description: "본문",
  });
  const posts = calls.filter((c) => c.method === "POST");
  assert.deepEqual(posts, [
    {
      method: "POST",
      path: `/companies/${company}/issues`,
      body: {
        projectId: project,
        title: "작업",
        description: "본문",
        priority: "medium",
        status: "backlog",
        assigneeAgentId: null,
        assigneeUserId: null,
        parentId: null,
        watchdog: null,
        executionPolicy: null,
      },
    },
  ]);
});
test("invalid identifiers, extra mutation fields and invalid titles fail before network", async () => {
  for (const input of [
    { companyId: "../", projectId: project, title: "제목", description: "" },
    { companyId: company, projectId: project, title: " ", description: "" },
    {
      companyId: company,
      projectId: project,
      title: "x".repeat(201),
      description: "",
    },
    {
      companyId: company,
      projectId: project,
      title: "제목",
      description: "x".repeat(20001),
    },
    {
      companyId: company,
      projectId: project,
      title: "제목",
      description: "",
      assigneeAgentId: agent,
    },
  ]) {
    const { service, calls } = fixture();
    await assert.rejects(() => service.draft(input as never));
    assert.equal(calls.length, 0);
  }
});
test("cross-company project, issue, agent and missing company are rejected", async () => {
  const one = fixture({
    [`/companies/${company}/projects`]: [
      { id: project, companyId: other, name: "other" },
    ],
  });
  await assert.rejects(() =>
    one.service.draft({
      companyId: company,
      projectId: project,
      title: "test",
      description: "",
    }),
  );
  const two = fixture({
    [`/issues/${issue}`]: { id: issue, companyId: other },
  });
  await assert.rejects(() =>
    two.service.detail({ companyId: company, issueId: issue }),
  );
  const three = fixture({
    [`/companies/${company}/agents`]: [{ id: agent, companyId: other }],
  });
  await assert.rejects(() =>
    three.service.pause({
      companyId: company,
      agentId: agent,
      confirmed: true,
    }),
  );
  await assert.rejects(() => fixture().service.board({ companyId: other }));
  assert.equal(
    [...one.calls, ...two.calls, ...three.calls].filter(
      (c) => c.method === "POST",
    ).length,
    0,
  );
});
test("pause requires explicit confirmation and only posts the pause endpoint", async () => {
  const { service, calls } = fixture();
  await assert.rejects(() =>
    service.pause({
      companyId: company,
      agentId: agent,
      confirmed: false,
    } as never),
  );
  assert.equal(calls.length, 0);
  assert.equal(
    (
      await service.pause({
        companyId: company,
        agentId: agent,
        confirmed: true,
      })
    ).status,
    "paused",
  );
  assert.deepEqual(
    calls.filter((c) => c.method === "POST"),
    [{ method: "POST", path: `/agents/${agent}/pause`, body: {} }],
  );
});
function wire(status: number, body: string, mode = "normal") {
  let options: any;
  let destroyed = false;
  const request = ((opts: unknown, callback: (stream: any) => void) => {
    options = opts;
    const req = new EventEmitter() as any;
    req.write = () => {};
    req.destroy = () => {
      destroyed = true;
    };
    req.end = () => {
      if (mode === "timeout") return;
      queueMicrotask(() => {
        const response = new PassThrough() as any;
        response.statusCode = status;
        response.headers = { "content-type": "application/json" };
        callback(response);
        response.end(body);
      });
    };
    return req;
  }) as any;
  return { request, options: () => options, destroyed: () => destroyed };
}
test("transport pins localhost and ignores proxy environment", async () => {
  const mock = wire(200, "[]");
  await createTransport({ request: mock.request })("GET", "/companies");
  assert.equal(mock.options().hostname, "127.0.0.1");
  assert.equal(mock.options().port, 3100);
  assert.equal(mock.options().path, "/api/companies");
  assert.equal(mock.options().agent, false);
});
test("transport blocks redirects, errors, invalid JSON and oversized response", async () => {
  for (const [status, body] of [
    [302, "{}"],
    [500, "SECRET_INTERNAL"],
    [200, "bad-json"],
    [200, "x".repeat(2_100_000)],
  ] as const) {
    const mock = wire(status, body);
    await assert.rejects(
      () => createTransport({ request: mock.request })("GET", "/companies"),
      (error) => !String(error).includes("SECRET_INTERNAL"),
    );
  }
});
test("transport has absolute timeout and never accepts arbitrary URL or method", async () => {
  const mock = wire(200, "{}", "timeout");
  await assert.rejects(
    () =>
      createTransport({ request: mock.request, timeoutMs: 10 })(
        "GET",
        "/companies",
      ),
    /시간/,
  );
  assert.equal(mock.destroyed(), true);
  await assert.rejects(() =>
    createTransport({ request: mock.request })("GET", "https://example.com"),
  );
  await assert.rejects(() =>
    createTransport({ request: mock.request })("DELETE" as never, "/companies"),
  );
});

test("draft fails closed when external object detection is enabled or unknown", async () => {
  for (const flags of [{ enableExternalObjects: true }, {}]) {
    const { service, calls } = fixture({
      "/instance/settings/experimental": flags,
    });
    await assert.rejects(() =>
      service.draft({
        companyId: company,
        projectId: project,
        title: "제목",
        description: "",
      }),
    );
    assert.equal(calls.filter((c) => c.method === "POST").length, 0);
  }
});

test("free text secrets are masked and field sizes and lists are bounded", async () => {
  const { service } = fixture({
    [`/issues/${issue}`]: {
      id: issue,
      companyId: company,
      title: "Bearer test_private_token password=some-private-value",
      description: "d".repeat(30000),
    },
    [`/issues/${issue}/comments?limit=50&order=desc`]: Array.from(
      { length: 70 },
      () => ({ id: issue, body: "x".repeat(12000) }),
    ),
  });
  const result = await service.detail({ companyId: company, issueId: issue });
  assert.ok(!JSON.stringify(result).includes("test_private_token"));
  assert.ok(!JSON.stringify(result).includes("some-private-value"));
  assert.equal(result.issue.description?.length, 20000);
  assert.equal(result.comments.length, 50);
  assert.equal(result.comments[0].body.length, 10000);
});
test("all read and pause IDs are validated before transport; cross-company rows fail closed", async () => {
  const { service, calls } = fixture();
  await assert.rejects(() => service.board({ companyId: "../" }));
  await assert.rejects(() =>
    service.detail({ companyId: company, issueId: "../" }),
  );
  await assert.rejects(() =>
    service.pause({ companyId: company, agentId: "../", confirmed: true }),
  );
  await assert.rejects(() => service.companies({ url: "https://example.com" }));
  assert.equal(calls.length, 0);
  await assert.rejects(() =>
    fixture({
      [`/companies/${company}/issues?limit=100`]: [
        { id: issue, companyId: other },
      ],
    }).service.board({ companyId: company }),
  );
});
test("already paused agent does not issue a mutation", async () => {
  const { service, calls } = fixture({
    [`/companies/${company}/agents`]: [
      { id: agent, companyId: company, status: "paused" },
    ],
  });
  await service.pause({ companyId: company, agentId: agent, confirmed: true });
  assert.equal(calls.filter((c) => c.method === "POST").length, 0);
});

test("draft optional operation UUID uses real create idempotency without assignment or extra wake", async () => {
  const { service, calls } = fixture();
  await service.draft({
    companyId: company,
    projectId: project,
    title: "Draft",
    description: "",
    operationId: issue,
  });
  const posts = calls.filter((c) => c.method === "POST");
  assert.equal(posts.length, 1);
  assert.equal((posts[0].body as any).idempotencyKey, "panel-draft:" + issue);
  assert.equal((posts[0].body as any).status, "backlog");
  assert.equal((posts[0].body as any).assigneeAgentId, null);
});
