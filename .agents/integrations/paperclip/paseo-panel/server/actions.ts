import {
  actionInput,
  inboxRpc,
  approvalRpc,
  agentActionRpc,
  type Action,
  type Interaction,
  type Approval,
  type Question,
  type Receipt,
} from "../shared/actions";
import { detailInput, id } from "../shared/contracts";
import {
  createTransport,
  row,
  rows,
  member,
  clean,
  optionalId,
  uuid,
  type Row,
  type Transport,
} from "./paperclip";
import { hash, memoryLedger, fileLedger, type Ledger } from "./receipts";
export { memoryLedger } from "./receipts";
export class PrewriteRejection extends Error {}
function fail(message: string): never {
  throw Error(message);
}
const list = (value: unknown): Row[] =>
  Array.isArray(value) ? value.map(row) : [];
const object = (value: unknown): Row =>
  value && typeof value === "object" && !Array.isArray(value)
    ? (value as Row)
    : {};
const string = (value: unknown) => (typeof value === "string" ? value : "");
const number = (value: unknown): number | null =>
  typeof value === "number" && Number.isFinite(value) ? value : null;
const pending = (r: Row) =>
  ["pending", "revision_requested"].includes(string(r.status));
const eligible = (r: Row) =>
  ["idle", "running", "active", "error"].includes(string(r.status));
const completeText = (value: unknown, max = 20000) =>
  typeof value === "string" && value.length <= max;
const same = (actual: string, expected: string) => {
  if (actual !== expected)
    fail("표시한 내용이 변경되었습니다. 새로고침 후 다시 확인해 주세요.");
};
function options(value: unknown) {
  return list(value)
    .slice(0, 100)
    .map((o) => ({
      id: string(o.id),
      label: clean(o.label, 2000),
      description: clean(o.description, 4000),
      freeText: o.freeText === true,
    }));
}
function questionView(storage: Row, canonical?: Row): Question {
  const q = canonical ?? storage;
  const validation = object(q.textValidation);
  return {
    id: string(q.id),
    prompt: [clean(q.header, 500), clean(q.prompt, 20000)]
      .filter(Boolean)
      .join("\n"),
    help: clean(q.helpText, 10000),
    mode: canonical
      ? q.answerMode === "text"
        ? "text"
        : q.answerMode === "multi_select"
          ? "multi"
          : "single"
      : q.selectionMode === "multi"
        ? "multi"
        : "single",
    required: q.required === true,
    custom:
      canonical && q.customAnswer !== undefined
        ? object(q.customAnswer).enabled === true
        : storage.allowOther === true ||
          list(storage.options).some((o) => o.freeText === true),
    options: options(canonical ? q.options : storage.options),
    minLength: number(validation.minLength),
    maxLength: number(validation.maxLength),
    inputType: string(validation.inputType) || "text",
    minimum: number(validation.minimum),
    maximum: number(validation.maximum),
    pattern: typeof validation.pattern === "string" ? validation.pattern : null,
  };
}
function validateAnswers(
  card: Interaction,
  input: Extract<Action, { kind: "answer" }>["answers"],
  storage: Row,
) {
  const answerMap = new Map(input.map((a) => [a.questionId, a]));
  if (answerMap.size !== input.length) fail("질문을 중복 제출할 수 없습니다.");
  for (const answer of input)
    if (!card.questions.some((q) => q.id === answer.questionId))
      fail("알 수 없는 질문입니다.");
  return card.questions.flatMap((q) => {
    const answer = answerMap.get(q.id);
    if (!answer) {
      if (q.required) fail("필수 질문에 답해 주세요.");
      return [];
    }
    const ids = answer.optionIds;
    const other = (answer.otherText ?? "").trim();
    if (
      new Set(ids).size !== ids.length ||
      ids.some((v) => !q.options.some((o) => o.id === v))
    )
      fail("선택지가 올바르지 않습니다.");
    if (q.mode !== "multi" && ids.length > 1)
      fail("하나의 선택지만 고를 수 있습니다.");
    if (q.mode === "text" && ids.length)
      fail("텍스트 질문에는 선택지를 보낼 수 없습니다.");
    if (
      q.mode !== "text" &&
      other &&
      !q.custom &&
      !ids.some((v) => q.options.find((o) => o.id === v)?.freeText)
    )
      fail("이 질문은 직접 입력을 허용하지 않습니다.");
    if (q.required && !ids.length && !other) fail("필수 질문에 답해 주세요.");
    if (ids.some((v) => q.options.find((o) => o.id === v)?.freeText) && !other)
      fail("선택한 직접 입력 내용을 적어 주세요.");
    if (other) {
      if (
        (q.minLength !== null && other.length < q.minLength) ||
        (q.maxLength !== null && other.length > q.maxLength)
      )
        fail("입력 길이가 질문 조건과 다릅니다.");
      if (["number", "integer"].includes(q.inputType)) {
        const value = Number(other);
        if (
          !Number.isFinite(value) ||
          (q.inputType === "integer" && !Number.isInteger(value)) ||
          (q.minimum !== null && value < q.minimum) ||
          (q.maximum !== null && value > q.maximum)
        )
          fail("숫자 입력 조건을 확인해 주세요.");
      }
    }
    const source = list(storage.questions).find((s) => s.id === q.id);
    if (!source) fail("질문 저장 형식을 확인할 수 없습니다.");
    if (ids.some((v) => !list(source.options).some((o) => o.id === v)))
      fail("질문 선택지가 변경되었습니다.");
    return [
      {
        questionId: q.id,
        optionIds: ids,
        ...(other ? { otherText: other } : {}),
      },
    ];
  });
}

export function createActions(
  transport: Transport = createTransport(),
  ledger: Ledger = fileLedger(),
) {
  const locks = new Set<string>();
  async function company(companyId: string) {
    const value = rows(await transport("GET", "/companies")).find(
      (c) => c.id === companyId,
    );
    if (!value) fail("회사를 찾을 수 없습니다.");
    return value;
  }
  async function agent(companyId: string, agentId: string) {
    await company(companyId);
    const value = rows(
      await transport("GET", `/companies/${companyId}/agents`),
    ).find((a) => a.id === agentId);
    if (!value) fail("에이전트를 찾을 수 없습니다.");
    return member(value, companyId);
  }
  async function project(companyId: string, projectId: string) {
    const value = rows(
      await transport("GET", `/companies/${companyId}/projects`),
    ).find((p) => p.id === projectId);
    if (!value) fail("프로젝트를 찾을 수 없습니다.");
    member(value, companyId);
    if (
      value.pausedAt ||
      value.status === "paused" ||
      value.pauseState === "paused"
    )
      fail("일시 정지된 프로젝트입니다.");
    return value;
  }
  async function externalOff() {
    if (
      row(await transport("GET", "/instance/settings/experimental"))
        .enableExternalObjects !== false
    )
      fail("외부 객체 자동 감지가 꺼진 경우에만 내용을 등록할 수 있습니다.");
  }
  async function issue(companyId: string, issueId: string) {
    await company(companyId);
    const value = member(
      row(await transport("GET", `/issues/${issueId}`)),
      companyId,
    );
    if (value.id !== issueId) fail("이슈 식별자가 일치하지 않습니다.");
    return value;
  }
  async function approvalProjection(
    source: Row,
    companyId: string,
  ): Promise<Approval> {
    member(source, companyId);
    const payload = object(source.payload);
    const type = string(source.type);
    const allowed = [
      "title",
      "summary",
      "description",
      "rationale",
      "plan",
      "requestedAction",
      "issueId",
    ];
    const safe =
      type === "request_board_approval" &&
      Object.keys(payload).every((k) => allowed.includes(k)) &&
      completeText(payload.title, 200) &&
      ["summary", "description", "rationale", "plan", "requestedAction"].some(
        (k) => completeText(payload[k]) && string(payload[k]).trim(),
      ) &&
      Object.entries(payload).every(([k, v]) =>
        k === "issueId" ? id.safeParse(v).success : completeText(v),
      );
    const links = rows(
      await transport("GET", `/approvals/${uuid(source.id)}/issues`),
    );
    for (const link of links) member(link, companyId);
    return {
      id: uuid(source.id),
      type,
      status: clean(source.status),
      title: clean(payload.title, 200) || clean(type),
      body: ["summary", "description", "rationale", "plan", "requestedAction"]
        .filter((k) => typeof payload[k] === "string")
        .map((k) => `${k}\n${clean(payload[k], 20000)}`)
        .join("\n\n"),
      fingerprint: hash({
        source,
        links: links.map((l) => ({
          id: l.id,
          status: l.status,
          updatedAt: l.updatedAt,
        })),
      }),
      supported: safe && pending(source),
      reason: !pending(source)
        ? "이미 처리된 승인입니다."
        : safe
          ? ""
          : "관리 권한·알 수 없는 승인 내용은 Paperclip에서 확인해 주세요.",
      issueIds: links.map((l) => uuid(l.id)),
    };
  }
  async function interactionProjection(
    source: Row,
    issueSource: Row,
  ): Promise<Interaction> {
    member(source, uuid(issueSource.companyId));
    if (source.issueId !== issueSource.id) fail("상호작용의 이슈가 다릅니다.");
    const payload = object(source.payload),
      kind = string(source.kind),
      target = object(payload.target);
    let reason = "",
      document: Interaction["document"] = null;
    const canonical = object(payload.questionSet),
      storage = list(payload.questions),
      canonicalQuestions = list(canonical.questions);
    const questions = (
      canonical.schema === "paperclip.question_set.v1"
        ? canonicalQuestions
        : storage
    )
      .slice(0, 20)
      .map((q) =>
        questionView(
          storage.find((s) => s.id === q.id) ?? {},
          canonical.schema === "paperclip.question_set.v1" ? q : undefined,
        ),
      );
    let sourceDoc: Row | null = null;
    if (
      ![
        "ask_user_questions",
        "request_confirmation",
        "request_checkbox_confirmation",
      ].includes(kind)
    )
      reason = "이 요청 종류는 Paperclip 전용 화면에서 처리해 주세요.";
    if (payload.toolAction || payload.secretProposal)
      reason =
        "외부 도구 실행 또는 인증 정보 변경은 이 패널에서 처리하지 않습니다.";
    if (target.type) {
      if (target.type === "issue_document") {
        if (
          (target.issueId && target.issueId !== issueSource.id) ||
          !/^[-\w]{1,100}$/.test(string(target.key))
        )
          reason = "다른 이슈 또는 알 수 없는 문서 대상입니다.";
        else {
          sourceDoc = member(
            row(
              await transport(
                "GET",
                `/issues/${issueSource.id}/documents/${target.key}`,
              ),
            ),
            uuid(issueSource.companyId),
          );
          if (
            sourceDoc.issueId !== issueSource.id ||
            sourceDoc.latestRevisionId !== target.revisionId ||
            (target.documentId && sourceDoc.id !== target.documentId)
          )
            reason = "문서 버전이 바뀌었습니다.";
          if (
            !completeText(sourceDoc.body, 100000) ||
            !completeText(sourceDoc.title, 1000) ||
            clean(sourceDoc.body, 100000) !== sourceDoc.body
          )
            reason = "문서 전체를 안전하게 표시할 수 없습니다.";
          document = {
            title: clean(sourceDoc.title, 1000),
            body: clean(sourceDoc.body, 100000),
            revision: clean(sourceDoc.latestRevisionId, 100),
          };
        }
      } else if (
        !(target.type === "custom" && target.key === "native_completion_review")
      )
        reason = "알 수 없는 확인 대상입니다.";
    }
    if (kind === "ask_user_questions") {
      if (
        (canonical.description !== undefined &&
          !completeText(canonical.description)) ||
        (canonical.title !== undefined && !completeText(canonical.title, 500))
      )
        reason = "질문 세트 안내를 모두 표시할 수 없습니다.";
      if (
        !questions.length ||
        storage.length > 20 ||
        canonicalQuestions.length > 20 ||
        questions.some((q) => !q.id || !storage.some((s) => s.id === q.id))
      )
        reason = "이 질문 세트의 개수 또는 저장 형식을 지원하지 않습니다.";
      if (
        (canonical.schema &&
          canonical.schema !== "paperclip.question_set.v1") ||
        canonicalQuestions.some(
          (q) =>
            !["text", "single_select", "multi_select"].includes(
              string(q.answerMode),
            ),
        )
      )
        reason = "알 수 없는 질문 형식입니다.";
      if (
        new Set(questions.map((q) => q.id)).size !== questions.length ||
        questions.some(
          (q) =>
            new Set(q.options.map((o) => o.id)).size !== q.options.length ||
            q.options.some((o) => !o.id),
        )
      )
        reason = "질문 또는 선택지 식별자가 올바르지 않습니다.";
      if (questions.some((q) => q.pattern))
        reason = "정규식 검증이 필요한 질문은 Paperclip에서 답해 주세요.";
      if (
        [...storage, ...canonicalQuestions].some(
          (q) =>
            !completeText(q.prompt) ||
            (q.header !== undefined && !completeText(q.header, 500)) ||
            (q.helpText !== undefined && !completeText(q.helpText, 10000)) ||
            list(q.options).length > 100 ||
            list(q.options).some(
              (o) =>
                !completeText(o.label, 2000) ||
                (o.description !== undefined &&
                  !completeText(o.description, 4000)),
            ),
        )
      )
        reason = "질문 전체가 표시 범위를 초과합니다.";
    } else if (
      !completeText(payload.prompt) ||
      (payload.detailsMarkdown !== undefined &&
        !completeText(payload.detailsMarkdown)) ||
      list(payload.options).length > 100 ||
      list(payload.options).some(
        (o) =>
          !completeText(o.label, 2000) ||
          (o.description !== undefined && !completeText(o.description, 4000)),
      )
    )
      reason = "확인 내용을 모두 표시할 수 없습니다.";
    if (
      (source.title !== undefined &&
        source.title !== null &&
        !completeText(source.title, 500)) ||
      (source.summary !== undefined &&
        source.summary !== null &&
        !completeText(source.summary))
    )
      reason = "요청 전체를 표시할 수 없습니다.";
    if (
      source.status !== "pending" ||
      ["done", "cancelled"].includes(string(issueSource.status))
    )
      reason = "이미 처리됐거나 종료된 요청입니다.";
    const native =
      target.type === "custom" && target.key === "native_completion_review";
    let reviewRun: Row | null = null;
    if (native) {
      if (!optionalId(source.sourceRunId))
        reason = "검토 대상 실행 정보를 확인할 수 없습니다.";
      else {
        reviewRun = member(
          row(await transport("GET", `/heartbeat-runs/${source.sourceRunId}`)),
          uuid(issueSource.companyId),
        );
        if (
          reviewRun.id !== source.sourceRunId ||
          !(
            object(reviewRun.contextSnapshot).issueId === issueSource.id ||
            reviewRun.issueId === issueSource.id
          )
        )
          reason = "검토 대상 실행과 이슈가 일치하지 않습니다.";
      }
    }
    const nativeContext = native
      ? `\n작업: ${clean(issueSource.title)}\n상태: ${clean(issueSource.status)}\n작업 모드: ${clean(issueSource.workMode)}\n검토 정책: ${clean(issueSource.reviewPolicy)}\n검토 버전: ${clean(target.revisionId, 100)}\n검토 대상 실행: ${clean(reviewRun?.id, 100)} / ${clean(reviewRun?.status)} / ${clean(reviewRun?.finishedAt)}`
      : "";
    return {
      id: uuid(source.id),
      issueId: uuid(issueSource.id),
      kind,
      status: clean(source.status),
      title:
        clean(source.title, 500) || clean(payload.title, 500) || "응답 요청",
      body: [
        clean(canonical.title, 500),
        clean(canonical.description, 20000),
        clean(payload.prompt, 20000),
        clean(payload.detailsMarkdown, 20000),
        clean(source.summary, 20000),
        nativeContext,
      ]
        .filter(Boolean)
        .join("\n\n"),
      fingerprint: hash({
        source,
        issue: {
          id: issueSource.id,
          status: issueSource.status,
          workMode: issueSource.workMode,
          reviewPolicy: issueSource.reviewPolicy,
        },
        document: sourceDoc,
        reviewRun: reviewRun
          ? {
              id: reviewRun.id,
              status: reviewRun.status,
              finishedAt: reviewRun.finishedAt,
            }
          : null,
      }),
      supported: !reason,
      reason,
      effect: native
        ? "승인하면 작업이 완료될 수 있습니다. 거절하면 수정 요청으로 돌아가 모델 실행이 이어질 수 있습니다."
        : "응답·확인 저장 후 에이전트 모델 호출이 이어질 수 있습니다. 일시 정지된 에이전트를 자동 재개하지 않습니다.",
      questions,
      options: options(payload.options),
      minSelected: number(payload.minSelected) ?? 0,
      maxSelected: number(payload.maxSelected) ?? 100,
      rejectRequiresReason: payload.rejectRequiresReason === true,
      document,
    };
  }
  async function contextRaw(companyId: string, issueId: string) {
    const source = await issue(companyId, issueId);
    const [interactionRows, approvalRows, holdValue, diagnosticValue] =
      await Promise.all([
        transport("GET", `/issues/${issueId}/interactions`),
        transport("GET", `/issues/${issueId}/approvals`),
        transport("GET", `/issues/${issueId}/tree-control/state`),
        transport("GET", `/issues/${issueId}/diagnostics/blockers`),
      ]);
    const allInteractions = list(interactionRows),
      allApprovals = list(approvalRows),
      hold = object(holdValue),
      diagnostic = object(diagnosticValue);
    for (const r of allInteractions) {
      member(r, companyId);
      if (r.issueId !== issueId) fail("이슈 요청 소속이 다릅니다.");
    }
    for (const r of allApprovals) member(r, companyId);
    const interactions = await Promise.all(
      allInteractions
        .filter(pending)
        .slice(0, 30)
        .map((r) => interactionProjection(r, source)),
    );
    const approvals = await Promise.all(
      allApprovals
        .filter(pending)
        .slice(0, 30)
        .map((r) => approvalProjection(r, companyId)),
    );
    const gates: string[] = [];
    if (interactions.length)
      gates.push("대기 질문·확인 요청에 먼저 응답하세요.");
    if (approvals.length) gates.push("대기 승인 요청을 먼저 처리하세요.");
    if (
      object(diagnostic.readiness).isDependencyReady !== true ||
      diagnostic.truncated === true
    )
      gates.push(
        "선행 작업이 준비되지 않았거나 준비 상태를 확인할 수 없습니다. 취소된 작업은 완료로 간주하지 않습니다.",
      );
    if (!Object.hasOwn(hold, "activePauseHold") || hold.activePauseHold)
      gates.push("작업 트리의 명시적 일시 정지가 적용되어 있습니다.");
    if (source.activeRecoveryAction)
      gates.push(
        "실행 복구·정합성 확인이 필요합니다. Paperclip의 복구 화면에서 확인하세요.",
      );
    const execution = object(source.executionBlocker);
    if (Object.keys(execution).length && execution.canRetry !== true)
      gates.push(
        clean(execution.nextAction, 500) ||
          "실행 차단 원인을 Paperclip에서 확인하세요.",
      );
    const assigned = optionalId(source.assigneeAgentId);
    let assignee: Row | null = null;
    if (assigned) {
      assignee = await agent(companyId, assigned);
      if (!eligible(assignee))
        gates.push(
          `담당 에이전트 상태: ${clean(assignee.status)}. 재개는 에이전트 탭에서 명시적으로 요청하세요.`,
        );
    }
    const scheduled = object(source.scheduledRetry);
    let failedRun: ReturnType<typeof publicContext>["failedRun"] = null;
    if (
      optionalId(execution.runId) &&
      optionalId(execution.agentId) &&
      execution.canRetry === true
    ) {
      const run = member(
        row(await transport("GET", `/heartbeat-runs/${execution.runId}`)),
        companyId,
      );
      if (
        run.id === execution.runId &&
        run.agentId === execution.agentId &&
        ["failed", "timed_out"].includes(string(run.status)) &&
        source.assigneeAgentId === run.agentId
      ) {
        const context = object(run.contextSnapshot);
        if (context.issueId === issueId || run.issueId === issueId)
          failedRun = {
            runId: uuid(run.id),
            agentId: uuid(run.agentId),
            status: clean(run.status),
            canRetry:
              gates.length === 0 && !source.scheduledRetry && !source.activeRun,
          };
      }
    }
    const deps = list(diagnostic.blockers)
      .slice(0, 100)
      .map((d) => ({
        id: uuid(d.id),
        title: clean(d.title, 500),
        status: clean(d.status),
        ready: d.isDependencyReady === true,
      }));
    const fingerprint = hash({
      source: {
        id: source.id,
        status: source.status,
        updatedAt: source.updatedAt,
        projectId: source.projectId,
        assigneeAgentId: source.assigneeAgentId,
        execution,
        scheduled,
        activeRecoveryAction: source.activeRecoveryAction,
        activeRun: source.activeRun,
      },
      hold,
      diagnostic,
      interactions: allInteractions.map((r) => ({
        id: r.id,
        status: r.status,
        updatedAt: r.updatedAt,
      })),
      approvals: allApprovals.map((r) => ({
        id: r.id,
        status: r.status,
        updatedAt: r.updatedAt,
      })),
    });
    const result = {
      fingerprint,
      status: clean(source.status),
      assigneeId: assigned,
      gates,
      canStart:
        source.status === "backlog" &&
        gates.length === 0 &&
        !source.activeRun &&
        !source.scheduledRetry,
      dependencies: deps,
      interactions,
      approvals,
      scheduledRetry: optionalId(scheduled.runId)
        ? {
            runId: uuid(scheduled.runId),
            status: clean(scheduled.status),
            at: clean(scheduled.scheduledRetryAt),
            canRetry:
              scheduled.status === "scheduled_retry" && gates.length === 0,
          }
        : null,
      failedRun,
      truncated:
        allInteractions.filter(pending).length > 30 ||
        allApprovals.filter(pending).length > 30 ||
        diagnostic.truncated === true,
    };
    return { source, result, allInteractions };
  }
  function publicContext() {
    return {} as {
      failedRun: {
        runId: string;
        agentId: string;
        status: string;
        canRetry: boolean;
      } | null;
    };
  }
  async function context(input: unknown) {
    const { companyId, issueId } = detailInput.parse(input);
    return (await contextRaw(companyId, issueId)).result;
  }
  async function approval(input: unknown) {
    const { companyId, approvalId } = approvalRpc.input.parse(input);
    await company(companyId);
    const source = member(
      row(await transport("GET", `/approvals/${approvalId}`)),
      companyId,
    );
    if (source.id !== approvalId) fail("승인 식별자가 일치하지 않습니다.");
    return approvalProjection(source, companyId);
  }
  async function agentAction(input: unknown) {
    const { companyId, agentId } = agentActionRpc.input.parse(input);
    const source = await agent(companyId, agentId);
    return {
      id: agentId,
      name: clean(source.name),
      status: clean(source.status),
      fingerprint: hash({
        id: source.id,
        status: source.status,
        updatedAt: source.updatedAt,
      }),
    };
  }
  async function inbox(input: unknown) {
    const { companyId, cursor } = inboxRpc.input.parse(input);
    await company(companyId);
    const feed = member(
      row(
        await transport(
          "GET",
          `/companies/${companyId}/attention?limit=50${cursor ? "&cursor=" + encodeURIComponent(cursor) : ""}`,
        ),
      ),
      companyId,
    );
    const approvals = cursor
      ? []
      : await Promise.all(
          rows(
            await transport(
              "GET",
              `/companies/${companyId}/approvals?status=pending`,
            ),
            30,
          ).map((a) => approvalProjection(a, companyId)),
        );
    const items = rows(feed.items, 50).map((item) => {
      const subject = object(item.subject),
        meta = object(subject.metadata),
        related = object(item.relatedIssue),
        detail = object(item.detail);
      for (const value of [item, subject, meta, related])
        if (value.companyId !== undefined) member(value, companyId);
      return {
        id: clean(item.id, 200) || clean(subject.id, 200),
        source: clean(item.sourceKind),
        title:
          clean(subject.title, 500) ||
          clean(related.title, 500) ||
          clean(item.title, 500) ||
          "응답 요청",
        detail: [
          clean(detail.firstQuestionText, 1500),
          clean(item.whyNow, 500),
          typeof item.detail === "string" ? clean(item.detail, 2000) : "",
        ]
          .filter(Boolean)
          .join("\n"),
        issueId: optionalId(meta.issueId) || optionalId(related.id),
        interactionId:
          item.sourceKind === "issue_thread_interaction"
            ? optionalId(subject.id)
            : null,
        approvalId:
          item.sourceKind === "approval" ? optionalId(subject.id) : null,
      };
    });
    return {
      items,
      nextCursor:
        typeof feed.nextCursor === "string" && feed.nextCursor.length <= 2000
          ? feed.nextCursor
          : null,
      totalCount: number(feed.totalCount) ?? items.length,
      approvals,
      truncated: list(feed.items).length > 50 || approvals.length === 30,
    };
  }
  async function action(input: unknown): Promise<Receipt> {
    const value = actionInput.parse(input),
      contentHash = hash(value),
      key =
        value.companyId +
        ":" +
        (value.kind === "retryFailed"
          ? "failed-run:" + value.runId
          : value.operationId);
    const old = await ledger.get(key);
    if (old) {
      same(old.fingerprint, contentHash);
      if (old.result) return old.result;
      fail(
        "이 요청 결과가 불명확합니다. 재전송하지 말고 현재 상태와 접수 기록을 확인해 주세요.",
      );
    }
    const target =
      value.companyId +
      ":" +
      ("issueId" in value
        ? value.issueId
        : "approvalId" in value
          ? value.approvalId
          : "agentId" in value && value.kind === "resume"
            ? value.agentId
            : "new:" + value.operationId);
    if (locks.has(target)) fail("같은 대상의 요청을 처리 중입니다.");
    locks.add(target);
    let claimed = false;
    const write = async (
      method: "POST" | "PATCH",
      path: string,
      body: unknown,
    ) => {
      await ledger.claim(key, target, contentHash);
      claimed = true;
      return transport(method, path, body);
    };
    try {
      let result: Receipt;
      if (value.kind === "submit") {
        const owner = await company(value.companyId);
        if (owner.status !== "active")
          fail("활성 회사에서만 작업을 요청할 수 있습니다.");
        await project(value.companyId, value.projectId);
        const worker = await agent(value.companyId, value.agentId);
        if (!eligible(worker))
          fail(
            "담당 에이전트를 먼저 명시적으로 재개하거나 다른 담당자를 선택해 주세요.",
          );
        await externalOff();
        const created = member(
          row(
            await write("POST", `/companies/${value.companyId}/issues`, {
              title: value.title,
              description: value.description,
              projectId: value.projectId,
              status: "todo",
              priority: "medium",
              assigneeAgentId: value.agentId,
              assigneeUserId: null,
              parentId: null,
              watchdog: null,
              executionPolicy: null,
              idempotencyKey: "panel-submit:" + value.operationId,
              allowDuplicate: true,
            }),
          ),
          value.companyId,
        );
        if (
          created.projectId !== value.projectId ||
          created.assigneeAgentId !== value.agentId ||
          !["todo", "in_progress", "in_review", "done", "blocked"].includes(
            string(created.status),
          )
        )
          fail(
            "작업은 접수되었을 수 있으나 프로젝트·담당자·상태가 요청과 다릅니다. 목록을 확인하세요.",
          );
        result = {
          status: clean(created.status),
          message:
            "작업 요청이 접수되었습니다. 실행 시작·완료 여부는 상태를 새로 확인해 주세요.",
          issueId: uuid(created.id),
        };
      } else if (value.kind === "resume") {
        const fresh = await agentAction({
          companyId: value.companyId,
          agentId: value.agentId,
        });
        same(fresh.fingerprint, value.fingerprint);
        if (fresh.status !== "paused")
          fail("일시 정지된 에이전트만 재개할 수 있습니다.");
        const resumed = member(
          row(await write("POST", `/agents/${value.agentId}/resume`, {})),
          value.companyId,
        );
        if (resumed.id !== value.agentId)
          fail("재개 응답이 일치하지 않습니다.");
        result = {
          status: clean(resumed.status),
          message:
            "에이전트 재개를 반영했습니다. 다른 대기 업무도 실행될 수 있습니다.",
        };
      } else if (value.kind === "approve" || value.kind === "rejectApproval") {
        const fresh = await approval({
          companyId: value.companyId,
          approvalId: value.approvalId,
        });
        same(fresh.fingerprint, value.fingerprint);
        if (!fresh.supported) fail(fresh.reason);
        const decided = member(
          row(
            await write(
              "POST",
              `/approvals/${value.approvalId}/${value.kind === "approve" ? "approve" : "reject"}`,
              { decisionNote: value.note },
            ),
          ),
          value.companyId,
        );
        if (decided.id !== value.approvalId)
          fail("승인 응답이 일치하지 않습니다.");
        result = {
          status: clean(decided.status),
          message:
            "승인 결정을 저장했습니다. 실행 재개 여부는 별도로 확인해 주세요.",
        };
      } else if ("issueId" in value) {
        const raw = await contextRaw(value.companyId, value.issueId),
          ctx = raw.result;
        if (["answer", "accept", "reject"].includes(value.kind)) {
          const v = value as Extract<
            Action,
            { kind: "answer" | "accept" | "reject" }
          >;
          const card = ctx.interactions.find((c) => c.id === v.interactionId);
          if (!card) fail("대기 중인 요청을 찾을 수 없습니다.");
          same(card.fingerprint, v.fingerprint);
          if (!card.supported) fail(card.reason);
          let body: unknown = {};
          let route = "";
          if (v.kind === "answer") {
            if (card.kind !== "ask_user_questions")
              fail("질문 요청이 아닙니다.");
            const source = raw.allInteractions.find(
              (s) => s.id === v.interactionId,
            )!;
            body = {
              answers: validateAnswers(card, v.answers, object(source.payload)),
            };
            route = "respond";
          } else {
            if (
              ![
                "request_confirmation",
                "request_checkbox_confirmation",
              ].includes(card.kind)
            )
              fail("확인 요청이 아닙니다.");
            if (v.kind === "accept") {
              const selected = v.selectedOptionIds;
              if (
                new Set(selected).size !== selected.length ||
                selected.some((s) => !card.options.some((o) => o.id === s)) ||
                selected.length < card.minSelected ||
                selected.length > card.maxSelected
              )
                fail("확인 선택지를 다시 확인해 주세요.");
              if (card.kind === "request_confirmation" && selected.length)
                fail("일반 확인에는 선택지를 보낼 수 없습니다.");
              body =
                card.kind === "request_checkbox_confirmation"
                  ? { selectedOptionIds: selected }
                  : {};
              route = "accept";
            } else {
              if (card.rejectRequiresReason && !v.reason.trim())
                fail("거절 사유를 적어 주세요.");
              body = v.reason ? { reason: v.reason } : {};
              route = "reject";
            }
          }
          const saved = member(
            row(
              await write(
                "POST",
                `/issues/${value.issueId}/interactions/${v.interactionId}/${route}`,
                body,
              ),
            ),
            value.companyId,
          );
          if (saved.id !== v.interactionId || saved.issueId !== value.issueId)
            fail("응답 저장 결과가 일치하지 않습니다.");
          result = {
            status: clean(saved.status),
            message:
              "응답을 저장했습니다. 실행 전달·재개 성공을 뜻하지는 않습니다.",
            issueId: value.issueId,
          };
        } else {
          same(ctx.fingerprint, value.fingerprint);
          if (value.kind === "start") {
            if (!ctx.canStart)
              fail(
                "초안의 질문·승인·선행 작업·실행 차단 조건을 먼저 해결하세요.",
              );
            await project(value.companyId, uuid(raw.source.projectId));
            if (!eligible(await agent(value.companyId, value.agentId)))
              fail("일시 정지된 담당자를 자동 재개하지 않습니다.");
            const updated = member(
              row(
                await write("PATCH", `/issues/${value.issueId}`, {
                  status: "todo",
                  assigneeAgentId: value.agentId,
                  assigneeUserId: null,
                }),
              ),
              value.companyId,
            );
            if (
              updated.id !== value.issueId ||
              updated.projectId !== raw.source.projectId ||
              updated.assigneeAgentId !== value.agentId
            )
              fail("작업 응답의 프로젝트·담당자가 일치하지 않습니다.");
            result = {
              status: clean(updated.status),
              message:
                "초안 실행 요청을 접수했습니다. 모델 실행 여부는 현재 상태로 확인하세요.",
              issueId: value.issueId,
            };
          } else if (value.kind === "retryScheduled") {
            if (
              !ctx.scheduledRetry?.canRetry ||
              ctx.scheduledRetry.runId !== value.runId
            )
              fail(
                "예약된 재시도가 바뀌었거나 실행 조건이 충족되지 않았습니다.",
              );
            const receipt = row(
              await write(
                "POST",
                `/issues/${value.issueId}/scheduled-retry/retry-now`,
                {},
              ),
            );
            const outcome = string(receipt.outcome);
            if (
              ![
                "promoted",
                "already_promoted",
                "no_scheduled_retry",
                "gate_suppressed",
              ].includes(outcome)
            )
              fail("재시도 결과를 해석할 수 없습니다.");
            result = {
              status: "recorded",
              message:
                clean(receipt.message, 1000) ||
                "예약 재시도 결과를 확인하세요.",
              outcome,
              issueId: value.issueId,
            };
          } else if (value.kind === "retryFailed") {
            if (!ctx.failedRun?.canRetry || ctx.failedRun.runId !== value.runId)
              fail("이 실패 실행을 안전하게 재시도할 수 없습니다.");
            const receipt = row(
              await write("POST", `/agents/${ctx.failedRun.agentId}/wakeup`, {
                source: "on_demand",
                triggerDetail: "manual",
                reason: "retry_failed_run",
                failedRunId: value.runId,
                idempotencyKey: "panel-retry:" + value.operationId,
              }),
            );
            result = {
              status: clean(receipt.status) || "requested",
              message:
                receipt.skipped === true
                  ? "서버가 재시도 실행을 건너뛰었습니다. 사유와 현재 상태를 확인하세요."
                  : receipt.queued === true
                    ? "재시도 요청이 대기열에 접수되었습니다. 실제 실행 여부는 새로 확인하세요."
                    : "지정한 실패 실행의 재시도 요청을 접수했습니다. 실제 실행 여부는 새로 확인하세요.",
              outcome:
                receipt.skipped === true
                  ? "skipped"
                  : receipt.queued === true
                    ? "queued"
                    : "requested",
              issueId: value.issueId,
            };
          } else if (value.kind === "comment") {
            await externalOff();
            const saved = row(
              await write("POST", `/issues/${value.issueId}/comments`, {
                body: value.body,
              }),
            );
            if (
              saved.companyId !== value.companyId ||
              saved.issueId !== value.issueId
            )
              fail("추가 지시 응답이 일치하지 않습니다.");
            result = {
              status: "saved",
              message:
                "추가 지시를 저장했습니다. 모델 실행이 이어질 수 있습니다.",
              issueId: value.issueId,
            };
          } else return fail("지원하지 않는 작업입니다.");
        }
      } else return fail("지원하지 않는 작업입니다.");
      await ledger.finish(key, target, contentHash, result);
      return result;
    } catch (error) {
      if (claimed)
        throw Error(
          "요청 결과를 확정할 수 없습니다. 자동 재전송하지 않습니다. 목록·대기함과 로컬 접수 기록을 확인해 주세요.",
        );
      throw new PrewriteRejection(
        error instanceof Error ? error.message : "요청 조건을 확인해 주세요.",
      );
    } finally {
      locks.delete(target);
    }
  }
  async function actionReply(input: unknown): Promise<Receipt> {
    try {
      return await action(input);
    } catch (error) {
      if (error instanceof PrewriteRejection)
        return {
          status: "not_sent",
          outcome: "prewrite_rejected",
          message: error.message,
        };
      throw error;
    }
  }
  return { inbox, context, approval, agentAction, action, actionReply };
}
