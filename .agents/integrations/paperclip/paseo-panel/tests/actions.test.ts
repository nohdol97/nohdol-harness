import { test } from "node:test";
import assert from "node:assert/strict";
import { createActions, memoryLedger } from "../server/actions";
import { createTransport, type Transport } from "../server/paperclip";
const c = "11111111-1111-4111-8111-111111111111",
  p = "22222222-2222-4222-8222-222222222222",
  a = "33333333-3333-4333-8333-333333333333",
  i = "44444444-4444-4444-8444-444444444444",
  x = "55555555-5555-4555-8555-555555555555",
  op = "66666666-6666-4666-8666-666666666666";
const question = {
  id: x,
  companyId: c,
  issueId: i,
  kind: "ask_user_questions",
  status: "pending",
  title: "Question",
  payload: {
    version: 1,
    questions: [
      {
        id: "q",
        prompt: "Pick",
        selectionMode: "single",
        required: true,
        allowOther: true,
        options: [{ id: "one", label: "One" }],
      },
    ],
  },
};
function fixture(overrides: Record<string, unknown> = {}, failWrite = false) {
  const calls: { method: string; path: string; body?: unknown }[] = [];
  const data: Record<string, unknown> = {
    "/companies": [{ id: c, status: "active" }],
    [`/companies/${c}/projects`]: [
      { id: p, companyId: c, status: "in_progress" },
    ],
    [`/companies/${c}/agents`]: [
      { id: a, companyId: c, status: "idle", name: "Worker" },
    ],
    "/instance/settings/experimental": { enableExternalObjects: false },
    [`/issues/${i}`]: {
      id: i,
      companyId: c,
      projectId: p,
      status: "backlog",
      title: "Task",
      updatedAt: "1",
      blockedBy: [],
      assigneeAgentId: null,
    },
    [`/issues/${i}/interactions`]: [],
    [`/issues/${i}/approvals`]: [],
    [`/issues/${i}/tree-control/state`]: { activePauseHold: null },
    [`/issues/${i}/diagnostics/blockers`]: {
      readiness: { isDependencyReady: true },
      blockers: [],
      truncated: false,
    },
    [`/companies/${c}/attention?limit=50`]: {
      companyId: c,
      totalCount: 0,
      items: [],
      nextCursor: null,
    },
    [`/companies/${c}/approvals?status=pending`]: [],
    ...overrides,
  };
  const transport: Transport = async (method, path, body) => {
    calls.push({ method, path, body });
    if (method !== "GET") {
      if (failWrite) throw Error("timeout");
      if ("WRITE " + path in data) return data["WRITE " + path];
      if (path.endsWith("/issues"))
        return {
          id: i,
          companyId: c,
          projectId: p,
          assigneeAgentId: a,
          status: "todo",
        };
      if (path.endsWith("/respond")) return { ...question, status: "answered" };
      if (path.endsWith("/accept") || path.endsWith("/reject"))
        return { ...question, status: "accepted" };
      if (path.endsWith("/resume"))
        return { id: a, companyId: c, status: "idle" };
      return {
        id: i,
        companyId: c,
        issueId: i,
        projectId: p,
        assigneeAgentId: a,
        status: "todo",
      };
    }
    if (!(path in data)) throw Error("Missing fixture " + path);
    return data[path];
  };
  return { service: createActions(transport, memoryLedger()), calls, data };
}
const submit = {
  kind: "submit",
  companyId: c,
  projectId: p,
  agentId: a,
  title: "Task",
  description: "Build",
  operationId: op,
  confirmed: true,
} as const;
test("submit uses real create idempotency and never sends an extra wake; repeat returns receipt", async () => {
  const { service, calls } = fixture();
  await service.action(submit);
  await service.action(submit);
  const writes = calls.filter((v) => v.method !== "GET");
  assert.equal(writes.length, 1);
  assert.equal((writes[0].body as any).idempotencyKey, "panel-submit:" + op);
  assert.equal((writes[0].body as any).status, "todo");
  assert.equal((writes[0].body as any).allowDuplicate, true);
  await assert.rejects(() => service.action({ ...submit, title: "Changed" }));
});
test("paused assignee and mismatched deduplicated result never report execution requested", async () => {
  const paused = fixture({
    [`/companies/${c}/agents`]: [{ id: a, companyId: c, status: "paused" }],
  });
  await assert.rejects(() => paused.service.action(submit));
  assert.equal(paused.calls.filter((v) => v.method !== "GET").length, 0);
  const service = createActions(
    async (method, path) =>
      method === "POST"
        ? {
            id: i,
            companyId: c,
            projectId: x,
            assigneeAgentId: a,
            status: "todo",
          }
        : path === "/companies"
          ? [{ id: c, status: "active" }]
          : path.endsWith("/projects")
            ? [{ id: p, companyId: c }]
            : path.endsWith("/agents")
              ? [{ id: a, companyId: c, status: "idle" }]
              : { enableExternalObjects: false },
    memoryLedger(),
  );
  await assert.rejects(() => service.action(submit));
});
test("draft start checks stale fingerprint, gates and only PATCHes todo assignment", async () => {
  const { service, calls, data } = fixture();
  const ctx = await service.context({ companyId: c, issueId: i });
  data[`/issues/${i}`] = {
    ...(data[`/issues/${i}`] as object),
    updatedAt: "2",
  };
  await assert.rejects(() =>
    service.action({
      kind: "start",
      companyId: c,
      issueId: i,
      agentId: a,
      fingerprint: ctx.fingerprint,
      operationId: op,
      confirmed: true,
    }),
  );
  const fresh = await service.context({ companyId: c, issueId: i });
  await service.action({
    kind: "start",
    companyId: c,
    issueId: i,
    agentId: a,
    fingerprint: fresh.fingerprint,
    operationId: op,
    confirmed: true,
  });
  assert.deepEqual(calls.filter((v) => v.method !== "GET")[0], {
    method: "PATCH",
    path: `/issues/${i}`,
    body: { status: "todo", assigneeAgentId: a, assigneeUserId: null },
  });
});
test("questions validate unknown/duplicate options and changed question before response", async () => {
  const { service, calls } = fixture({
    [`/issues/${i}/interactions`]: [question],
  });
  const card = (await service.context({ companyId: c, issueId: i }))
    .interactions[0];
  const action = {
    kind: "answer",
    companyId: c,
    issueId: i,
    interactionId: x,
    fingerprint: card.fingerprint,
    operationId: op,
    confirmed: true,
  } as const;
  await assert.rejects(() =>
    service.action({
      ...action,
      answers: [{ questionId: "q", optionIds: ["evil"] }],
    }),
  );
  await assert.rejects(() =>
    service.action({
      ...action,
      answers: [{ questionId: "q", optionIds: ["one", "one"] }],
    }),
  );
  const result = await service.action({
    ...action,
    answers: [{ questionId: "q", optionIds: ["one"] }],
  });
  assert.match(result.message, /저장/);
  assert.equal(calls.filter((v) => v.method !== "GET").length, 1);
});
test("unknown, privileged and truncated confirmations are read-only", async () => {
  for (const payload of [
    { prompt: "Confirm", toolAction: {} },
    { prompt: "Confirm", target: { type: "custom", key: "unknown" } },
    { prompt: "x".repeat(21000) },
  ]) {
    const { service } = fixture({
      [`/issues/${i}/interactions`]: [
        { ...question, kind: "request_confirmation", payload },
      ],
    });
    const card = (await service.context({ companyId: c, issueId: i }))
      .interactions[0];
    assert.equal(card.supported, false);
    await assert.rejects(() =>
      service.action({
        kind: "accept",
        companyId: c,
        issueId: i,
        interactionId: x,
        fingerprint: card.fingerprint,
        selectedOptionIds: [],
        operationId: op,
        confirmed: true,
      }),
    );
  }
});
test("ambiguous write blocks replay and a new operation on the same target", async () => {
  const { service, calls } = fixture({}, true);
  const ctx = await service.context({ companyId: c, issueId: i });
  const action = {
    kind: "start",
    companyId: c,
    issueId: i,
    agentId: a,
    fingerprint: ctx.fingerprint,
    operationId: op,
    confirmed: true,
  } as const;
  await assert.rejects(() => service.action(action));
  await assert.rejects(() => service.action(action));
  await assert.rejects(() => service.action({ ...action, operationId: x }));
  assert.equal(calls.filter((v) => v.method !== "GET").length, 1);
});
test("cancelled dependency, pending question and recovery gate refuse start", async () => {
  for (const override of [
    {
      [`/issues/${i}/diagnostics/blockers`]: {
        readiness: { isDependencyReady: false },
        blockers: [],
        truncated: false,
      },
    },
    { [`/issues/${i}/interactions`]: [question] },
    {
      [`/issues/${i}`]: {
        id: i,
        companyId: c,
        status: "backlog",
        projectId: p,
        activeRecoveryAction: { id: x },
      },
    },
  ]) {
    const { service, calls } = fixture(override);
    const ctx = await service.context({ companyId: c, issueId: i });
    await assert.rejects(() =>
      service.action({
        kind: "start",
        companyId: c,
        issueId: i,
        agentId: a,
        fingerprint: ctx.fingerprint,
        operationId: op,
        confirmed: true,
      }),
    );
    assert.equal(calls.filter((v) => v.method !== "GET").length, 0);
  }
});
test("transport enforces method/path pairs including administrative and arbitrary URLs", async () => {
  const t = createTransport();
  for (const [method, path] of [
    ["POST", "/companies"],
    ["GET", `/agents/${a}/resume`],
    ["PATCH", `/agents/${a}`],
    ["POST", `/approvals/${x}/delete`],
    ["GET", `/issues/${i}/documents/..`],
  ])
    await assert.rejects(() => t(method as any, path));
});

test("actual project pausedAt and tree activePauseHold suppress writes; unknown hold shape fails closed", async () => {
  const paused = fixture({
    [`/companies/${c}/projects`]: [
      { id: p, companyId: c, pausedAt: "2026-10-15" },
    ],
  });
  await assert.rejects(() => paused.service.action(submit));
  assert.equal(paused.calls.filter((v) => v.method !== "GET").length, 0);
  for (const hold of [{ activePauseHold: { id: x } }, {}]) {
    const { service, calls } = fixture({
      [`/issues/${i}/tree-control/state`]: hold,
    });
    const ctx = await service.context({ companyId: c, issueId: i });
    assert.equal(ctx.canStart, false);
    await assert.rejects(() =>
      service.action({
        kind: "start",
        companyId: c,
        issueId: i,
        agentId: a,
        fingerprint: ctx.fingerprint,
        operationId: op,
        confirmed: true,
      }),
    );
    assert.equal(calls.filter((v) => v.method !== "GET").length, 0);
  }
});
test("canonical multi, text, custom answers reconstruct the exact allowed payload", async () => {
  const payload = {
    version: 1,
    questions: [
      {
        id: "multi",
        prompt: "Multi",
        options: [
          { id: "a", label: "A" },
          { id: "b", label: "B" },
        ],
      },
      { id: "text", prompt: "Count", options: [] },
      {
        id: "custom",
        prompt: "Other",
        allowOther: true,
        options: [{ id: "yes", label: "Yes" }],
      },
    ],
    questionSet: {
      schema: "paperclip.question_set.v1",
      questions: [
        {
          id: "multi",
          prompt: "Multi",
          required: true,
          answerMode: "multi_select",
          options: [
            { id: "a", label: "A" },
            { id: "b", label: "B" },
          ],
        },
        {
          id: "text",
          prompt: "Count",
          required: true,
          answerMode: "text",
          textValidation: { inputType: "integer", minimum: 2, maximum: 10 },
        },
        {
          id: "custom",
          prompt: "Other",
          required: false,
          answerMode: "single_select",
          options: [{ id: "yes", label: "Yes" }],
          customAnswer: { enabled: true },
        },
      ],
    },
  };
  const { service, calls } = fixture({
    [`/issues/${i}/interactions`]: [{ ...question, payload }],
  });
  const card = (await service.context({ companyId: c, issueId: i }))
    .interactions[0];
  const input = {
    kind: "answer",
    companyId: c,
    issueId: i,
    interactionId: x,
    fingerprint: card.fingerprint,
    operationId: op,
    confirmed: true,
  } as const;
  const answers = [
    { questionId: "multi", optionIds: ["a", "b"] },
    { questionId: "text", optionIds: [], otherText: "3" },
    { questionId: "custom", optionIds: [], otherText: "Another" },
  ];
  await assert.rejects(() =>
    service.action({
      ...input,
      answers: [
        ...answers.slice(0, 1),
        { questionId: "text", optionIds: [], otherText: "1" },
      ],
    }),
  );
  await service.action({ ...input, answers });
  assert.deepEqual(calls.filter((v) => v.method === "POST")[0].body, {
    answers,
  });
});
test("checkbox decisions enforce options/counts and reject-required reason", async () => {
  const payload = {
    version: 1,
    prompt: "Check all",
    options: [
      { id: "one", label: "One" },
      { id: "two", label: "Two" },
    ],
    minSelected: 1,
    maxSelected: 2,
    rejectRequiresReason: true,
  };
  for (const kind of ["accept", "reject"] as const) {
    const { service, calls } = fixture({
      [`/issues/${i}/interactions`]: [
        { ...question, kind: "request_checkbox_confirmation", payload },
      ],
    });
    const card = (await service.context({ companyId: c, issueId: i }))
      .interactions[0];
    const input = {
      kind,
      companyId: c,
      issueId: i,
      interactionId: x,
      fingerprint: card.fingerprint,
      operationId: op,
      confirmed: true,
    };
    if (kind === "accept") {
      await assert.rejects(() =>
        service.action({ ...input, selectedOptionIds: [] }),
      );
      await service.action({ ...input, selectedOptionIds: ["one"] });
      assert.deepEqual(calls.filter((v) => v.method === "POST")[0].body, {
        selectedOptionIds: ["one"],
      });
    } else {
      await assert.rejects(() => service.action({ ...input, reason: "" }));
      await service.action({ ...input, reason: "Revise" });
      assert.deepEqual(calls.filter((v) => v.method === "POST")[0].body, {
        reason: "Revise",
      });
    }
  }
});
test("document revision and changed card fingerprint fail closed", async () => {
  const doc = {
    id: p,
    companyId: c,
    issueId: i,
    key: "plan",
    title: "Plan",
    body: "Review entire body",
    latestRevisionId: "rev1",
  };
  const cardSource = {
    ...question,
    kind: "request_confirmation",
    payload: {
      prompt: "Approve plan",
      target: {
        type: "issue_document",
        issueId: i,
        documentId: p,
        key: "plan",
        revisionId: "rev1",
      },
    },
  };
  const { service, data, calls } = fixture({
    [`/issues/${i}/interactions`]: [cardSource],
    [`/issues/${i}/documents/plan`]: doc,
  });
  const card = (await service.context({ companyId: c, issueId: i }))
    .interactions[0];
  assert.equal(card.document?.body, doc.body);
  assert.equal(card.supported, true);
  data[`/issues/${i}/documents/plan`] = {
    ...doc,
    latestRevisionId: "rev2",
    body: "Changed",
  };
  await assert.rejects(() =>
    service.action({
      kind: "accept",
      companyId: c,
      issueId: i,
      interactionId: x,
      fingerprint: card.fingerprint,
      operationId: op,
      confirmed: true,
      selectedOptionIds: [],
    }),
  );
  assert.equal(calls.filter((v) => v.method === "POST").length, 0);
});
test("company and interaction issue boundaries are enforced", async () => {
  for (const source of [
    { ...question, companyId: p },
    { ...question, issueId: p },
  ])
    await assert.rejects(() =>
      fixture({ [`/issues/${i}/interactions`]: [source] }).service.context({
        companyId: c,
        issueId: i,
      }),
    );
});
test("prewrite failures are typed while uncertain upstream failure stays an RPC rejection", async () => {
  const { service } = fixture({
    [`/companies/${c}/agents`]: [{ id: a, companyId: c, status: "paused" }],
  });
  assert.equal(
    (await service.actionReply(submit)).outcome,
    "prewrite_rejected",
  );
  await assert.rejects(() => fixture({}, true).service.actionReply(submit));
});

test("supported board approval requires complete known payload and same-company linked issues", async () => {
  const source = {
    id: x,
    companyId: c,
    type: "request_board_approval",
    status: "pending",
    payload: { title: "Release plan", description: "Full business review" },
  };
  const { service, calls } = fixture({
    [`/approvals/${x}`]: source,
    [`/approvals/${x}/issues`]: [{ id: i, companyId: c, status: "blocked" }],
    ["WRITE /approvals/" + x + "/approve"]: { ...source, status: "approved" },
  });
  const card = await service.approval({ companyId: c, approvalId: x });
  assert.equal(card.supported, true);
  await service.action({
    kind: "approve",
    companyId: c,
    approvalId: x,
    fingerprint: card.fingerprint,
    note: "Looks good",
    operationId: op,
    confirmed: true,
  });
  assert.deepEqual(calls.filter((v) => v.method === "POST")[0].body, {
    decisionNote: "Looks good",
  });
  const unsafe = fixture({
    [`/approvals/${x}`]: {
      ...source,
      payload: { ...source.payload, toolAction: { secret: "hidden" } },
    },
    [`/approvals/${x}/issues`]: [],
  });
  assert.equal(
    (await unsafe.service.approval({ companyId: c, approvalId: x })).supported,
    false,
  );
  await assert.rejects(() =>
    fixture({
      [`/approvals/${x}`]: source,
      [`/approvals/${x}/issues`]: [{ id: i, companyId: p }],
    }).service.approval({ companyId: c, approvalId: x }),
  );
});
test("scheduled retry returns exact outcome and refuses replacement run", async () => {
  for (const outcome of [
    "promoted",
    "already_promoted",
    "no_scheduled_retry",
    "gate_suppressed",
  ]) {
    const source = {
      id: i,
      companyId: c,
      projectId: p,
      status: "blocked",
      assigneeAgentId: a,
      scheduledRetry: { runId: x, status: "scheduled_retry", agentId: a },
    };
    const { service, calls } = fixture({
      [`/issues/${i}`]: source,
      [`WRITE /issues/${i}/scheduled-retry/retry-now`]: {
        outcome,
        message: outcome,
      },
    });
    const ctx = await service.context({ companyId: c, issueId: i });
    await assert.rejects(() =>
      service.action({
        kind: "retryScheduled",
        companyId: c,
        issueId: i,
        runId: p,
        fingerprint: ctx.fingerprint,
        operationId: op,
        confirmed: true,
      }),
    );
    const receipt = await service.action({
      kind: "retryScheduled",
      companyId: c,
      issueId: i,
      runId: x,
      fingerprint: ctx.fingerprint,
      operationId: op,
      confirmed: true,
    });
    assert.equal(receipt.outcome, outcome);
    assert.equal(calls.filter((v) => v.method === "POST").length, 1);
  }
});
test("exact failed run identity and gate are checked; queued/skip differs and old run cannot be requested twice", async () => {
  for (const response of [{ queued: true }, { skipped: true }]) {
    const source = {
      id: i,
      companyId: c,
      projectId: p,
      status: "blocked",
      assigneeAgentId: a,
      executionBlocker: { runId: x, agentId: a, canRetry: true },
    };
    const { service, calls } = fixture({
      [`/issues/${i}`]: source,
      [`/heartbeat-runs/${x}`]: {
        id: x,
        companyId: c,
        agentId: a,
        status: "failed",
        contextSnapshot: { issueId: i },
      },
      [`WRITE /agents/${a}/wakeup`]: response,
    });
    const ctx = await service.context({ companyId: c, issueId: i });
    assert.equal(ctx.failedRun?.canRetry, true);
    const input = {
      kind: "retryFailed",
      companyId: c,
      issueId: i,
      runId: x,
      fingerprint: ctx.fingerprint,
      operationId: op,
      confirmed: true,
    } as const;
    const receipt = await service.action(input);
    assert.equal(receipt.outcome, "queued" in response ? "queued" : "skipped");
    await service.action(input);
    await assert.rejects(() => service.action({ ...input, operationId: p }));
    assert.equal(calls.filter((v) => v.method === "POST").length, 1);
    assert.equal(
      (calls.find((v) => v.method === "POST")?.body as any).failedRunId,
      x,
    );
    const bad = fixture({
      [`/issues/${i}`]: source,
      [`/heartbeat-runs/${x}`]: {
        id: x,
        companyId: c,
        agentId: a,
        status: "failed",
        contextSnapshot: { issueId: p },
      },
    });
    assert.equal(
      (await bad.service.context({ companyId: c, issueId: i })).failedRun,
      null,
    );
  }
});
test("explicit resume and comment use exact dedicated paths without status override", async () => {
  const resumed = fixture({
    [`/companies/${c}/agents`]: [{ id: a, companyId: c, status: "paused" }],
  });
  const info = await resumed.service.agentAction({ companyId: c, agentId: a });
  await resumed.service.action({
    kind: "resume",
    companyId: c,
    agentId: a,
    fingerprint: info.fingerprint,
    operationId: op,
    confirmed: true,
  });
  assert.equal(
    resumed.calls.filter((v) => v.method === "POST")[0].path,
    `/agents/${a}/resume`,
  );
  const { service, calls } = fixture();
  const ctx = await service.context({ companyId: c, issueId: i });
  await service.action({
    kind: "comment",
    companyId: c,
    issueId: i,
    fingerprint: ctx.fingerprint,
    body: "Please check the tests",
    operationId: op,
    confirmed: true,
  });
  assert.deepEqual(calls.filter((v) => v.method === "POST")[0], {
    method: "POST",
    path: `/issues/${i}/comments`,
    body: { body: "Please check the tests" },
  });
});
test("durable receipt reload blocks ambiguous target and replays a finished operation", async () => {
  const { fileLedger } = await import("../server/receipts");
  const { mkdtemp, rm } = await import("node:fs/promises");
  const { tmpdir } = await import("node:os");
  const { join } = await import("node:path");
  const directory = await mkdtemp(join(tmpdir(), "panel-ledger-"));
  try {
    const first = fileLedger(directory);
    await first.claim("op1", "issue1", "hash1");
    const restarted = fileLedger(directory);
    assert.deepEqual(await restarted.get("op1"), { fingerprint: "hash1" });
    await assert.rejects(() => restarted.claim("op2", "issue1", "hash2"));
    await restarted.finish("op1", "issue1", "hash1", {
      status: "saved",
      message: "Saved",
    });
    assert.deepEqual((await fileLedger(directory).get("op1"))?.result, {
      status: "saved",
      message: "Saved",
    });
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
test("concurrent local requests on same target are serialized before mutation", async () => {
  const ledger = memoryLedger();
  await Promise.allSettled([
    ledger.claim("one", "target", "hash"),
    ledger.claim("two", "target", "hash"),
  ]).then((results) => {
    assert.equal(results.filter((r) => r.status === "fulfilled").length, 1);
    assert.equal(results.filter((r) => r.status === "rejected").length, 1);
  });
});

test("canonical description/header and historical custom answer fallback remain visible", async () => {
  const payload = {
    questions: [
      {
        id: "q",
        prompt: "Pick",
        allowOther: true,
        options: [{ id: "one", label: "One" }],
      },
    ],
    questionSet: {
      schema: "paperclip.question_set.v1",
      title: "Set title",
      description: "Instructions for every answer",
      questions: [
        {
          id: "q",
          header: "Context",
          prompt: "Pick",
          required: true,
          answerMode: "single_select",
          options: [{ id: "one", label: "One" }],
        },
      ],
    },
  };
  const { service } = fixture({
    [`/issues/${i}/interactions`]: [{ ...question, payload }],
  });
  const card = (await service.context({ companyId: c, issueId: i }))
    .interactions[0];
  assert.match(card.body, /Instructions for every answer/);
  assert.match(card.questions[0].prompt, /Context/);
  assert.equal(card.questions[0].custom, true);
  await service.action({
    kind: "answer",
    companyId: c,
    issueId: i,
    interactionId: x,
    fingerprint: card.fingerprint,
    operationId: op,
    confirmed: true,
    answers: [{ questionId: "q", optionIds: [], otherText: "Another choice" }],
  });
});

test("installed attention object shape has readable titles/details and company boundary", async () => {
  const feed = {
    companyId: c,
    totalCount: 1,
    nextCursor: "page+1",
    items: [
      {
        id: "interaction:" + x,
        sourceKind: "issue_thread_interaction",
        subject: {
          id: x,
          title: "Choose the implementation",
          metadata: { issueId: i },
        },
        relatedIssue: { id: i, title: "Task" },
        detail: {
          kind: "ask_user_questions",
          firstQuestionText: "Which option?",
          privateConfig: "hidden",
        },
        whyNow: "Waiting for your answer",
      },
    ],
  };
  const { service } = fixture({ [`/companies/${c}/attention?limit=50`]: feed });
  const result = await service.inbox({ companyId: c });
  assert.equal(result.items[0].title, "Choose the implementation");
  assert.match(result.items[0].detail, /Which option/);
  assert.ok(!JSON.stringify(result).includes("hidden"));
  assert.equal(result.nextCursor, "page+1");
  await assert.rejects(() =>
    fixture({
      [`/companies/${c}/attention?limit=50`]: {
        ...feed,
        items: [{ ...feed.items[0], relatedIssue: { id: i, companyId: p } }],
      },
    }).service.inbox({ companyId: c }),
  );
});
