#!/usr/bin/env python3
"""Pre-check diagrams in a document and say when one has outgrown Mermaid.

Mermaid keeps its source inline, so a document can carry a diagram with no
toolchain at all. That only holds while the diagram stays small: past a
certain size Mermaid's layout stops being readable and the diagram belongs in
D2, rendered to SVG and embedded. Deciding that by feel produces tangled
diagrams nobody redraws, so the threshold is counted here instead.

This is a pre-check, not a renderer. Mermaid's own parser is JavaScript and
this repository keeps its scripts dependency-free, so what is checked is the
set of mistakes that are decidable from the text: an unknown diagram type,
unbalanced delimiters, labels Mermaid cannot parse or cannot render as
markdown, and embedded assets that do not exist. A file that passes may still
fail to render.

Usage: check.py [--max-nodes N] PATH [PATH ...]
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
from urllib.parse import unquote


FENCE_OPEN = re.compile(r"^\s*(`{3,}|~{3,})\s*([A-Za-z0-9_-]*)\s*$")
# A code span closes at the next backtick run of the same length, wherever that
# run sits, so it can carry a line ending inside it. A blank line ends the
# block and no span reaches past one.
INLINE_CODE = re.compile(r"(`+)(?:(?!\n[ \t]*\n).)*?\1", re.DOTALL)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
EMBED = re.compile(r"!\[\[([^\[\]\n|]+)(?:\|[^\[\]\n]*)?\]\]")
# This harness renders into repository Markdown, issues, and PR bodies rather
# than Obsidian, so `![alt](path)` is the embed form that actually appears here;
# the wikilink form above is kept because a ported note may still carry it.
MD_EMBED = re.compile(r"!\[[^\]\n]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"\n]*\")?\s*\)")
# A target whose existence is not decidable from disk. Mostly a scheme
# (`https:`), a protocol-relative `//host/…`, or a fragment. A bare Windows
# drive letter (`C:`) also matches — a misclassification, but the direction is
# skip, and root AGENTS.md §11 scopes this harness to macOS/Linux.
REMOTE_TARGET = re.compile(r"^(?:[A-Za-z][A-Za-z0-9+.-]*:|//|#)")
IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")

# Known Mermaid diagram types. An unknown type renders as an error block,
# which is easy to miss when writing many diagrams. This is an allowlist, so a
# type a newer Mermaid added reports as a problem — widen it rather than
# working around it.
DIAGRAM_TYPES = {
    "architecture-beta", "block-beta", "c4component", "c4container",
    "c4context", "c4deployment", "c4dynamic", "classdiagram", "erdiagram",
    "flowchart", "flowchart-elk", "gantt", "gitgraph", "graph", "journey",
    "kanban", "mindmap", "packet-beta", "pie", "quadrantchart",
    "requirementdiagram", "sankey-beta", "sequencediagram", "statediagram",
    "statediagram-v2", "timeline", "xychart-beta", "zenuml",
}
NODE_SHAPED = {"flowchart", "flowchart-elk", "graph"}
# Words that appear where a node id would and are not nodes.
NOT_NODES = {
    "subgraph", "end", "direction", "style", "classdef", "class", "click",
    "linkstyle", "tb", "td", "bt", "rl", "lr", "href", "call", "callback",
}
# Lines that begin with one of these are declarations, not edge statements, so
# the two-words-where-one-id-belongs rule must not read them.
STATEMENT_KEYWORDS = {
    "subgraph", "end", "direction", "style", "classdef", "class", "click",
    "linkstyle", "acctitle", "accdescr", "flowchart", "graph",
}

LABEL_OPENERS = "[({"
LABEL_CLOSERS = "])}"
# A token made only of link punctuation. `o` and `x` are arrowheads (`--o`,
# `--x`) and never stand alone, so they count only beside real link characters.
LINK_TOKEN = re.compile(r"^[-=.<>~&|ox]*[-=.<>~&|][-=.<>~&|ox]*$")
# A link carrying its text between the delimiters: `A -. note .-> B`. Removing
# it as a unit keeps the note's words from looking like a node id.
INLINE_LINK_TEXT = re.compile(
    r"(?:--|==|-\.)\s+[^-=|\n]+?\s+(?:-{2,}|={2,}|\.-+)[>ox]?"
)
QUOTED = re.compile(r'"[^"\n]*"')
EDGE_LABEL = re.compile(r"\|[^|\n]*\|")
# `id[[text]]` is Mermaid's subroutine shape. It is the one shape whose source
# is character-for-character an Obsidian wikilink, so a link pasted into a
# diagram parses as a box and nothing says otherwise: the note title is drawn
# with a double border, and Obsidian resolves no link inside a code fence. The
# diagram then shows a connection the vault does not have, which no rendering
# reveals. Quoting settles which of the two was meant, and every other label in
# a flowchart is quoted anyway.
SUBROUTINE_UNQUOTED = re.compile(r"\[\[\s*(?!\")([^\]\n]+?)\s*\]\]")

DEFAULT_MAX_NODES = 15


def fences(lines: list[str]) -> list[tuple[int, str, list[str]]]:
    """Return (start line, info string, body lines) for every fenced block."""
    blocks: list[tuple[int, str, list[str]]] = []
    marker: str | None = None
    info = ""
    start = 0
    body: list[str] = []
    for number, line in enumerate(lines, start=1):
        match = FENCE_OPEN.match(line)
        if marker is None:
            if match:
                marker = match.group(1)
                info = match.group(2).lower()
                start = number
                body = []
            continue
        if match and match.group(1)[0] == marker[0] and len(match.group(1)) >= len(marker):
            blocks.append((start, info, body))
            marker = None
            continue
        body.append(line)
    if marker is not None:
        blocks.append((start, info, body))
    return blocks


def prose_lines(lines: list[str]) -> list[str]:
    """Return the note's lines with code blanked out and positions preserved.

    An embed written inside a fence or a code span is an example of the syntax,
    not a picture the note draws. Reporting it as a missing asset sends a reader
    looking for a file nobody ever meant to add.
    """
    kept: list[str] = []
    marker: str | None = None
    for line in lines:
        match = FENCE_OPEN.match(line)
        if match:
            if marker is None:
                marker = match.group(1)
            elif match.group(1)[0] == marker[0] and len(match.group(1)) >= len(marker):
                marker = None
            kept.append("")
            continue
        kept.append("" if marker is not None else line)
    # One newline is kept for every one a span consumed, so a finding still
    # points at the line the reader has to open.
    text = INLINE_CODE.sub(
        lambda match: "\n" * match.group(0).count("\n"), "\n".join(kept)
    )
    # An embed left inside an HTML comment is a removal someone kept a note of,
    # not a picture the document draws — reporting it sends a reader looking for
    # a file that was deleted on purpose. Same newline-preserving substitution.
    text = HTML_COMMENT.sub(
        lambda match: "\n" * match.group(0).count("\n"), text
    )
    return text.split("\n")


def strip_labels(text: str) -> str:
    """Remove quoted strings and bracketed label text.

    What remains is node ids, arrows, and keywords, so counting identifiers
    afterwards does not also count every word inside a label.
    """
    text = re.sub(r'"[^"\n]*"', " ", text)
    text = re.sub(r"'[^'\n]*'", " ", text)
    for opening, closing in (("[", "]"), ("(", ")"), ("{", "}")):
        pattern = re.compile(re.escape(opening) + r"[^" + re.escape(opening + closing) + r"\n]*" + re.escape(closing))
        while True:
            replaced = pattern.sub(" ", text)
            if replaced == text:
                break
            text = replaced
    return text


def count_nodes(body: list[str]) -> int:
    found: set[str] = set()
    for line in body:
        stripped = line.strip()
        if not stripped or stripped.startswith("%%"):
            continue
        first = stripped.split()[0].lower().rstrip(":")
        if first in {"style", "classdef", "click", "linkstyle", "class"}:
            continue
        if first == "subgraph":
            # A subgraph carries one container, and an unquoted title is just
            # words - `subgraph Client Layer` is not two nodes. Counting them
            # inflates the total and sends a small diagram to D2 for no reason.
            rest = strip_labels(stripped[len("subgraph"):]).split()
            if rest:
                found.add(rest[0])
            continue
        for token in IDENTIFIER.findall(strip_labels(stripped)):
            if token.lower() not in NOT_NODES:
                found.add(token)
    return len(found)


def unbalanced(body: list[str]) -> list[str]:
    text = "\n".join(body)
    text = re.sub(r'"[^"\n]*"', " ", text)
    text = re.sub(r"'[^'\n]*'", " ", text)
    problems: list[str] = []
    for opening, closing, label in (
        ("[", "]", "square bracket"),
        ("(", ")", "parenthesis"),
        ("{", "}", "brace"),
    ):
        if text.count(opening) != text.count(closing):
            problems.append(
                f"unbalanced {label}: {text.count(opening)} {opening!r} "
                f"and {text.count(closing)} {closing!r}"
            )
    if text.count('"') % 2:
        problems.append("odd number of double quotes")
    return problems


def read_label(line: str, start: int, closers: str, found: list[tuple[str, bool]]) -> int:
    """Read one label body from `start`, recording it as (text, quoted).

    Returns the index just past the closing delimiter.
    """
    index = start
    while index < len(line) and line[index] == " ":
        index += 1
    if index < len(line) and line[index] == '"':
        # A quoted label may hold anything, including a parenthesis.
        closing = line.find('"', index + 1)
        if closing < 0:
            found.append((line[index + 1:], True))
            index = len(line)
        else:
            found.append((line[index + 1:closing], True))
            index = closing + 1
    else:
        body = index
        while index < len(line) and line[index] not in closers:
            index += 1
        found.append((line[body:index], False))
    while index < len(line) and line[index] in closers:
        index += 1
    return index


def scan_labels(line: str) -> list[tuple[str, bool]]:
    """Return (text, quoted) for every node label, edge label, and bare string.

    Mermaid accepts almost anything inside a label, but only while the label is
    quoted. Unquoted, a parenthesis or a double quote ends the statement and the
    whole diagram renders as an error block instead of a picture. The
    parenthesis is balanced, so counting delimiters cannot see it: the label
    text itself has to be read. Quoting fixes the parser, not the renderer, so
    quoted labels are recorded too - the markdown rules below apply to both.
    """
    found: list[tuple[str, bool]] = []
    index = 0
    while index < len(line):
        character = line[index]
        if character == '"':
            closing = line.find('"', index + 1)
            if closing < 0:
                found.append((line[index + 1:], True))
                index = len(line)
            else:
                found.append((line[index + 1:closing], True))
                index = closing + 1
        elif character == "|":
            index = read_label(line, index + 1, "|", found)
        elif character in LABEL_OPENERS:
            # Shapes stack their delimiters: [[ ]], [( )], (( )), {{ }}.
            while index < len(line) and line[index] in LABEL_OPENERS:
                index += 1
            index = read_label(line, index, LABEL_CLOSERS, found)
        else:
            index += 1
    return found


def unquoted_labels(line: str) -> list[str]:
    """Return the text of every label on the line that is written unquoted."""
    return [text for text, quoted in scan_labels(line) if not quoted]


# Mermaid renders a flowchart label as markdown, and its markdown handler
# supports only paragraph, text, strong, em, html, and escape. Anything else
# the lexer produces is replaced - in the version Obsidian bundles, by the
# literal text `Unsupported markdown: <type>`, which is what the reader sees
# instead of the label. The diagram parses, so no delimiter or label rule above
# can see it. Each pattern below was confirmed against Obsidian's own bundled
# `markdownToHTML` driven by `marked`.
#
# The rules split by what the lexer decides where. A block rule reads the front
# of a line, and a <br/> starts a new line, so each segment is judged on its own.
BLOCK_LABEL_RULES = (
    (re.compile(r"^\d{1,9}[.)](\s|$)"), "list",
     "starts with an ordered-list marker - write '①' or '1 ·' instead; "
     "'1)' is a list marker too, and the backslash escape '1\\.' is dropped "
     "by the other label renderer"),
    (re.compile(r"^[-*+](\s|$)"), "list",
     "starts with a bullet-list marker - drop it or write '·'"),
    (re.compile(r"^#{1,6}(\s|$)"), "heading",
     "starts with a heading marker - drop the '#' or move it off the front"),
    (re.compile(r"^>"), "blockquote",
     "starts with a blockquote marker - write '&gt;' or move it off the front"),
    (re.compile(r"^(?:-{3,}|\*{3,}|_{3,})$"), "hr",
     "is a horizontal rule - use a different separator"),
)
# An inline rule is not confined to one segment. The whole label goes to a
# single markdown lexer, and a backtick opened before a <br/> closes after it -
# `marked` reports one codespan spanning the break, so the reader gets
# "Unsupported markdown" for a label whose every segment looks harmless. These
# run over the whole label with the breaks flattened. Bold and italic span a
# break the same way and are left alone: strong and em are supported types, so
# they render.
INLINE_LABEL_RULES = (
    (re.compile(r"`[^`]*`"), "codespan",
     "holds a backtick pair - drop the backticks"),
    (re.compile(r"!?\[[^\]]*\]\([^)]*\)"), "link",
     "holds a markdown link - write the text and the target separately"),
)
# A markdown label breaks its lines on <br/>, not on a literal \n.
LINE_BREAK = re.compile(r"<br\s*/?>")
# Lines whose quoted strings are not rendered as a label.
NOT_LABEL_STATEMENTS = {"style", "classdef", "class", "click", "linkstyle"}


def markdown_label_problems(offset: int, line: str) -> list[str]:
    """Report label text Mermaid parses but cannot render as markdown.

    Quoting is what makes a label parse; it does nothing here, because the
    label text is handed to a markdown lexer either way. A label reading
    `1. Hardware Layer` becomes an ordered list, and the list is dropped.
    """
    problems: list[str] = []
    first = line.strip().split()[0].lower().rstrip(":;") if line.strip() else ""
    if first in NOT_LABEL_STATEMENTS:
        return problems

    texts = [text for text, _ in scan_labels(line)]
    if first == "subgraph":
        # `subgraph 1. Hardware Layer` carries its title with no delimiters, so
        # the label scanner never sees it.
        title = line.strip()[len("subgraph"):].strip()
        if title and "[" not in title and '"' not in title:
            texts.append(title)

    for text in texts:
        if "\\n" in text:
            problems.append(
                f"line {offset + 1}: label {text.strip()!r} holds a literal "
                "\\n - a markdown label renders it as two characters; "
                "use <br/> for the line break"
            )
        # An inline construct is read from the whole label, so the break has to
        # be flattened away before the rules run.
        flattened = LINE_BREAK.sub(" ", text).strip()
        for pattern, kind, advice in INLINE_LABEL_RULES:
            if pattern.search(flattened):
                problems.append(
                    f"line {offset + 1}: label {flattened!r} {advice} - "
                    f'Mermaid renders "Unsupported markdown: {kind}" '
                    "in place of the label"
                )
                break

        # The renderer that keeps HTML labels breaks a markdown block only at
        # the front of the label; the one that draws SVG text breaks it at
        # every <br/>. Checking each segment covers both.
        for segment in LINE_BREAK.split(text):
            segment = segment.strip()
            if not segment:
                continue
            for pattern, kind, advice in BLOCK_LABEL_RULES:
                if pattern.search(segment):
                    problems.append(
                        f"line {offset + 1}: label {segment!r} {advice} - "
                        f'Mermaid renders "Unsupported markdown: {kind}" '
                        "in place of the label"
                    )
                    break
    return problems


def spaced_reference(line: str) -> bool:
    """True when two words sit where one node id belongs.

    Writing `subgraph One Layer` and then `One Layer --> Two Layer` reads well
    but is not Mermaid: a subgraph title is not an id, and an id holds no space.
    """
    text = QUOTED.sub(" ", line)
    text = EDGE_LABEL.sub(" | ", text)
    text = strip_labels(text)
    text = INLINE_LINK_TEXT.sub(" --> ", text)
    after_word = False
    for token in text.split():
        if LINK_TOKEN.match(token):
            after_word = False
            continue
        # `A[x]:::cls` attaches a class to the id before it. Removing the label
        # leaves the suffix standing alone, so it is not a second id.
        if token.startswith(":::"):
            continue
        if after_word:
            return True
        after_word = True
    return False


def label_problems(body: list[str]) -> list[str]:
    """Report the flowchart mistakes that a delimiter count cannot see."""
    problems: list[str] = []
    opened = 0
    closed = 0
    for offset, line in enumerate(body):
        stripped = line.strip()
        if not stripped or stripped.startswith("%%"):
            continue
        first = stripped.split()[0].lower().rstrip(":;")
        if first == "subgraph":
            opened += 1
            title = QUOTED.sub(" ", stripped[len("subgraph"):])
            if "(" in title or ")" in title:
                problems.append(
                    f"line {offset + 1}: subgraph title holds a parenthesis "
                    'while unquoted - write subgraph ID["title (detail)"]'
                )
        elif stripped.lower() == "end":
            closed += 1

        for match in SUBROUTINE_UNQUOTED.finditer(line):
            text = match.group(1)
            problems.append(
                f"line {offset + 1}: subroutine label {text!r} is unquoted and "
                "reads as a wikilink - Mermaid draws a subroutine box here and "
                "Obsidian links nothing inside a fence, so a pasted [[note]] "
                f'connects to nothing; write ["{text}"] and link it in the '
                f'prose, or [["{text}"]] to keep the subroutine shape'
            )

        for label in unquoted_labels(line):
            if "(" in label or ")" in label:
                problems.append(
                    f"line {offset + 1}: unquoted label {label.strip()!r} holds "
                    'a parenthesis - quote it as ["...(...)..."]'
                )
            elif '"' in label:
                problems.append(
                    f"line {offset + 1}: unquoted label {label.strip()!r} holds "
                    "a double quote - quote the whole label instead"
                )

        problems.extend(markdown_label_problems(offset, line))

        if first not in STATEMENT_KEYWORDS and spaced_reference(line):
            problems.append(
                f"line {offset + 1}: {stripped!r} uses a node id containing a "
                "space - reference the id, not a title"
            )

    if opened != closed:
        problems.append(
            f"{opened} subgraph and {closed} end: every subgraph needs its own "
            "end on a line of its own"
        )
    return problems


def check_markdown(
    path: Path, max_nodes: int, problems: list[str], advice: list[str]
) -> int:
    lines = path.read_text(encoding="utf-8").splitlines()
    diagrams = 0

    for start, info, body in fences(lines):
        if info != "mermaid":
            continue
        diagrams += 1
        declaration = ""
        for line in body:
            if line.strip() and not line.strip().startswith("%%"):
                declaration = line.strip()
                break
        if not declaration:
            problems.append(f"{path}:{start}: mermaid block is empty")
            continue
        kind = declaration.split()[0].lower().rstrip(";")
        if kind not in DIAGRAM_TYPES:
            problems.append(
                f"{path}:{start}: unknown mermaid diagram type {kind!r}"
            )
            continue
        for problem in unbalanced(body):
            problems.append(f"{path}:{start}: {problem}")
        if kind in NODE_SHAPED:
            # Only the node-shaped types restrict labels this way; a
            # sequenceDiagram takes a parenthesis unquoted without complaint.
            for problem in label_problems(body):
                problems.append(f"{path}:{start}: {problem}")
            nodes = count_nodes(body[1:] if body and body[0].strip() else body)
            if nodes > max_nodes:
                advice.append(
                    f"{path}:{start}: about {nodes} nodes, over the {max_nodes} "
                    "Mermaid stays readable at - render this one with D2 and "
                    "embed the SVG"
                )

    # An embedded image that does not exist renders as a broken link, which is
    # invisible until someone opens the note.
    for number, line in enumerate(prose_lines(lines), start=1):
        for target in EMBED.findall(line) + MD_EMBED.findall(line):
            target = target.strip()
            if REMOTE_TARGET.match(target):
                continue
            if not target.lower().endswith((".svg", ".png", ".jpg", ".jpeg", ".webp")):
                continue
            if resolves(path, target):
                continue
            problems.append(f"{path}:{number}: embedded asset not found: {target}")

    return diagrams


def resolves(path: Path, target: str) -> bool:
    """Does this embed target name a file that exists?

    **False positives are the expensive direction here** — this check gates a
    document's completion, and one spurious "not found" teaches people to skip
    the checker. So every plausible reading of the target is tried, and an
    unreadable one is treated as fine rather than reported.
    """
    candidates = [target]
    # A non-ASCII filename is percent-encoded by the time it lands in a
    # document (GitHub does this on upload), while the file on disk is not.
    decoded = unquote(target)
    if decoded != target:
        candidates.append(decoded)
    for candidate in candidates:
        # A leading slash is not a filesystem path: `Path(a) / "/b"` discards
        # the left operand and resolves from the filesystem root, which is
        # wrong under every candidate rule. Read it from the repository root
        # when there is one, and skip it when there is not — an undecidable
        # target is not a finding.
        if candidate.startswith("/"):
            root = repo_root(path)
            if root is None:
                return True
            if (root / candidate.lstrip("/")).exists():
                return True
            continue
        if (path.parent / candidate).exists():
            return True
        if (path.parent / "assets" / Path(candidate).name).exists():
            return True
    return False


def repo_root(path: Path) -> Path | None:
    """Nearest ancestor holding `.git`. No subprocess — this file stays dependency-free."""
    try:
        here = path.resolve().parent
    except OSError:
        return None
    for directory in [here, *here.parents]:
        if (directory / ".git").exists():
            return directory
    return None


def check_svg(path: Path, problems: list[str]) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    if "<svg" not in text:
        problems.append(f"{path}: does not contain an <svg> element")
        return
    # A renderer that failed often still writes a file, and an empty canvas is
    # easy to embed without noticing.
    if not re.search(r"<(path|rect|circle|ellipse|line|polyline|polygon|text|g)\b", text):
        problems.append(f"{path}: contains no drawable elements")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-nodes", type=int, default=DEFAULT_MAX_NODES)
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    problems: list[str] = []
    advice: list[str] = []
    diagrams = 0
    for path in args.paths:
        if not path.is_file():
            problems.append(f"{path}: not a file")
            continue
        suffix = path.suffix.lower()
        if suffix in {".md", ".markdown"}:
            diagrams += check_markdown(path, args.max_nodes, problems, advice)
        elif suffix == ".svg":
            check_svg(path, problems)
        else:
            problems.append(f"{path}: unsupported file type {suffix or '(none)'}")

    for line in advice:
        print(f"diagram: {line}", file=sys.stderr)
    if problems:
        for problem in sorted(problems):
            print(f"diagram: {problem}", file=sys.stderr)
        return 1
    print(f"diagram: {diagrams} mermaid block(s) checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
