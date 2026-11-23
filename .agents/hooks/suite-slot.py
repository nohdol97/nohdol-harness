#!/usr/bin/env python3
"""Machine-wide slot limiter for full test suites.

Usage: suite-slot.py [--slots N] [--wait-limit SECONDS] -- <command> [args...]

Runs <command> once one of N machine-wide slots is free (default 2, env
SUITE_SLOTS). Slots are flock files under SUITE_SLOT_DIR (default
/tmp/harness-suite-slots), so a crashed holder frees its slot by itself.
The child inherits the lock descriptor: the slot stays taken until the
child and everything it left running exit, not just until this wrapper does.
Exit code: the command's own code (128+N when killed by signal N); 75 when no
slot freed within the wait limit (default 3600 s, the suite never ran, and
stderr says so); 64 on usage or environment-variable error; 71 when the slot
directory or the command cannot be used. Those three are never a suite result.
A nested call (SUITE_SLOT_HELD set by an outer wrapper) runs directly.
"""
import fcntl
import os
import subprocess
import sys
import time

EX_USAGE, EX_TEMPFAIL, EX_OSERR = 64, 75, 71


def parse(argv):
    try:
        slots = int(os.environ.get("SUITE_SLOTS", "2"))
    except ValueError:
        return None
    limit = 3600.0
    i = 0
    while i < len(argv) and argv[i] != "--":
        if argv[i] in ("--slots", "--wait-limit") and i + 1 < len(argv):
            try:
                if argv[i] == "--slots":
                    slots = int(argv[i + 1])
                else:
                    limit = float(argv[i + 1])
            except ValueError:
                return None
            i += 2
        else:
            return None
    cmd = argv[i + 1:]
    if i >= len(argv) or not cmd or slots < 1 or limit != limit:
        return None
    return slots, limit, cmd


def try_acquire(slot_dir, slots):
    for n in range(slots):
        path = os.path.join(slot_dir, f"slot-{n}.lock")
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o666)
        try:
            os.chmod(path, 0o666)
        except OSError:
            pass
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except OSError:
            os.close(fd)
    return None


def launch(cmd, fd):
    env = dict(os.environ, SUITE_SLOT_HELD="1")
    try:
        rc = subprocess.call(cmd, env=env, pass_fds=(fd,) if fd is not None else ())
    except OSError as e:
        print(f"suite-slot: cannot run {cmd[0]}: {e}", file=sys.stderr)
        return EX_OSERR
    return 128 - rc if rc < 0 else rc


def main(argv):
    parsed = parse(argv)
    if parsed is None:
        print(__doc__, file=sys.stderr)
        return EX_USAGE
    slots, limit, cmd = parsed
    try:
        poll = float(os.environ.get("SUITE_SLOT_POLL", "2"))
    except ValueError:
        print("suite-slot: SUITE_SLOT_POLL must be a number", file=sys.stderr)
        return EX_USAGE
    if os.environ.get("SUITE_SLOT_HELD"):
        return launch(cmd, None)
    slot_dir = os.environ.get("SUITE_SLOT_DIR", "/tmp/harness-suite-slots")
    start = time.monotonic()
    announced = False
    try:
        os.makedirs(slot_dir, mode=0o777, exist_ok=True)
        try:
            os.chmod(slot_dir, 0o777)
        except OSError:
            pass
        fd = try_acquire(slot_dir, slots)
    except OSError as e:
        print(f"suite-slot: cannot use slot directory {slot_dir}: {e}; command not run", file=sys.stderr)
        return EX_OSERR
    while fd is None:
        if time.monotonic() - start >= limit:
            print(f"suite-slot: no slot freed within {limit:.0f}s; command not run", file=sys.stderr)
            return EX_TEMPFAIL
        if not announced:
            print(f"suite-slot: all {slots} slots busy, waiting", file=sys.stderr)
            announced = True
        time.sleep(poll)
        try:
            fd = try_acquire(slot_dir, slots)
        except OSError as e:
            print(f"suite-slot: slot directory failed: {e}; command not run", file=sys.stderr)
            return EX_OSERR
    os.ftruncate(fd, 0)
    os.write(fd, f"pid={os.getpid()} cwd={os.getcwd()} cmd={' '.join(cmd)[:200]}\n".encode())
    if announced:
        print(f"suite-slot: slot acquired after {time.monotonic() - start:.0f}s", file=sys.stderr)
    try:
        return launch(cmd, fd)
    finally:
        os.close(fd)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
