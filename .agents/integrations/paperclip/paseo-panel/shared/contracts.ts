import { defineRpc } from "@getpaseo/plugin";
import { z } from "zod";

export const id = z.string().uuid();
const text = z.string();
const nullable = text.nullable();
export const companyInput = z.strictObject({ companyId: id });
export const detailInput = z.strictObject({ companyId: id, issueId: id });
export const draftInput = z.strictObject({
  operationId: id.optional(),
  companyId: id,
  projectId: id,
  title: text.trim().min(1).max(200),
  description: text.max(20000),
});
export const pauseInput = z.strictObject({
  companyId: id,
  agentId: id,
  confirmed: z.literal(true),
});
export const companySchema = z.object({ id, name: text });
export const projectSchema = z.object({ id, name: text, status: text });
export const issueSchema = z.object({
  id,
  identifier: text,
  title: text,
  description: nullable,
  status: text,
  priority: text,
  projectId: id.nullable(),
  assigneeAgentId: id.nullable(),
  updatedAt: nullable,
});
export const agentSchema = z.object({
  id,
  name: text,
  role: text,
  status: text,
});
export const runSchema = z.object({
  id,
  agentId: id.nullable(),
  status: text,
  createdAt: nullable,
  finishedAt: nullable,
});
export const commentSchema = z.object({
  id,
  body: text,
  authorAgentId: id.nullable(),
  authorType: text,
  createdAt: nullable,
});
export const companiesRpc = defineRpc({
  name: "paperclip.companies",
  input: z.strictObject({}),
  output: z.array(companySchema),
});
export const boardRpc = defineRpc({
  name: "paperclip.board",
  input: companyInput,
  output: z.object({
    projects: z.array(projectSchema),
    issues: z.array(issueSchema),
    agents: z.array(agentSchema),
    runs: z.array(runSchema),
  }),
});
export const detailRpc = defineRpc({
  name: "paperclip.detail",
  input: detailInput,
  output: z.object({ issue: issueSchema, comments: z.array(commentSchema) }),
});
export const draftRpc = defineRpc({
  name: "paperclip.draft",
  input: draftInput,
  output: issueSchema,
});
export const pauseRpc = defineRpc({
  name: "paperclip.pause",
  input: pauseInput,
  output: agentSchema,
});
export type Company = z.infer<typeof companySchema>;
export type Board = z.infer<typeof boardRpc.output>;
export type Detail = z.infer<typeof detailRpc.output>;
export type Agent = z.infer<typeof agentSchema>;
