import type { PluginServerContext } from "@getpaseo/plugin/server";
import {
  companiesRpc,
  boardRpc,
  detailRpc,
  draftRpc,
  pauseRpc,
} from "./shared/contracts";
import { createActions } from "./server/actions";
import {
  inboxRpc,
  contextRpc,
  approvalRpc,
  agentActionRpc,
  actionRpc,
} from "./shared/actions";
import { createService } from "./server/paperclip";

export default function contribute(server: PluginServerContext) {
  const service = createService();
  server.handle(companiesRpc, service.companies);
  server.handle(boardRpc, service.board);
  server.handle(detailRpc, service.detail);
  server.handle(draftRpc, service.draft);
  server.handle(pauseRpc, service.pause);
  const actions = createActions();
  server.handle(inboxRpc, actions.inbox);
  server.handle(contextRpc, actions.context);
  server.handle(approvalRpc, actions.approval);
  server.handle(agentActionRpc, actions.agentAction);
  server.handle(actionRpc, actions.actionReply);
  return () => {};
}
