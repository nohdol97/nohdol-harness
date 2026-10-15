import { useEffect, useRef, useState } from "react";
import { AppState, Pressable, Text, TextInput, View } from "react-native";
import { useRpc } from "@getpaseo/plugin/client";
import type { PluginHostProps } from "@getpaseo/plugin/client";
import {
  useInfiniteQuery,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  actionRpc,
  agentActionRpc,
  approvalRpc,
  contextRpc,
  inboxRpc,
  type Action,
  type Approval,
  type Interaction,
  type Question,
  type Receipt,
} from "../shared/actions";
import type { Agent } from "../shared/contracts";
type Colors = PluginHostProps["theme"]["colors"];
export const newOperationId = () =>
  "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = Math.floor(Math.random() * 16);
    return (c === "x" ? r : (r & 3) | 8).toString(16);
  });
export function usePanelVisible() {
  const [visible, setVisible] = useState(
    AppState.currentState !== "background" &&
      AppState.currentState !== "inactive",
  );
  useEffect(() => {
    const sub = AppState.addEventListener("change", (state) =>
      setVisible(state === "active"),
    );
    return () => sub.remove();
  }, []);
  return visible;
}
const errorText = (error: unknown) =>
  error instanceof Error
    ? error.message.slice(0, 500)
    : "요청을 완료할 수 없습니다.";
function Body({
  children,
  colors,
  error = false,
}: {
  children: React.ReactNode;
  colors: Colors;
  error?: boolean;
}) {
  return (
    <Text
      selectable
      style={{
        color: error ? colors.statusDanger : colors.foreground,
        fontSize: 14,
        lineHeight: 22,
      }}
    >
      {children}
    </Text>
  );
}
function SmallButton({
  label,
  colors,
  onPress,
  disabled = false,
  active = false,
}: {
  label: string;
  colors: Colors;
  onPress(): void;
  disabled?: boolean;
  active?: boolean;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      disabled={disabled}
      accessibilityState={{ disabled, selected: active }}
      onPress={onPress}
      style={{
        padding: 12,
        minHeight: 44,
        borderRadius: 9,
        borderWidth: 1,
        borderColor: active ? colors.accent : colors.border,
        backgroundColor: active ? colors.accent : colors.surface0,
        opacity: disabled ? 0.5 : 1,
      }}
    >
      <Text
        style={{
          color: active ? colors.accentForeground : colors.foreground,
          fontSize: 13,
        }}
      >
        {label}
      </Text>
    </Pressable>
  );
}
function Field({
  value,
  onChange,
  placeholder,
  colors,
  multiline = false,
  maxLength = 20000,
}: {
  value: string;
  onChange(value: string): void;
  placeholder: string;
  colors: Colors;
  multiline?: boolean;
  maxLength?: number;
}) {
  return (
    <TextInput
      accessibilityLabel={placeholder}
      placeholder={placeholder}
      placeholderTextColor={colors.foregroundMuted}
      value={value}
      onChangeText={onChange}
      multiline={multiline}
      maxLength={maxLength}
      textAlignVertical="top"
      style={{
        color: colors.foreground,
        padding: 12,
        borderWidth: 1,
        borderColor: colors.border,
        borderRadius: 9,
        minHeight: multiline ? 100 : 44,
        backgroundColor: colors.surface0,
      }}
    />
  );
}
export function ActionButton({
  action,
  label,
  warning,
  colors,
  disabled = false,
  onDone,
}: {
  action: Omit<Action, "operationId" | "confirmed">;
  label: string;
  warning: string;
  colors: Colors;
  disabled?: boolean;
  onDone?(receipt: Receipt): void;
}) {
  const invoke = useRpc(actionRpc),
    client = useQueryClient();
  const [intent, setIntent] = useState<typeof action | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [receipt, setReceipt] = useState<Receipt | null>(null),
    [uncertain, setUncertain] = useState(false);
  const lock = useRef(false),
    operation = useRef(newOperationId()),
    sent = useRef("");
  const serialized = JSON.stringify(action),
    changed = !!sent.current && sent.current !== serialized;

  const staleIntent = !!intent && JSON.stringify(intent) !== serialized;
  function reviewNew() {
    if (uncertain) return;
    operation.current = newOperationId();
    sent.current = "";
    setReceipt(null);
    setError("");
    setUncertain(false);
    setIntent(action);
  }
  async function send() {
    if (lock.current || !intent || staleIntent) return;
    lock.current = true;
    setBusy(true);
    setError("");
    sent.current = JSON.stringify(intent);
    try {
      const result = await invoke({
        ...intent,
        operationId: operation.current,
        confirmed: true,
      } as Action);
      if (result.outcome === "prewrite_rejected") {
        setError(result.message);
        setUncertain(false);
        setIntent(null);
        return;
      }
      setReceipt(result);
      setIntent(null);
      void client.invalidateQueries({
        predicate: (q) =>
          q.queryKey[0] === "paperclip" &&
          q.queryKey.includes(action.companyId),
      });
      onDone?.(result);
    } catch (e) {
      setError(errorText(e));
      setUncertain(true);
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  return (
    <View style={{ gap: 8 }}>
      {receipt ? (
        <Body colors={colors}>
          {receipt.message}
          {"\n"}응답 상태: {receipt.status}
          {receipt.outcome ? ` / ${receipt.outcome}` : ""}
        </Body>
      ) : (
        <SmallButton
          label={label}
          colors={colors}
          disabled={disabled || busy || uncertain}
          onPress={() => {
            setError("");
            setIntent(action);
          }}
        />
      )}
      {((receipt && changed) || (error && !uncertain)) && (
        <SmallButton
          label="새 요청 검토"
          colors={colors}
          disabled={disabled || busy}
          onPress={reviewNew}
        />
      )}{" "}
      {intent && !receipt && (
        <View
          style={{
            gap: 10,
            padding: 12,
            borderWidth: 1,
            borderColor: colors.statusWarning,
            borderRadius: 10,
          }}
        >
          <Body colors={colors}>{warning}</Body>
          {staleIntent && (
            <Body colors={colors} error>
              입력 또는 작업 상태가 변경되었습니다. 돌아간 뒤 새 내용을
              확인하세요.
            </Body>
          )}
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
            <SmallButton
              label={busy ? "처리 중…" : `${label} 확인`}
              colors={colors}
              active
              disabled={busy || uncertain || staleIntent || disabled}
              onPress={() => void send()}
            />
            <SmallButton
              label="돌아가기"
              colors={colors}
              disabled={busy}
              onPress={() => setIntent(null)}
            />
          </View>
        </View>
      )}
      {error && (
        <Body colors={colors} error>
          {error}
          {"\n"}입력은 보존됩니다.{" "}
          {uncertain
            ? "재전송하지 말고 접수 여부를 확인하세요."
            : "입력·상태를 확인한 후 새 요청을 검토할 수 있습니다."}
        </Body>
      )}
    </View>
  );
}
export function AgentPicker({
  agents,
  value,
  onChange,
  colors,
}: {
  agents: Agent[];
  value: string;
  onChange(id: string): void;
  colors: Colors;
}) {
  return (
    <View style={{ gap: 8 }}>
      <Body colors={colors}>
        담당자 선택 · 일시 정지는 자동 해제하지 않습니다.
      </Body>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
        {agents.map((a) => (
          <SmallButton
            key={a.id}
            label={`${a.name} (${a.status})`}
            colors={colors}
            active={value === a.id}
            disabled={
              !["idle", "running", "active", "error"].includes(a.status)
            }
            onPress={() => onChange(a.id)}
          />
        ))}
      </View>
    </View>
  );
}
export function ResumeAgent({
  companyId,
  agentId,
  colors,
  hostId,
}: {
  companyId: string;
  agentId: string;
  colors: Colors;
  hostId: string;
}) {
  const rpc = useRpc(agentActionRpc);
  const [open, setOpen] = useState(false);
  const query = useQuery({
    queryKey: ["paperclip", hostId, companyId, "agent-action", agentId],
    queryFn: () => rpc({ companyId, agentId }),
    enabled: open,
    retry: false,
  });
  return (
    <View style={{ gap: 8 }}>
      <SmallButton
        label="에이전트 재개"
        colors={colors}
        onPress={() => setOpen(!open)}
      />
      {open && query.error && (
        <Body colors={colors} error>
          {errorText(query.error)}
        </Body>
      )}
      {open && query.data && (
        <ActionButton
          action={
            {
              kind: "resume",
              companyId,
              agentId,
              fingerprint: query.data.fingerprint,
            } as Action
          }
          label="재개 요청"
          warning="이 에이전트 전체의 일시 정지를 해제합니다. 선택한 작업 외의 대기 업무·예약 업무도 모델을 호출할 수 있습니다."
          colors={colors}
          disabled={query.data.status !== "paused"}
        />
      )}
    </View>
  );
}

export function useInbox(companyId: string, hostId: string) {
  const rpc = useRpc(inboxRpc);
  const visible = usePanelVisible();
  return useInfiniteQuery({
    queryKey: ["paperclip", hostId, companyId, "inbox"],
    initialPageParam: "" as string,
    queryFn: ({ pageParam }) =>
      rpc({ companyId, ...(pageParam ? { cursor: pageParam } : {}) }),
    getNextPageParam: (last) => last.nextCursor ?? undefined,
    refetchInterval: visible ? 30000 : false,
    refetchIntervalInBackground: false,
    retry: false,
  });
}
export function Inbox({
  query,
  companyId,
  colors,
  onIssue,
  hostId,
}: {
  query: ReturnType<typeof useInbox>;
  companyId: string;
  colors: Colors;
  onIssue(id: string): void;
  hostId: string;
}) {
  const [approvalId, setApproval] = useState("");
  const items = [
    ...new Map(
      query.data?.pages.flatMap((p) => p.items).map((i) => [i.id, i]) ?? [],
    ).values(),
  ];
  return (
    <View style={{ gap: 12 }}>
      <Body colors={colors}>
        내 응답 필요 · 화면 표시 중 30초마다 확인합니다. 답변·승인은 모델 실행을
        이어갈 수 있습니다.
      </Body>
      <SmallButton
        label="대기함 새로고침"
        colors={colors}
        disabled={query.isFetching}
        onPress={() => void query.refetch()}
      />
      {query.isPending && <Body colors={colors}>대기 요청을 불러오는 중…</Body>}
      {query.error && (
        <Body colors={colors} error>
          {errorText(query.error)}
        </Body>
      )}
      {!query.isPending && !items.length && (
        <Body colors={colors}>지금 응답할 요청이 없습니다.</Body>
      )}
      {items.map((item) => (
        <View
          key={item.id}
          style={{
            gap: 8,
            padding: 14,
            borderWidth: 1,
            borderColor: colors.border,
            borderRadius: 12,
          }}
        >
          <Text
            style={{
              color: colors.foreground,
              fontWeight: "700",
              fontSize: 16,
            }}
          >
            {item.title}
          </Text>
          <Body colors={colors}>{item.detail}</Body>
          {item.issueId && (
            <SmallButton
              label="작업과 요청 열기"
              colors={colors}
              onPress={() => onIssue(item.issueId!)}
            />
          )}{" "}
          {item.approvalId && (
            <SmallButton
              label="승인 내용 열기"
              colors={colors}
              onPress={() => setApproval(item.approvalId!)}
            />
          )}{" "}
          {!item.issueId && !item.approvalId && (
            <Body colors={colors}>
              이 항목은 Paperclip 전용 화면에서 확인하세요.
            </Body>
          )}
        </View>
      ))}
      {query.data?.pages[0].approvals.map((approval) => (
        <View key={approval.id} style={{ gap: 8 }}>
          <SmallButton
            label={`업무 승인 · ${approval.title}`}
            colors={colors}
            onPress={() => setApproval(approval.id)}
          />
        </View>
      ))}
      {query.hasNextPage && (
        <SmallButton
          label="요청 더 보기"
          colors={colors}
          disabled={query.isFetchingNextPage || query.data!.pages.length >= 10}
          onPress={() => void query.fetchNextPage()}
        />
      )}{" "}
      {(query.data?.pages.some((p) => p.truncated) ||
        (query.data && query.data.pages.length >= 10)) && (
        <Body colors={colors}>
          표시 한도에 도달했습니다. 나머지 요청은 Paperclip에서 확인하세요.
        </Body>
      )}
      {approvalId && (
        <ApprovalForm
          key={approvalId}
          hostId={hostId}
          companyId={companyId}
          approvalId={approvalId}
          colors={colors}
        />
      )}
    </View>
  );
}
function Choices({
  question,
  selected,
  onChange,
  colors,
}: {
  question: Question;
  selected: string[];
  onChange(value: string[]): void;
  colors: Colors;
}) {
  return (
    <View style={{ gap: 8 }}>
      {question.options.map((option) => (
        <SmallButton
          key={option.id}
          colors={colors}
          label={`${selected.includes(option.id) ? "✓ " : ""}${option.label}${option.description ? " — " + option.description : ""}`}
          active={selected.includes(option.id)}
          onPress={() =>
            onChange(
              selected.includes(option.id)
                ? selected.filter((v) => v !== option.id)
                : question.mode === "multi"
                  ? [...selected, option.id]
                  : [option.id],
            )
          }
        />
      ))}
    </View>
  );
}
export function InteractionForm({
  card,
  companyId,
  colors,
}: {
  card: Interaction;
  companyId: string;
  colors: Colors;
}) {
  const [snapshot, setSnapshot] = useState(card);
  const [answers, setAnswers] = useState<
    Record<string, { optionIds: string[]; otherText: string }>
  >({});
  const [selected, setSelected] = useState<string[]>([]),
    [reason, setReason] = useState("");
  const current = snapshot;
  const stale = current.fingerprint !== card.fingerprint;
  const q = current.questions;
  const answerBody = q.map((question) => ({
    questionId: question.id,
    optionIds: answers[question.id]?.optionIds ?? [],
    ...(answers[question.id]?.otherText
      ? { otherText: answers[question.id].otherText }
      : {}),
  }));
  const requiredMissing = q.some(
    (question) =>
      question.required &&
      !answers[question.id]?.optionIds.length &&
      !answers[question.id]?.otherText.trim(),
  );
  const base = {
    companyId,
    issueId: current.issueId,
    interactionId: current.id,
    fingerprint: current.fingerprint,
  };
  return (
    <View
      style={{
        gap: 12,
        padding: 14,
        borderWidth: 1,
        borderColor: colors.border,
        borderRadius: 12,
      }}
    >
      <Text
        style={{ color: colors.foreground, fontWeight: "700", fontSize: 17 }}
      >
        {current.title}
      </Text>
      <Body colors={colors}>{current.body}</Body>
      <Body colors={colors}>{current.effect}</Body>
      {stale && (
        <>
          <Body colors={colors} error>
            요청 내용이 변경되었습니다. 입력은 보존했으며 제출을 잠갔습니다.
          </Body>
          <SmallButton
            colors={colors}
            label="새 내용 확인"
            onPress={() => setSnapshot(card)}
          />
        </>
      )}
      {current.document && (
        <View style={{ gap: 8 }}>
          <Body colors={colors}>
            문서: {current.document.title} · 버전 {current.document.revision}
          </Body>
          <Body colors={colors}>{current.document.body}</Body>
        </View>
      )}
      {!current.supported ? (
        <Body colors={colors} error>
          {current.reason}
        </Body>
      ) : current.kind === "ask_user_questions" ? (
        <>
          {q.map((question) => {
            const answer = answers[question.id] ?? {
              optionIds: [],
              otherText: "",
            };
            const change = (patch: Partial<typeof answer>) =>
              setAnswers((v) => ({
                ...v,
                [question.id]: { ...answer, ...patch },
              }));
            return (
              <View key={question.id} style={{ gap: 8 }}>
                <Body colors={colors}>
                  {question.prompt}
                  {question.required ? " *" : " (선택)"}
                </Body>
                {question.help && <Body colors={colors}>{question.help}</Body>}
                {question.mode !== "text" && (
                  <Choices
                    question={question}
                    selected={answer.optionIds}
                    onChange={(optionIds) => change({ optionIds })}
                    colors={colors}
                  />
                )}{" "}
                {(question.mode === "text" ||
                  question.custom ||
                  question.options.some(
                    (o) => o.freeText && answer.optionIds.includes(o.id),
                  )) && (
                  <Field
                    colors={colors}
                    value={answer.otherText}
                    onChange={(otherText) => change({ otherText })}
                    placeholder={`${question.prompt} 직접 입력`}
                    maxLength={Math.min(question.maxLength ?? 100000, 100000)}
                    multiline
                  />
                )}
                {(question.minLength !== null ||
                  question.maxLength !== null ||
                  question.inputType !== "text") && (
                  <Body colors={colors}>
                    조건: {question.inputType} · 길이 {question.minLength ?? 0}–
                    {question.maxLength ?? "제한 없음"}
                    {question.minimum !== null
                      ? ` · 최소 ${question.minimum}`
                      : ""}
                    {question.maximum !== null
                      ? ` · 최대 ${question.maximum}`
                      : ""}
                  </Body>
                )}
              </View>
            );
          })}
          <ActionButton
            action={{ ...base, kind: "answer", answers: answerBody } as Action}
            colors={colors}
            label="답변 저장"
            warning={current.effect}
            disabled={stale || requiredMissing}
          />
        </>
      ) : (
        <>
          {current.options.map((option) => (
            <SmallButton
              key={option.id}
              colors={colors}
              label={`${selected.includes(option.id) ? "✓ " : ""}${option.label}${option.description ? " — " + option.description : ""}`}
              active={selected.includes(option.id)}
              onPress={() =>
                setSelected((v) =>
                  v.includes(option.id)
                    ? v.filter((x) => x !== option.id)
                    : [...v, option.id],
                )
              }
            />
          ))}
          {current.options.length > 0 && (
            <Body colors={colors}>
              선택 수: {current.minSelected}–{current.maxSelected}
            </Body>
          )}
          <ActionButton
            action={
              { ...base, kind: "accept", selectedOptionIds: selected } as Action
            }
            colors={colors}
            label="검토 후 승인"
            warning={current.effect}
            disabled={
              stale ||
              selected.length < current.minSelected ||
              selected.length > current.maxSelected
            }
          />
          <Field
            colors={colors}
            value={reason}
            onChange={setReason}
            placeholder={
              current.rejectRequiresReason
                ? "거절 사유 (필수)"
                : "거절 사유 (선택)"
            }
            maxLength={4000}
            multiline
          />
          <ActionButton
            action={{ ...base, kind: "reject", reason } as Action}
            colors={colors}
            label="거절 / 수정 요청"
            warning={current.effect}
            disabled={stale || (current.rejectRequiresReason && !reason.trim())}
          />
        </>
      )}
    </View>
  );
}
export function ApprovalForm({
  companyId,
  approvalId,
  colors,
  hostId,
}: {
  companyId: string;
  approvalId: string;
  colors: Colors;
  hostId: string;
}) {
  const rpc = useRpc(approvalRpc);
  const query = useQuery({
    queryKey: ["paperclip", hostId, companyId, "approval", approvalId],
    queryFn: () => rpc({ companyId, approvalId }),
    retry: false,
  });
  return (
    <View style={{ gap: 10 }}>
      {query.error && (
        <Body colors={colors} error>
          {errorText(query.error)}
        </Body>
      )}
      {query.data ? (
        <ApprovalDecision
          key={approvalId}
          approval={query.data}
          companyId={companyId}
          colors={colors}
        />
      ) : (
        <Body colors={colors}>승인 내용을 불러오는 중…</Body>
      )}
    </View>
  );
}
function ApprovalDecision({
  approval,
  companyId,
  colors,
}: {
  approval: Approval;
  companyId: string;
  colors: Colors;
}) {
  const [snapshot, setSnapshot] = useState(approval),
    [note, setNote] = useState("");
  const stale = snapshot.fingerprint !== approval.fingerprint;
  return (
    <View
      style={{
        gap: 10,
        padding: 14,
        borderWidth: 1,
        borderColor: colors.border,
        borderRadius: 12,
      }}
    >
      <Text
        style={{ color: colors.foreground, fontWeight: "700", fontSize: 17 }}
      >
        {snapshot.title}
      </Text>
      <Body colors={colors}>{snapshot.body}</Body>
      {stale && (
        <SmallButton
          label="변경된 승인 내용 확인"
          colors={colors}
          onPress={() => setSnapshot(approval)}
        />
      )}{" "}
      {!snapshot.supported ? (
        <Body colors={colors} error>
          {snapshot.reason}
        </Body>
      ) : (
        <>
          <Field
            value={note}
            onChange={setNote}
            colors={colors}
            placeholder="결정 의견 (선택)"
            multiline
            maxLength={4000}
          />
          {(["approve", "rejectApproval"] as const).map((kind) => (
            <ActionButton
              key={kind}
              colors={colors}
              action={
                {
                  kind,
                  companyId,
                  approvalId: snapshot.id,
                  fingerprint: snapshot.fingerprint,
                  note,
                } as Action
              }
              label={kind === "approve" ? "업무 승인" : "업무 거절"}
              warning="결정이 저장되며 요청자 또는 다른 대기 에이전트가 모델 호출을 이어갈 수 있습니다."
              disabled={stale}
            />
          ))}
        </>
      )}
    </View>
  );
}
export function IssueActions({
  companyId,
  issueId,
  hostId,
  agents,
  colors,
  onIssue,
}: {
  companyId: string;
  issueId: string;
  hostId: string;
  agents: Agent[];
  colors: Colors;
  onIssue(id: string): void;
}) {
  const rpc = useRpc(contextRpc),
    visible = usePanelVisible();
  const query = useQuery({
    queryKey: ["paperclip", hostId, companyId, "context", issueId],
    queryFn: () => rpc({ companyId, issueId }),
    retry: false,
    refetchInterval: visible ? 30000 : false,
    refetchIntervalInBackground: false,
  });
  const [agentId, setAgent] = useState(""),
    [comment, setComment] = useState("");
  const ctx = query.data;
  const [displayedCards, setDisplayedCards] = useState<Interaction[]>([]);
  const [displayedApprovals, setDisplayedApprovals] = useState<Approval[]>([]);
  useEffect(() => {
    if (!ctx) return;
    setDisplayedCards((previous) => [
      ...ctx.interactions,
      ...previous
        .filter((old) => !ctx.interactions.some((next) => next.id === old.id))
        .slice(0, 30)
        .map((old) => ({
          ...old,
          fingerprint: "0".repeat(64),
          supported: false,
          status: "unavailable",
          reason:
            "이 요청은 대기 목록에서 사라졌습니다. 다른 곳에서 처리되었을 수 있습니다. 보존한 입력을 확인해 주세요.",
        })),
    ]);
    setDisplayedApprovals((previous) => [
      ...ctx.approvals,
      ...previous
        .filter((old) => !ctx.approvals.some((next) => next.id === old.id))
        .slice(0, 30)
        .map((old) => ({
          ...old,
          fingerprint: "0".repeat(64),
          supported: false,
          status: "unavailable",
          reason: "이미 처리되었거나 대기 목록에서 사라진 승인입니다.",
        })),
    ]);
  }, [ctx]);
  return (
    <View style={{ gap: 12 }}>
      <Text
        style={{ color: colors.foreground, fontSize: 17, fontWeight: "700" }}
      >
        요청 · 차단 원인 · 후속 작업
      </Text>
      {query.error && (
        <>
          <Body colors={colors} error>
            {errorText(query.error)}
          </Body>
          <SmallButton
            label="작업 조건 다시 확인"
            colors={colors}
            onPress={() => void query.refetch()}
          />
        </>
      )}
      {query.isPending && (
        <Body colors={colors}>현재 작업 조건을 확인하는 중…</Body>
      )}
      {ctx && (
        <>
          {ctx.gates.map((gate, index) => (
            <Body key={index} colors={colors}>
              {gate}
            </Body>
          ))}
          {ctx.truncated && (
            <Body colors={colors} error>
              일부 요청만 표시했습니다. 전체 판단은 Paperclip에서 확인하세요.
            </Body>
          )}
          {ctx.dependencies.map((dep) => (
            <SmallButton
              key={dep.id}
              colors={colors}
              label={`선행 작업 · ${dep.title} (${dep.status}${dep.ready ? " · 준비됨" : " · 대기"})`}
              onPress={() => onIssue(dep.id)}
            />
          ))}
          {displayedCards.map((card) => (
            <InteractionForm
              key={card.id}
              card={card}
              companyId={companyId}
              colors={colors}
            />
          ))}
          {displayedApprovals.map((approval) => (
            <ApprovalDecision
              key={approval.id}
              approval={approval}
              companyId={companyId}
              colors={colors}
            />
          ))}
          {ctx.status === "backlog" && (
            <>
              <AgentPicker
                agents={agents}
                value={agentId}
                onChange={setAgent}
                colors={colors}
              />
              <ActionButton
                action={
                  {
                    kind: "start",
                    companyId,
                    issueId,
                    agentId,
                    fingerprint: ctx.fingerprint,
                  } as Action
                }
                label="초안 실행 요청"
                warning="선택한 담당자를 지정하고 todo로 변경합니다. Paperclip이 모델 실행을 요청하며 초안의 기존 정책은 유지합니다."
                colors={colors}
                disabled={!ctx.canStart || !agentId}
              />
            </>
          )}
          {ctx.scheduledRetry && (
            <>
              <Body colors={colors}>
                예약 재시도 · {ctx.scheduledRetry.at} ·{" "}
                {ctx.scheduledRetry.status}
              </Body>
              <ActionButton
                action={
                  {
                    kind: "retryScheduled",
                    companyId,
                    issueId,
                    runId: ctx.scheduledRetry.runId,
                    fingerprint: ctx.fingerprint,
                  } as Action
                }
                label="예약 재시도 지금 요청"
                warning="표시된 예약 재시도를 앞당깁니다. 실행 조건은 서버에서 다시 확인하며 모델 호출이 이어질 수 있습니다."
                colors={colors}
                disabled={!ctx.scheduledRetry.canRetry}
              />
            </>
          )}
          {ctx.failedRun && (
            <ActionButton
              action={
                {
                  kind: "retryFailed",
                  companyId,
                  issueId,
                  runId: ctx.failedRun.runId,
                  fingerprint: ctx.fingerprint,
                } as Action
              }
              label="이 실패 실행 재시도"
              warning="표시된 실패 실행만 재시도합니다. 결과가 불명확하면 다시 요청하지 않고 상태를 확인해야 합니다."
              colors={colors}
              disabled={!ctx.failedRun.canRetry}
            />
          )}
          <Field
            colors={colors}
            value={comment}
            onChange={setComment}
            placeholder="추가 지시 — 모델 실행이 이어질 수 있습니다"
            multiline
          />
          <ActionButton
            action={
              {
                kind: "comment",
                companyId,
                issueId,
                fingerprint: ctx.fingerprint,
                body: comment,
              } as Action
            }
            colors={colors}
            label="추가 지시 보내기"
            warning="단순 메모가 아닙니다. 이 댓글은 에이전트의 모델 호출을 유발할 수 있으며 차단 원인을 자동 해제하지는 않습니다."
            disabled={!comment.trim()}
          />
        </>
      )}
    </View>
  );
}
