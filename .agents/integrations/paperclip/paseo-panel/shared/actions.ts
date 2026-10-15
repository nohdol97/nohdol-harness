import { defineRpc } from "@getpaseo/plugin";
import { z } from "zod";
import { id, detailInput } from "./contracts";
const text = z.string();
const fingerprint = text.regex(/^[a-f0-9]{64}$/);
const base = { companyId: id, operationId: id, confirmed: z.literal(true) };
const issue = { ...base, issueId: id, fingerprint };
const interaction = { ...issue, interactionId: id };
export const actionInput = z.discriminatedUnion("kind", [
  z.strictObject({
    ...base,
    kind: z.literal("submit"),
    projectId: id,
    agentId: id,
    title: text.trim().min(1).max(200),
    description: text.max(20000),
  }),
  z.strictObject({ ...issue, kind: z.literal("start"), agentId: id }),
  z.strictObject({
    ...base,
    kind: z.literal("resume"),
    agentId: id,
    fingerprint,
  }),
  z.strictObject({
    ...interaction,
    kind: z.literal("answer"),
    answers: z
      .array(
        z.strictObject({
          questionId: text.min(1).max(200),
          optionIds: z.array(text.min(1).max(200)).max(100),
          otherText: text.max(100000).optional(),
        }),
      )
      .max(20),
  }),
  z.strictObject({
    ...interaction,
    kind: z.literal("accept"),
    selectedOptionIds: z.array(text.min(1).max(200)).max(100),
  }),
  z.strictObject({
    ...interaction,
    kind: z.literal("reject"),
    reason: text.trim().max(4000),
  }),
  z.strictObject({
    ...base,
    kind: z.enum(["approve", "rejectApproval"]),
    approvalId: id,
    fingerprint,
    note: text.max(4000),
  }),
  z.strictObject({
    ...issue,
    kind: z.enum(["retryScheduled", "retryFailed"]),
    runId: id,
  }),
  z.strictObject({
    ...issue,
    kind: z.literal("comment"),
    body: text.trim().min(1).max(20000),
  }),
]);
const option = z.object({
  id: text,
  label: text,
  description: text,
  freeText: z.boolean(),
});
export const questionSchema = z.object({
  id: text,
  prompt: text,
  help: text,
  mode: z.enum(["single", "multi", "text"]),
  required: z.boolean(),
  custom: z.boolean(),
  options: z.array(option),
  minLength: z.number().nullable(),
  maxLength: z.number().nullable(),
  inputType: text,
  minimum: z.number().nullable(),
  maximum: z.number().nullable(),
  pattern: text.nullable(),
});
export const interactionSchema = z.object({
  id,
  issueId: id,
  kind: text,
  status: text,
  title: text,
  body: text,
  fingerprint,
  supported: z.boolean(),
  reason: text,
  effect: text,
  questions: z.array(questionSchema),
  options: z.array(option),
  minSelected: z.number(),
  maxSelected: z.number(),
  rejectRequiresReason: z.boolean(),
  document: z.object({ title: text, body: text, revision: text }).nullable(),
});
export const approvalSchema = z.object({
  id,
  type: text,
  status: text,
  title: text,
  body: text,
  fingerprint,
  supported: z.boolean(),
  reason: text,
  issueIds: z.array(id),
});
export const receiptSchema = z.object({
  status: text,
  message: text,
  issueId: id.optional(),
  outcome: text.optional(),
});
export const inboxRpc = defineRpc({
  name: "paperclip.inbox",
  input: z.strictObject({ companyId: id, cursor: text.max(2000).optional() }),
  output: z.object({
    items: z.array(
      z.object({
        id: text,
        source: text,
        title: text,
        detail: text,
        issueId: id.nullable(),
        interactionId: id.nullable(),
        approvalId: id.nullable(),
      }),
    ),
    nextCursor: text.nullable(),
    totalCount: z.number(),
    approvals: z.array(approvalSchema),
    truncated: z.boolean(),
  }),
});
export const contextRpc = defineRpc({
  name: "paperclip.context",
  input: detailInput,
  output: z.object({
    fingerprint,
    status: text,
    assigneeId: id.nullable(),
    gates: z.array(text),
    canStart: z.boolean(),
    dependencies: z.array(
      z.object({ id, title: text, status: text, ready: z.boolean() }),
    ),
    interactions: z.array(interactionSchema),
    approvals: z.array(approvalSchema),
    scheduledRetry: z
      .object({ runId: id, status: text, at: text, canRetry: z.boolean() })
      .nullable(),
    failedRun: z
      .object({ runId: id, agentId: id, status: text, canRetry: z.boolean() })
      .nullable(),
    truncated: z.boolean(),
  }),
});
export const approvalRpc = defineRpc({
  name: "paperclip.approval",
  input: z.strictObject({ companyId: id, approvalId: id }),
  output: approvalSchema,
});
export const agentActionRpc = defineRpc({
  name: "paperclip.agent-action",
  input: z.strictObject({ companyId: id, agentId: id }),
  output: z.object({ id, name: text, status: text, fingerprint }),
});
export const actionRpc = defineRpc({
  name: "paperclip.action",
  input: actionInput,
  output: receiptSchema,
});
export type Action = z.infer<typeof actionInput>;
export type Receipt = z.infer<typeof receiptSchema>;
export type Interaction = z.infer<typeof interactionSchema>;
export type Question = z.infer<typeof questionSchema>;
export type Approval = z.infer<typeof approvalSchema>;
