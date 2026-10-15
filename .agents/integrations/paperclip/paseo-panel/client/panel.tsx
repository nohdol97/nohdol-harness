import { useRef, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
  useWindowDimensions,
} from "react-native";
import type { PluginHostProps } from "@getpaseo/plugin/client";
import { useRpc } from "@getpaseo/plugin/client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  boardRpc,
  companiesRpc,
  detailRpc,
  draftRpc,
  pauseRpc,
  type Agent,
} from "../shared/contracts";

type Colors = PluginHostProps["theme"]["colors"];
const labels: Record<string, string> = {
  backlog: "초안",
  todo: "할 일",
  in_progress: "진행 중",
  in_review: "검토 중",
  done: "완료",
  blocked: "막힘",
  cancelled: "취소",
  paused: "일시 정지",
  running: "실행 중",
  idle: "대기",
  active: "활성",
  error: "오류",
  pending_approval: "승인 대기",
  terminated: "종료",
  succeeded: "성공",
  failed: "실패",
  queued: "대기열",
  timed_out: "시간 초과",
  critical: "긴급",
  high: "높음",
  medium: "보통",
  low: "낮음",
};
function when(value: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleString("ko-KR", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
}
function errorMessage(error: unknown) {
  return error instanceof Error
    ? error.message.slice(0, 300)
    : "요청을 완료할 수 없습니다.";
}
function Button({
  label,
  onPress,
  colors,
  disabled,
  active,
  danger,
}: {
  label: string;
  onPress(): void;
  colors: Colors;
  disabled?: boolean;
  active?: boolean;
  danger?: boolean;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled, selected: active }}
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => ({
        minHeight: 44,
        paddingHorizontal: 14,
        paddingVertical: 11,
        borderRadius: 10,
        borderWidth: 1,
        borderColor: danger
          ? colors.statusDanger
          : active
            ? colors.accent
            : colors.border,
        backgroundColor: active ? colors.accent : colors.surface1,
        opacity: disabled ? 0.45 : pressed ? 0.7 : 1,
        justifyContent: "center",
      })}
    >
      <Text
        style={{
          color: active
            ? colors.accentForeground
            : danger
              ? colors.statusDanger
              : colors.foreground,
          fontSize: 13,
          fontWeight: "600",
        }}
      >
        {label}
      </Text>
    </Pressable>
  );
}
function Note({
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
      accessibilityRole={error ? "alert" : undefined}
      style={{
        color: error ? colors.statusDanger : colors.foregroundMuted,
        fontSize: 13,
        lineHeight: 20,
      }}
    >
      {children}
    </Text>
  );
}
function Badge({ status, colors }: { status: string; colors: Colors }) {
  return (
    <Text
      style={{
        color: ["error", "failed", "blocked"].includes(status)
          ? colors.statusDanger
          : ["running", "in_progress", "in_review"].includes(status)
            ? colors.accent
            : colors.foregroundMuted,
        fontSize: 12,
        fontWeight: "600",
      }}
    >
      {labels[status] ?? status ?? "—"}
    </Text>
  );
}
function Empty({ text, colors }: { text: string; colors: Colors }) {
  return (
    <View
      style={{
        padding: 24,
        alignItems: "center",
        borderWidth: 1,
        borderStyle: "dashed",
        borderColor: colors.border,
        borderRadius: 14,
      }}
    >
      <Note colors={colors}>{text}</Note>
    </View>
  );
}

export function PaperclipPanel({ theme, host, layout }: PluginHostProps) {
  const colors = theme.colors;
  const loadCompanies = useRpc(companiesRpc);
  const companies = useQuery({
    queryKey: ["paperclip", host.id, "companies"],
    queryFn: () => loadCompanies({}),
    retry: false,
  });
  const [chosenCompany, setCompany] = useState("");
  const companyId = companies.data?.some((c) => c.id === chosenCompany)
    ? chosenCompany
    : companies.data?.[0]?.id;
  const { width } = useWindowDimensions();
  const compact = layout.compact || width < 850;
  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.surface0 }}
      contentContainerStyle={{
        padding: compact ? 16 : 26,
        gap: 20,
        maxWidth: 1400,
        width: "100%",
        alignSelf: "center",
        paddingBottom: 48,
      }}
    >
      <View style={{ gap: 6 }}>
        <Text
          style={{
            color: colors.accent,
            fontSize: 11,
            fontWeight: "700",
            letterSpacing: 2,
          }}
        >
          PAPERCLIP · LOCAL
        </Text>
        <Text
          accessibilityRole="header"
          style={{ color: colors.foreground, fontSize: 28, fontWeight: "700" }}
        >
          작업을 한눈에
        </Text>
        <Note colors={colors}>
          프로젝트와 검토 흐름을 확인하세요. 화면 조회는 모델을 호출하지
          않습니다.
        </Note>
      </View>
      {companies.isPending && (
        <ActivityIndicator
          color={colors.accent}
          accessibilityLabel="회사 불러오는 중"
        />
      )}
      {companies.error && (
        <View style={{ gap: 8 }}>
          <Note colors={colors} error>
            {errorMessage(companies.error)}
          </Note>
          <Button
            colors={colors}
            label="연결 다시 시도"
            onPress={() => void companies.refetch()}
            disabled={companies.isFetching}
          />
        </View>
      )}
      {companies.data?.length === 0 && (
        <Empty
          colors={colors}
          text="등록된 회사가 없습니다. Paperclip에서 회사를 먼저 만들어 주세요."
        />
      )}
      {!!companies.data?.length && (
        <View style={{ gap: 8 }}>
          <Text style={{ color: colors.foregroundMuted, fontSize: 12 }}>
            회사
          </Text>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
            {companies.data.map((company) => (
              <Button
                key={company.id}
                label={company.name}
                colors={colors}
                active={company.id === companyId}
                onPress={() => setCompany(company.id)}
              />
            ))}
          </View>
        </View>
      )}
      {companyId && (
        <CompanyBoard
          key={host.id + companyId}
          companyId={companyId}
          hostId={host.id}
          colors={colors}
          compact={compact}
        />
      )}
      <View
        style={{
          borderTopWidth: 1,
          borderColor: colors.border,
          paddingTop: 14,
        }}
      >
        <Note colors={colors}>
          연결된 컴퓨터의 Paperclip · 수동 새로고침 · 이슈 최대 100개 / 실행
          30개
        </Note>
      </View>
    </ScrollView>
  );
}

function CompanyBoard({
  companyId,
  hostId,
  colors,
  compact,
}: {
  companyId: string;
  hostId: string;
  colors: Colors;
  compact: boolean;
}) {
  const loadBoard = useRpc(boardRpc);
  const loadDetail = useRpc(detailRpc);
  const createDraft = useRpc(draftRpc);
  const pauseAgent = useRpc(pauseRpc);
  const queryClient = useQueryClient();
  const boardKey = ["paperclip", hostId, companyId, "board"];
  const board = useQuery({
    queryKey: boardKey,
    queryFn: () => loadBoard({ companyId }),
    retry: false,
  });
  const [projectId, setProject] = useState("");
  const [tab, setTab] = useState<"issues" | "agents" | "runs">("issues");
  const [issueId, setIssue] = useState("");
  const [draftOpen, setDraftOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [notice, setNotice] = useState("");
  const [confirmAgent, setConfirmAgent] = useState<Agent | null>(null);
  const mutationLock = useRef(false);
  const detail = useQuery({
    queryKey: ["paperclip", hostId, companyId, "detail", issueId],
    queryFn: () => loadDetail({ companyId, issueId }),
    enabled: !!issueId,
    retry: false,
  });
  const draft = useMutation({ mutationFn: createDraft, retry: false });
  const pause = useMutation({ mutationFn: pauseAgent, retry: false });
  const busy = draft.isPending || pause.isPending;
  const refresh = () => {
    void queryClient.invalidateQueries({
      queryKey: ["paperclip", hostId, companyId],
    });
  };
  async function submitDraft() {
    if (mutationLock.current || !projectId || !title.trim()) return;
    mutationLock.current = true;
    setNotice("");
    try {
      const result = await draft.mutateAsync({
        companyId,
        projectId,
        title: title.trim(),
        description,
      });
      setTitle("");
      setDescription("");
      setDraftOpen(false);
      setIssue(result.id);
      setTab("issues");
      setNotice(
        "미배정 초안을 등록했습니다. 실행이나 배정은 시작하지 않았습니다.",
      );
      refresh();
    } catch {
      /* Preserve the draft. The UI renders the bounded RPC error. */
    } finally {
      mutationLock.current = false;
    }
  }
  async function confirmPause() {
    if (mutationLock.current || !confirmAgent) return;
    mutationLock.current = true;
    setNotice("");
    try {
      await pause.mutateAsync({
        companyId,
        agentId: confirmAgent.id,
        confirmed: true,
      });
      setNotice(`${confirmAgent.name} 에이전트를 일시 정지했습니다.`);
      setConfirmAgent(null);
      refresh();
    } catch {
      /* Keep the confirmation available with the error. */
    } finally {
      mutationLock.current = false;
    }
  }
  const card = {
    backgroundColor: colors.surface1,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 14,
    padding: 16,
    gap: 12,
  } as const;
  const input = {
    color: colors.foreground,
    backgroundColor: colors.surface0,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    fontSize: 14,
    minHeight: 46,
  } as const;
  const data = board.data;
  const issues =
    data?.issues.filter(
      (issue) => !projectId || issue.projectId === projectId,
    ) ?? [];
  return (
    <View style={{ gap: 18 }}>
      <View
        style={{
          flexDirection: "row",
          flexWrap: "wrap",
          gap: 8,
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Note colors={colors}>
          {board.dataUpdatedAt
            ? `최근 확인 ${when(new Date(board.dataUpdatedAt).toISOString())}`
            : "Paperclip에 연결하는 중"}
        </Note>
        <Button
          colors={colors}
          label={board.isFetching ? "불러오는 중…" : "새로고침"}
          onPress={refresh}
          disabled={board.isFetching || busy}
        />
      </View>
      {board.isPending && (
        <ActivityIndicator
          color={colors.accent}
          accessibilityLabel="작업 목록 불러오는 중"
        />
      )}
      {board.error && (
        <Note error colors={colors}>
          {errorMessage(board.error)}
          {data ? "\n아래 내용은 마지막으로 조회한 데이터입니다." : ""}
        </Note>
      )}
      {notice ? (
        <View style={card}>
          <Text
            accessibilityRole="alert"
            style={{ color: colors.statusSuccess, lineHeight: 21 }}
          >
            {notice}
          </Text>
        </View>
      ) : null}
      {data && (
        <>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 }}>
            {[
              [
                "진행 중",
                data.issues.filter((i) => i.status === "in_progress").length,
              ],
              [
                "검토 대기",
                data.issues.filter((i) => i.status === "in_review").length,
              ],
              [
                "정지된 에이전트",
                data.agents.filter((a) => a.status === "paused").length,
              ],
            ].map(([label, count]) => (
              <View
                key={label}
                style={{
                  ...card,
                  flexGrow: 1,
                  minWidth: compact ? 100 : 180,
                  gap: 6,
                }}
              >
                <Text style={{ color: colors.foregroundMuted, fontSize: 12 }}>
                  {label}
                </Text>
                <Text
                  style={{
                    color: colors.foreground,
                    fontSize: 25,
                    fontWeight: "700",
                  }}
                >
                  {count}
                </Text>
              </View>
            ))}
          </View>
          <View style={{ gap: 8 }}>
            <Text style={{ color: colors.foregroundMuted, fontSize: 12 }}>
              프로젝트 · 이슈 목록과 초안 등록에 적용
            </Text>
            <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
              <Button
                label="전체"
                colors={colors}
                active={!projectId}
                disabled={busy}
                onPress={() => {
                  setProject("");
                  setIssue("");
                }}
              />
              {data.projects.map((project) => (
                <Button
                  key={project.id}
                  label={project.name}
                  colors={colors}
                  active={project.id === projectId}
                  disabled={busy}
                  onPress={() => {
                    setProject(project.id);
                    setIssue("");
                  }}
                />
              ))}
            </View>
          </View>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
            {(["issues", "agents", "runs"] as const).map((value) => (
              <Button
                key={value}
                colors={colors}
                active={tab === value}
                label={
                  value === "issues"
                    ? `이슈 ${issues.length}`
                    : value === "agents"
                      ? `에이전트 ${data.agents.length}`
                      : "최근 실행"
                }
                onPress={() => setTab(value)}
              />
            ))}
            <Button
              colors={colors}
              label={draftOpen ? "초안 닫기" : "+ 새 초안"}
              disabled={busy}
              onPress={() => {
                setDraftOpen(!draftOpen);
                draft.reset();
              }}
            />
          </View>
          {draftOpen && (
            <View style={card}>
              <Text
                accessibilityRole="header"
                style={{
                  color: colors.foreground,
                  fontSize: 17,
                  fontWeight: "700",
                }}
              >
                새 작업 초안
              </Text>
              <Note colors={colors}>
                선택한 프로젝트에 미배정 backlog로 저장합니다. 자동 실행하지
                않습니다.
              </Note>
              {!projectId && (
                <Note colors={colors} error>
                  위에서 프로젝트를 하나 선택해 주세요.
                </Note>
              )}
              <TextInput
                accessibilityLabel="초안 제목"
                placeholder="어떤 작업이 필요한가요?"
                placeholderTextColor={colors.foregroundMuted}
                value={title}
                onChangeText={setTitle}
                maxLength={200}
                editable={!busy}
                style={input}
              />
              <TextInput
                accessibilityLabel="초안 설명"
                placeholder="목표, 구현 범위, 검토 기준을 적어 주세요."
                placeholderTextColor={colors.foregroundMuted}
                value={description}
                onChangeText={setDescription}
                maxLength={20000}
                multiline
                editable={!busy}
                textAlignVertical="top"
                style={{ ...input, minHeight: 140 }}
              />
              <Note colors={colors}>
                {title.length}/200 · 설명 {description.length.toLocaleString()}
                /20,000
              </Note>
              {draft.error && (
                <Note colors={colors} error>
                  {errorMessage(draft.error)}
                  {"\n"}응답이 끊겼다면 목록에서 등록 여부를 먼저 확인해 주세요.
                  입력은 보존됩니다.
                </Note>
              )}
              <Button
                colors={colors}
                active
                label={draft.isPending ? "등록 중…" : "초안 등록"}
                disabled={busy || !projectId || !title.trim()}
                onPress={() => void submitDraft()}
              />
            </View>
          )}
          {tab === "issues" && (
            <View
              style={{
                flexDirection: compact ? "column" : "row",
                alignItems: "stretch",
                gap: 16,
              }}
            >
              <View
                style={{
                  flex: 1,
                  minWidth: 0,
                  gap: 8,
                  display: compact && issueId ? "none" : "flex",
                }}
              >
                {issues.length === 0 && (
                  <Empty
                    colors={colors}
                    text="이 프로젝트에는 표시할 이슈가 없습니다."
                  />
                )}
                {issues.map((issue) => (
                  <Pressable
                    key={issue.id}
                    accessibilityRole="button"
                    accessibilityLabel={`${issue.identifier} ${issue.title}`}
                    accessibilityState={{ selected: issue.id === issueId }}
                    onPress={() => setIssue(issue.id)}
                    style={({ pressed }) => ({
                      ...card,
                      borderColor:
                        issue.id === issueId ? colors.accent : colors.border,
                      opacity: pressed ? 0.75 : 1,
                    })}
                  >
                    <View
                      style={{
                        flexDirection: "row",
                        justifyContent: "space-between",
                        gap: 8,
                      }}
                    >
                      <Text
                        style={{ color: colors.foregroundMuted, fontSize: 12 }}
                      >
                        {issue.identifier || "작업"}
                      </Text>
                      <Badge status={issue.status} colors={colors} />
                    </View>
                    <Text
                      style={{
                        color: colors.foreground,
                        fontSize: 15,
                        fontWeight: "600",
                        lineHeight: 23,
                      }}
                    >
                      {issue.title}
                    </Text>
                    <Note colors={colors}>
                      {data.projects.find((p) => p.id === issue.projectId)
                        ?.name ?? "프로젝트 없음"}{" "}
                      · {labels[issue.priority] ?? issue.priority}
                    </Note>
                  </Pressable>
                ))}
              </View>
              <View
                style={{
                  flex: 1,
                  minWidth: 0,
                  gap: 12,
                  display: compact && !issueId ? "none" : "flex",
                }}
              >
                {!issueId ? (
                  <Empty
                    colors={colors}
                    text="이슈를 선택하면 설명과 최근 댓글을 볼 수 있습니다."
                  />
                ) : (
                  <View style={card}>
                    <View
                      style={{
                        flexDirection: "row",
                        justifyContent: "space-between",
                        gap: 8,
                      }}
                    >
                      <Text
                        accessibilityRole="header"
                        style={{
                          color: colors.foreground,
                          fontSize: 17,
                          fontWeight: "700",
                        }}
                      >
                        이슈 상세
                      </Text>
                      <Button
                        colors={colors}
                        label={compact ? "목록으로" : "닫기"}
                        onPress={() => setIssue("")}
                      />
                    </View>
                    {detail.isPending && (
                      <ActivityIndicator color={colors.accent} />
                    )}
                    {detail.error && (
                      <View style={{ gap: 8 }}>
                        <Note error colors={colors}>
                          {errorMessage(detail.error)}
                        </Note>
                        <Button
                          label="상세 다시 시도"
                          colors={colors}
                          disabled={detail.isFetching}
                          onPress={() => void detail.refetch()}
                        />
                      </View>
                    )}
                    {detail.data && (
                      <>
                        <Badge
                          colors={colors}
                          status={detail.data.issue.status}
                        />
                        <Text
                          style={{
                            color: colors.foreground,
                            fontSize: 19,
                            lineHeight: 27,
                            fontWeight: "700",
                          }}
                        >
                          {detail.data.issue.title}
                        </Text>
                        <Text
                          selectable
                          style={{
                            color: colors.foreground,
                            fontSize: 14,
                            lineHeight: 23,
                          }}
                        >
                          {detail.data.issue.description ||
                            "작성된 설명이 없습니다."}
                        </Text>
                        <View
                          style={{
                            height: 1,
                            backgroundColor: colors.border,
                            marginVertical: 6,
                          }}
                        />
                        <Text
                          style={{
                            color: colors.foreground,
                            fontSize: 15,
                            fontWeight: "700",
                          }}
                        >
                          최근 댓글 · {detail.data.comments.length}
                        </Text>
                        {!detail.data.comments.length && (
                          <Note colors={colors}>아직 댓글이 없습니다.</Note>
                        )}
                        {detail.data.comments.map((comment) => (
                          <View
                            key={comment.id}
                            style={{
                              backgroundColor: colors.surface0,
                              padding: 12,
                              borderRadius: 10,
                              gap: 8,
                            }}
                          >
                            <Note colors={colors}>
                              {data.agents.find(
                                (a) => a.id === comment.authorAgentId,
                              )?.name ??
                                (comment.authorType === "agent"
                                  ? "에이전트"
                                  : "사용자")}{" "}
                              · {when(comment.createdAt)}
                            </Note>
                            <Text
                              selectable
                              style={{
                                color: colors.foreground,
                                fontSize: 14,
                                lineHeight: 22,
                              }}
                            >
                              {comment.body}
                            </Text>
                          </View>
                        ))}
                      </>
                    )}
                  </View>
                )}
              </View>
            </View>
          )}
          {tab === "agents" && (
            <View style={{ gap: 10 }}>
              <Note colors={colors}>
                회사 전체 에이전트입니다. 일시 정지는 진행 중인 실행도
                취소합니다.
              </Note>
              {data.agents.length === 0 && (
                <Empty colors={colors} text="등록된 에이전트가 없습니다." />
              )}
              {data.agents.map((agent) => (
                <View key={agent.id} style={card}>
                  <View
                    style={{
                      flexDirection: "row",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: 12,
                    }}
                  >
                    <View style={{ flex: 1, gap: 5 }}>
                      <Text
                        style={{
                          color: colors.foreground,
                          fontSize: 16,
                          fontWeight: "600",
                        }}
                      >
                        {agent.name}
                      </Text>
                      <Note colors={colors}>{agent.role || "역할 미지정"}</Note>
                      <Badge status={agent.status} colors={colors} />
                    </View>
                    <Button
                      colors={colors}
                      label="일시 정지"
                      disabled={
                        busy || ["paused", "terminated"].includes(agent.status)
                      }
                      onPress={() => {
                        setConfirmAgent(agent);
                        pause.reset();
                      }}
                    />
                  </View>
                  {confirmAgent?.id === agent.id && (
                    <View
                      style={{
                        borderTopWidth: 1,
                        borderColor: colors.border,
                        paddingTop: 12,
                        gap: 10,
                      }}
                    >
                      <Text
                        style={{ color: colors.foreground, lineHeight: 22 }}
                      >
                        {agent.name}을(를) 일시 정지할까요? 진행 중인 실행이
                        취소되며, 이 패널에서는 다시 시작할 수 없습니다.
                      </Text>
                      {pause.error && (
                        <Note colors={colors} error>
                          {errorMessage(pause.error)}
                        </Note>
                      )}
                      <View
                        style={{
                          flexDirection: "row",
                          flexWrap: "wrap",
                          gap: 8,
                        }}
                      >
                        <Button
                          colors={colors}
                          label={
                            pause.isPending ? "정지 중…" : "실행 취소 및 정지"
                          }
                          danger
                          disabled={busy}
                          onPress={() => void confirmPause()}
                        />
                        <Button
                          colors={colors}
                          label="돌아가기"
                          disabled={busy}
                          onPress={() => setConfirmAgent(null)}
                        />
                      </View>
                    </View>
                  )}
                </View>
              ))}
            </View>
          )}
          {tab === "runs" && (
            <View style={{ gap: 10 }}>
              <Note colors={colors}>
                회사 전체의 최근 실행 상태입니다. 원시 로그와 실행 설정은
                가져오지 않습니다.
              </Note>
              {data.runs.length === 0 && (
                <Empty colors={colors} text="아직 실행 기록이 없습니다." />
              )}
              {data.runs.map((run) => (
                <View key={run.id} style={card}>
                  <View
                    style={{
                      flexDirection: "row",
                      justifyContent: "space-between",
                      gap: 12,
                    }}
                  >
                    <Text
                      style={{
                        color: colors.foreground,
                        fontSize: 15,
                        fontWeight: "600",
                      }}
                    >
                      {data.agents.find((a) => a.id === run.agentId)?.name ??
                        "에이전트"}
                    </Text>
                    <Badge colors={colors} status={run.status} />
                  </View>
                  <Note colors={colors}>
                    시작 {when(run.createdAt)}
                    {run.finishedAt ? ` · 종료 ${when(run.finishedAt)}` : ""}
                  </Note>
                </View>
              ))}
            </View>
          )}
        </>
      )}
    </View>
  );
}
