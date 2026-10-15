import type {
  PluginClientContext,
  PluginSidebarItemProps,
} from "@getpaseo/plugin/client";
import { SidebarRow } from "@getpaseo/plugin/client/ui";
import { PaperclipPanel } from "./client/panel";

function PaperclipItem({ currentScreen, openScreen }: PluginSidebarItemProps) {
  return (
    <SidebarRow
      icon="ClipboardList"
      active={currentScreen?.screenId === "paperclip"}
      onPress={() => openScreen({ screenId: "paperclip" })}
    />
  );
}
export default function contribute(client: PluginClientContext) {
  const cleanups = [
    client.addScreen({
      id: "paperclip",
      title: "Paperclip",
      Component: PaperclipPanel,
    }),
    client.addSidebarHeaderItem({
      id: "paperclip",
      title: "Paperclip",
      Component: PaperclipItem,
    }),
    client.addCommandCenterItem({
      id: "paperclip-open",
      title: "Paperclip 패널 열기",
      icon: "ClipboardList",
      keywords: ["paperclip", "작업", "이슈"],
      context: "workspace",
      onSelect: (context) => context.openPanel("paperclip"),
    }),
    client.addWorkspacePanel({
      id: "paperclip",
      title: "Paperclip",
      icon: "ClipboardList",
      context: "workspace",
      locations: ["workspace", "explorer"],
      Component: PaperclipPanel,
    }),
  ];
  return () => cleanups.forEach((cleanup) => cleanup());
}
