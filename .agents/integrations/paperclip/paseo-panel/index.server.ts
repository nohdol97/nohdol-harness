import type { PluginServerContext } from "@getpaseo/plugin/server";
import {
  companiesRpc,
  boardRpc,
  detailRpc,
  draftRpc,
  pauseRpc,
} from "./shared/contracts";
import { createService } from "./server/paperclip";

export default function contribute(server: PluginServerContext) {
  const service = createService();
  server.handle(companiesRpc, service.companies);
  server.handle(boardRpc, service.board);
  server.handle(detailRpc, service.detail);
  server.handle(draftRpc, service.draft);
  server.handle(pauseRpc, service.pause);
  return () => {};
}
