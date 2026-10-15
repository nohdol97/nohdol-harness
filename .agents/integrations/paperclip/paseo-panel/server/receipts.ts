import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile, rename, unlink } from "node:fs/promises";
import { join } from "node:path";
import { homedir } from "node:os";
import type { Receipt } from "../shared/actions";
export const hash = (value: unknown) =>
  createHash("sha256").update(JSON.stringify(value)).digest("hex");
type Entry = { fingerprint: string; result?: Receipt };
export interface Ledger {
  get(key: string): Promise<Entry | null>;
  claim(key: string, target: string, fingerprint: string): Promise<void>;
  finish(
    key: string,
    target: string,
    fingerprint: string,
    result: Receipt,
  ): Promise<void>;
}
export function memoryLedger(): Ledger {
  const entries = new Map<string, Entry>(),
    targets = new Set<string>();
  return {
    async get(key) {
      return entries.get(key) ?? null;
    },
    async claim(key, target, fingerprint) {
      if (entries.has(key) || targets.has(target))
        throw Error(
          "이전 요청 결과가 불명확하거나 처리 중입니다. 상태를 확인한 뒤 운영자가 접수 기록을 확인해야 합니다.",
        );
      entries.set(key, { fingerprint });
      targets.add(target);
    },
    async finish(key, target, fingerprint, result) {
      entries.set(key, { fingerprint, result });
      targets.delete(target);
    },
  };
}
export function fileLedger(
  directory = join(
    homedir(),
    ".paseo",
    "plugin-state",
    "nohdol-paperclip-panel",
  ),
): Ledger {
  const path = (key: string) => join(directory, hash(key) + ".json");
  return {
    async get(key) {
      try {
        return JSON.parse(
          await readFile(path("operation:" + key), "utf8"),
        ) as Entry;
      } catch (error) {
        if ((error as NodeJS.ErrnoException).code === "ENOENT") return null;
        throw Error("요청 접수 기록을 읽을 수 없습니다.");
      }
    },
    async claim(key, target, fingerprint) {
      await mkdir(directory, { recursive: true, mode: 0o700 });
      try {
        await writeFile(
          path("target:" + target),
          JSON.stringify({ operation: hash(key), fingerprint }),
          { flag: "wx", mode: 0o600 },
        );
      } catch {
        throw Error("같은 대상의 요청이 처리 중이거나 결과 확인이 필요합니다.");
      }
      try {
        await writeFile(
          path("operation:" + key),
          JSON.stringify({ fingerprint }),
          { flag: "wx", mode: 0o600 },
        );
      } catch {
        await unlink(path("target:" + target));
        throw Error("이미 접수된 요청입니다. 결과를 확인해 주세요.");
      }
    },
    async finish(key, target, fingerprint, result) {
      const temp = path("operation:" + key) + ".tmp";
      await writeFile(temp, JSON.stringify({ fingerprint, result }), {
        mode: 0o600,
      });
      await rename(temp, path("operation:" + key));
      await unlink(path("target:" + target));
    },
  };
}
