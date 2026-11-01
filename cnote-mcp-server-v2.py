"""
C-Note MCP Server
Personal knowledge vault management for the C-Note vault.

Canonical structure docs: <vault>/_system/structure.md
Tag taxonomy:              <vault>/_system/tag-taxonomy.md
Librarian protocol:        <vault>/_system/librarian-protocol.md
"""

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ConfigDict

# ── Config ─────────────────────────────────────────────────────────────────────

DEFAULT_VAULT_ROOT = Path("/Users/lupin/_Workspace/documents/notes/c-note")


def _resolve_vault_root() -> Path:
    """Find the vault root.

    Priority:
    1. CNOTE_VAULT env var
    2. ~/.config/cnote/vault_path (if exists)
    3. DEFAULT_VAULT_ROOT
    """
    env = os.environ.get("CNOTE_VAULT")
    if env:
        return Path(env).expanduser().resolve()
    cfg = Path.home() / ".config" / "cnote" / "vault_path"
    if cfg.exists():
        return Path(cfg.read_text().strip()).expanduser().resolve()
    return DEFAULT_VAULT_ROOT


VAULT_ROOT = _resolve_vault_root()
META_DIR = VAULT_ROOT / ".cnote"
INDEX_FILE = META_DIR / "index.json"
LOG_FILE = META_DIR / "activity.log"
CONFIG_FILE = META_DIR / "config.json"
VAULT_INDEX_MD = VAULT_ROOT / "_system" / "index.md"
MAX_LOG_LINES = 500

# ── Structural constants ───────────────────────────────────────────────────────

# Top-level working folders. Anything outside this set is not a valid destination.
TOP_LEVEL = {"_system", "inbox", "daily", "clients", "projects", "library", "life"}

# Folders that hold per-entity subfolders (each subfolder = one client/project)
SUBFOLDER_PARENTS = {"clients", "projects"}

# Folders that store content in flat (no sub-folders)
FLAT_FOLDERS = {"_system", "inbox", "daily", "library", "life"}

# Shape values (matches #shape/* tag taxonomy)
SHAPES = {"log", "evergreen", "index", "daily", "inbox"}

# ── App ────────────────────────────────────────────────────────────────────────

mcp = FastMCP("cnote_mcp")

# ── Vault initialization ───────────────────────────────────────────────────────


def ensure_vault():
    """Create the canonical folder structure if any pieces are missing."""
    META_DIR.mkdir(parents=True, exist_ok=True)
    (VAULT_ROOT / "_system").mkdir(parents=True, exist_ok=True)
    (VAULT_ROOT / "inbox").mkdir(parents=True, exist_ok=True)
    (VAULT_ROOT / "daily").mkdir(parents=True, exist_ok=True)
    (VAULT_ROOT / "clients").mkdir(parents=True, exist_ok=True)
    (VAULT_ROOT / "projects").mkdir(parents=True, exist_ok=True)
    (VAULT_ROOT / "library").mkdir(parents=True, exist_ok=True)
    (VAULT_ROOT / "life").mkdir(parents=True, exist_ok=True)

    if not INDEX_FILE.exists():
        INDEX_FILE.write_text(json.dumps({"notes": {}}, indent=2))
    if not LOG_FILE.exists():
        LOG_FILE.write_text("")
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(
            json.dumps(
                {
                    "vault_version": "2.0",
                    "tag_style": "inline",
                    "default_inbox_drop": True,
                },
                indent=2,
            )
        )


# ── Index + log helpers ────────────────────────────────────────────────────────


def load_index() -> dict:
    ensure_vault()
    return json.loads(INDEX_FILE.read_text())


def save_index(idx: dict):
    INDEX_FILE.write_text(json.dumps(idx, indent=2))


def append_log(action: str, path: str, detail: str = ""):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"{ts} | {action} | {path} | {detail}\n"
    existing = LOG_FILE.read_text() if LOG_FILE.exists() else ""
    lines = existing.splitlines(keepends=True)
    lines = lines[-(MAX_LOG_LINES - 1) :]
    lines.append(line)
    LOG_FILE.write_text("".join(lines))


def index_upsert(
    rel_path: str,
    title: str,
    folder: str,
    shape: str,
    tags: list[str],
    description: str = "",
):
    """Add or update a single entry in .cnote/index.json."""
    idx = load_index()
    idx["notes"][rel_path] = {
        "title": title,
        "folder": folder,
        "shape": shape,
        "tags": tags,
        "description": description or title,
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    save_index(idx)


def index_remove(rel_path: str):
    idx = load_index()
    if rel_path in idx["notes"]:
        del idx["notes"][rel_path]
        save_index(idx)


def index_move(old_rel: str, new_rel: str):
    idx = load_index()
    if old_rel in idx["notes"]:
        meta = idx["notes"].pop(old_rel)
        meta["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        idx["notes"][new_rel] = meta
        save_index(idx)


# ── Path / slug helpers ────────────────────────────────────────────────────────


def slugify(text: str, max_len: int = 60) -> str:
    """Lowercase, ASCII, hyphenated slug. Max 60 chars."""
    text = text.lower().strip()
    # strip emoji and non-ASCII
    text = re.sub(r"[^\x00-\x7f]+", " ", text)
    # drop punctuation except hyphen and underscore
    text = re.sub(r"[^\w\s-]", " ", text)
    # collapse whitespace and underscores to single hyphen
    text = re.sub(r"[\s_]+", "-", text)
    # collapse multiple hyphens
    text = re.sub(r"-+", "-", text)
    text = text.strip("-")
    return text[:max_len]


def validate_folder(folder: str) -> tuple[bool, str]:
    """Check that `folder` is a valid destination. Returns (ok, error_message)."""
    if not folder:
        return False, "folder is required"

    parts = folder.strip("/").split("/")
    top = parts[0]

    if top not in TOP_LEVEL:
        return (
            False,
            f"'{top}' is not a valid top-level folder. Valid: {sorted(TOP_LEVEL)}",
        )

    if top in FLAT_FOLDERS and len(parts) > 1:
        return False, f"'{top}/' is flat — no subfolders allowed"

    if top in SUBFOLDER_PARENTS:
        if len(parts) == 1:
            return False, f"'{top}/' requires a subfolder (e.g. {top}/<slug>)"
        if len(parts) > 2:
            return (
                False,
                f"'{top}/<slug>/' is the deepest allowed nesting in {top}/",
            )
        # subfolder slug must be valid
        sub = parts[1]
        if sub != slugify(sub):
            return False, f"subfolder '{sub}' is not a valid slug"

    return True, ""


def location_tag_for_folder(folder: str) -> Optional[str]:
    """Auto-derived location tag for a folder."""
    parts = folder.strip("/").split("/")
    top = parts[0]
    if top == "clients" and len(parts) == 2:
        return f"#client/{parts[1]}"
    if top == "projects" and len(parts) == 2:
        return f"#project/{parts[1]}"
    if top == "library":
        return "#library"
    if top == "life":
        return "#life"
    return None


def shape_tag(shape: str) -> str:
    return f"#shape/{shape}"


# ── File body helpers ──────────────────────────────────────────────────────────


_TAG_LINE_RE = re.compile(r"^\s*(#\S+\s*)+\s*$")


def _strip_existing_wrapper(content: str) -> tuple[Optional[str], str]:
    """If content already has a # Title heading, strip it off and return (title, body).
    Otherwise return (None, content).

    Also strips an italicized metadata line immediately after the title if present.
    Also strips a trailing tag-only line.
    """
    lines = content.splitlines()
    title = None
    start = 0

    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
        start = 1
        # skip an italicized meta line if next
        if (
            start < len(lines)
            and lines[start].startswith("*")
            and lines[start].endswith("*")
        ):
            start += 1
        # skip a blank line after meta
        while start < len(lines) and not lines[start].strip():
            start += 1

    # strip trailing blank lines
    end = len(lines)
    while end > start and not lines[end - 1].strip():
        end -= 1

    # strip a trailing tag-only line
    if end > start and _TAG_LINE_RE.match(lines[end - 1]):
        end -= 1

    body = "\n".join(lines[start:end]).strip()
    return title, body


def render_body(
    title: str,
    body: str,
    tags: list[str],
    meta_note: str = "",
) -> str:
    """Wrap body content in the canonical C-Note file format.

    # <title>
    *<meta_note>*

    <body>

    #tag1  #tag2 ...
    """
    today = datetime.now().strftime("%Y-%m-%d")
    if not meta_note:
        meta_note = f"Created {today}"
    tag_line = "  ".join(tags)
    return f"# {title}\n*{meta_note}*\n\n{body.strip()}\n\n{tag_line}\n"


def merge_tags(*tag_groups: list[str]) -> list[str]:
    """Dedupe-preserve-order tag merge."""
    out: list[str] = []
    for group in tag_groups:
        for t in group or []:
            t = t.strip()
            if not t:
                continue
            if not t.startswith("#"):
                t = "#" + t
            if t not in out:
                out.append(t)
    return out


# ── Input models ───────────────────────────────────────────────────────────────


class SaveInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    content: str = Field(..., description="Markdown body content", min_length=1)
    title: Optional[str] = Field(
        default=None,
        description="Title for the file. If omitted, derived from first heading or first line of content.",
        max_length=200,
    )
    folder: str = Field(
        default="inbox",
        description=(
            "Destination folder. One of: inbox, daily, library, life, "
            "clients/<slug>, projects/<slug>. Defaults to inbox."
        ),
    )
    shape: Optional[str] = Field(
        default=None,
        description=(
            "File shape: log | evergreen | index | inbox | daily. "
            "Inferred from folder if omitted."
        ),
    )
    slug: Optional[str] = Field(
        default=None,
        description="Optional explicit slug for the filename (without .md). If omitted, derived from title.",
    )
    date_override: Optional[str] = Field(
        default=None,
        description="YYYY-MM-DD to use as the date prefix for shape=log. Defaults to today.",
    )
    tags: Optional[list[str]] = Field(
        default_factory=list,
        description="Additional tags beyond auto-applied shape + location tags",
    )
    description: Optional[str] = Field(
        default=None,
        description="One-sentence description for the vault index. Defaults to title.",
        max_length=300,
    )


class InboxFileInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    filename: str = Field(
        ..., description="Filename in inbox/ to file (no path prefix)"
    )
    destination_folder: str = Field(
        ...,
        description="Where to file it (e.g. clients/418-productions, library, projects/lemr)",
    )
    new_slug: Optional[str] = Field(
        default=None,
        description="New slug for the file (without .md). If omitted, derived from title.",
    )
    shape: Optional[str] = Field(
        default=None,
        description="log | evergreen | index. Inferred if omitted.",
    )
    title: Optional[str] = Field(
        default=None,
        description="Override the title parsed from the file",
        max_length=200,
    )
    tags: Optional[list[str]] = Field(default_factory=list)
    description: Optional[str] = Field(default=None, max_length=300)


class MoveInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    from_path: str = Field(..., description="Current vault-relative path")
    to_folder: str = Field(..., description="New folder (must be a valid destination)")
    new_slug: Optional[str] = Field(default=None, description="New slug, without .md")


class SearchInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(..., min_length=1)
    folder: Optional[str] = Field(
        default=None, description="Restrict to a folder prefix"
    )
    shape: Optional[str] = Field(default=None)
    tag: Optional[str] = Field(default=None, description="Require this tag")
    limit: int = Field(default=10, ge=1, le=50)


class GetInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    rel_path: str = Field(..., min_length=1)


class AppendInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    rel_path: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)


# ── Core logic ─────────────────────────────────────────────────────────────────


def _infer_shape(folder: str, slug: str, explicit: Optional[str]) -> str:
    if explicit:
        if explicit not in SHAPES:
            raise ValueError(f"shape must be one of {SHAPES}")
        return explicit
    top = folder.split("/")[0]
    if top == "inbox":
        return "inbox"
    if top == "daily":
        return "daily"
    if slug == "_index":
        return "index"
    # If slug starts with YYYY-MM-DD pattern → log
    if re.match(r"^\d{4}-\d{2}-\d{2}-", slug):
        return "log"
    return "evergreen"


def _derive_title(content: str, override: Optional[str]) -> str:
    if override:
        return override.strip()
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("# "):
            return line[2:].strip()
        return line[:120]
    return "Untitled"


def _build_filename(shape: str, slug: str, date_override: Optional[str]) -> str:
    if shape == "log":
        date = date_override or datetime.now().strftime("%Y-%m-%d")
        # Strip any date already in slug to avoid double-dating
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}-?", "", slug)
        return f"{date}-{slug}.md"
    if shape == "index":
        return "_index.md"
    return f"{slug}.md"


def _resolve_destination(
    folder: str, filename: str, allow_overwrite: bool = False
) -> Path:
    dest = VAULT_ROOT / folder / filename
    if dest.exists() and not allow_overwrite:
        base = dest.stem
        ext = dest.suffix
        counter = 2
        while dest.exists():
            dest = VAULT_ROOT / folder / f"{base}-{counter}{ext}"
            counter += 1
    return dest


def _ensure_subfolder(folder: str):
    """Ensure the destination folder exists. For clients/projects, also stub an _index.md."""
    full = VAULT_ROOT / folder
    full.mkdir(parents=True, exist_ok=True)
    parts = folder.split("/")
    if parts[0] in SUBFOLDER_PARENTS and len(parts) == 2:
        index_path = full / "_index.md"
        if not index_path.exists():
            kind = "Client" if parts[0] == "clients" else "Project"
            slug = parts[1]
            title = slug.replace("-", " ").title()
            body = (
                f"## What this is\n\n_(stub — fill in)_\n\n"
                f"## Status\n\n_(stub — fill in)_\n\n"
                f"## Key docs\n\n_(stub — populate as evergreen docs are added)_"
            )
            shape = "index"
            tags = [shape_tag(shape)]
            loc = location_tag_for_folder(folder)
            if loc:
                tags.append(loc)
            index_path.write_text(render_body(f"{kind}: {title}", body, tags))
            rel = str(index_path.relative_to(VAULT_ROOT))
            index_upsert(
                rel, f"{kind}: {title}", folder, shape, tags, f"Index for {folder}"
            )
            append_log("stubbed-index", rel, "auto on subfolder create")


# ── Tools ──────────────────────────────────────────────────────────────────────


@mcp.tool(
    name="cn_save",
    annotations={
        "title": "Save Note",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def cn_save(params: SaveInput) -> str:
    """Write content to a destination folder with the canonical body format.

    Defaults to dropping into inbox/ if no folder is given. The MCP server will:
    - Validate the folder against the structure spec.
    - Pick a slug from the title if none is given.
    - Apply #shape/* and the location tag (#client/<slug>, #project/<slug>, #library, #life).
    - Stub an _index.md if a new client or project subfolder is being created.
    - Update .cnote/index.json and the activity log.

    Args:
        params: SaveInput

    Returns:
        str: JSON with path, title, shape, tags, action
    """
    ensure_vault()

    ok, err = validate_folder(params.folder)
    if not ok:
        return json.dumps({"error": err})

    # Special case: daily folder collapses to today's file
    if params.folder == "daily":
        return await _save_to_daily(params)

    title = _derive_title(params.content, params.title)
    slug = params.slug or slugify(title)
    if not slug:
        return json.dumps({"error": "could not derive a valid slug from title"})

    shape = _infer_shape(params.folder, slug, params.shape)
    filename = _build_filename(shape, slug, params.date_override)

    _ensure_subfolder(params.folder)
    dest = _resolve_destination(params.folder, filename)

    # Auto tags
    auto = [shape_tag(shape)]
    loc = location_tag_for_folder(params.folder)
    if loc:
        auto.append(loc)
    all_tags = merge_tags(auto, params.tags or [])

    # Strip any existing wrapper from incoming content, then re-wrap
    _, body = _strip_existing_wrapper(params.content)
    today = datetime.now().strftime("%Y-%m-%d")
    meta = f"Created {today}"
    dest.write_text(render_body(title, body, all_tags, meta))

    rel = str(dest.relative_to(VAULT_ROOT))
    index_upsert(
        rel, title, params.folder, shape, all_tags, params.description or title
    )
    append_log("save", rel, title)

    return json.dumps(
        {
            "action": "created",
            "path": rel,
            "title": title,
            "shape": shape,
            "tags": all_tags,
            "message": f"'{title}' → {rel}",
        },
        indent=2,
    )


async def _save_to_daily(params: SaveInput) -> str:
    """Helper: append to today's daily note or create it."""
    date = params.date_override or datetime.now().strftime("%Y-%m-%d")
    daily = VAULT_ROOT / "daily" / f"{date}.md"
    title = _derive_title(params.content, params.title)
    _, body = _strip_existing_wrapper(params.content)
    ts = datetime.now().strftime("%H:%M")

    if daily.exists():
        existing = daily.read_text()
        addition = f"\n\n---\n\n## {ts} — {title}\n\n{body}\n"
        daily.write_text(existing + addition)
        action = "appended-daily"
    else:
        tags = [shape_tag("daily")]
        all_tags = merge_tags(tags, params.tags or [])
        full_body = f"## {ts} — {title}\n\n{body}"
        daily.write_text(
            render_body(f"Daily Note — {date}", full_body, all_tags, f"Created {date}")
        )
        action = "created-daily"

    rel = str(daily.relative_to(VAULT_ROOT))
    # daily notes get a single index entry (per file), updated on each touch
    idx = load_index()
    if rel not in idx["notes"]:
        idx["notes"][rel] = {
            "title": f"Daily — {date}",
            "folder": "daily",
            "shape": "daily",
            "tags": [shape_tag("daily")],
            "description": f"Daily journal {date}",
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
    else:
        idx["notes"][rel]["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_index(idx)
    append_log(action, rel, title)

    return json.dumps(
        {
            "action": action,
            "path": rel,
            "title": title,
            "message": f"'{title}' → {rel}",
        },
        indent=2,
    )


@mcp.tool(
    name="cn_inbox_list",
    annotations={
        "title": "List Inbox",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def cn_inbox_list() -> str:
    """Show every file in inbox/ with a short snippet for triage.

    Returns:
        str: JSON list of {filename, size, mtime, snippet} entries
    """
    ensure_vault()
    inbox = VAULT_ROOT / "inbox"
    items = []
    for p in sorted(inbox.glob("*.md")):
        try:
            text = p.read_text()
            snippet = text.strip().splitlines()[0][:120] if text.strip() else "(empty)"
            items.append(
                {
                    "filename": p.name,
                    "size": p.stat().st_size,
                    "mtime": datetime.fromtimestamp(p.stat().st_mtime).strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                    "snippet": snippet,
                }
            )
        except Exception as e:
            items.append({"filename": p.name, "error": str(e)})

    return json.dumps({"count": len(items), "items": items}, indent=2)


@mcp.tool(
    name="cn_inbox_file",
    annotations={
        "title": "File from Inbox",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def cn_inbox_file(params: InboxFileInput) -> str:
    """Move one file from inbox/ to its destination with the canonical wrapper applied.

    Rewrites the file head to match the canonical body format, auto-applies #shape/*
    and location tags, then moves the file. Updates the index and activity log.

    Args:
        params: InboxFileInput

    Returns:
        str: JSON with from, to, action, tags, message
    """
    ensure_vault()
    src = VAULT_ROOT / "inbox" / params.filename
    if not src.exists():
        return json.dumps({"error": f"inbox/{params.filename} not found"})

    ok, err = validate_folder(params.destination_folder)
    if not ok:
        return json.dumps({"error": err})

    original = src.read_text()
    parsed_title, body = _strip_existing_wrapper(original)
    title = params.title or parsed_title or _derive_title(original, None)
    slug = params.new_slug or slugify(title)
    if not slug:
        return json.dumps({"error": "could not derive a valid slug"})

    shape = _infer_shape(params.destination_folder, slug, params.shape)
    filename = _build_filename(shape, slug, None)

    _ensure_subfolder(params.destination_folder)
    dest = _resolve_destination(params.destination_folder, filename)

    auto = [shape_tag(shape)]
    loc = location_tag_for_folder(params.destination_folder)
    if loc:
        auto.append(loc)
    all_tags = merge_tags(auto, params.tags or [])

    today = datetime.now().strftime("%Y-%m-%d")
    meta = f"Filed from inbox {today}"
    dest.write_text(render_body(title, body, all_tags, meta))
    src.unlink()

    src_rel = f"inbox/{params.filename}"
    dst_rel = str(dest.relative_to(VAULT_ROOT))
    index_upsert(
        dst_rel,
        title,
        params.destination_folder,
        shape,
        all_tags,
        params.description or title,
    )
    append_log("inbox-file", dst_rel, f"from {src_rel}")

    return json.dumps(
        {
            "from": src_rel,
            "to": dst_rel,
            "title": title,
            "shape": shape,
            "tags": all_tags,
            "message": f"{src_rel} → {dst_rel}",
        },
        indent=2,
    )


@mcp.tool(
    name="cn_move",
    annotations={
        "title": "Move File",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def cn_move(params: MoveInput) -> str:
    """Move a file from one location to another inside the vault.

    Re-derives shape and re-applies auto tags based on the new location.

    Args:
        params: MoveInput

    Returns:
        str: JSON with from, to, message
    """
    ensure_vault()
    src = VAULT_ROOT / params.from_path
    if not src.exists():
        return json.dumps({"error": f"{params.from_path} not found"})

    ok, err = validate_folder(params.to_folder)
    if not ok:
        return json.dumps({"error": err})

    original = src.read_text()
    parsed_title, body = _strip_existing_wrapper(original)
    title = parsed_title or src.stem.replace("-", " ").title()
    slug = params.new_slug or src.stem
    # Strip any date prefix from stem when re-deriving slug for non-log shape
    shape = _infer_shape(params.to_folder, slug, None)
    filename = _build_filename(shape, slug, None)

    _ensure_subfolder(params.to_folder)
    dest = _resolve_destination(params.to_folder, filename)

    # Preserve existing tags from the old file when relocating
    existing_tags: list[str] = []
    for line in original.splitlines():
        if _TAG_LINE_RE.match(line):
            existing_tags = [t for t in line.split() if t.startswith("#")]

    # Drop stale location/shape tags, add new
    cleaned = [
        t
        for t in existing_tags
        if not (
            t.startswith("#shape/")
            or t.startswith("#client/")
            or t.startswith("#project/")
            or t in ("#library", "#life")
        )
    ]
    auto = [shape_tag(shape)]
    loc = location_tag_for_folder(params.to_folder)
    if loc:
        auto.append(loc)
    all_tags = merge_tags(auto, cleaned)

    today = datetime.now().strftime("%Y-%m-%d")
    meta = f"Moved {today}"
    dest.write_text(render_body(title, body, all_tags, meta))
    src.unlink()

    src_rel = params.from_path
    dst_rel = str(dest.relative_to(VAULT_ROOT))
    index_remove(src_rel)
    index_upsert(dst_rel, title, params.to_folder, shape, all_tags)
    append_log("move", dst_rel, f"from {src_rel}")

    return json.dumps(
        {
            "from": src_rel,
            "to": dst_rel,
            "title": title,
            "shape": shape,
            "tags": all_tags,
            "message": f"{src_rel} → {dst_rel}",
        },
        indent=2,
    )


@mcp.tool(
    name="cn_search",
    annotations={
        "title": "Search Vault",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def cn_search(params: SearchInput) -> str:
    """Search the vault index and file contents for a query.

    Args:
        params: SearchInput

    Returns:
        str: JSON results
    """
    ensure_vault()
    idx = load_index()
    terms = [t for t in params.query.lower().split() if t]
    results = []

    for rel_path, meta in idx["notes"].items():
        if params.folder and not rel_path.startswith(params.folder.strip("/") + "/"):
            continue
        if params.shape and meta.get("shape") != params.shape:
            continue
        if params.tag and params.tag not in meta.get("tags", []):
            continue

        score = 0
        haystack = (
            meta.get("title", "")
            + " "
            + meta.get("description", "")
            + " "
            + " ".join(meta.get("tags", []))
        ).lower()
        for term in terms:
            if term in haystack:
                score += 2

        snippet = ""
        file_path = VAULT_ROOT / rel_path
        if file_path.exists():
            try:
                text = file_path.read_text()
                lower = text.lower()
                for term in terms:
                    if term in lower:
                        score += 1
                        i = lower.find(term)
                        start = max(0, i - 60)
                        end = min(len(text), i + 120)
                        snippet = "..." + text[start:end].strip() + "..."
                        break
            except Exception:
                pass

        if score > 0:
            results.append(
                {
                    "path": rel_path,
                    "title": meta.get("title", rel_path),
                    "folder": meta.get("folder", ""),
                    "shape": meta.get("shape", ""),
                    "tags": meta.get("tags", []),
                    "updated": meta.get("updated", ""),
                    "score": score,
                    "snippet": snippet,
                }
            )

    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[: params.limit]
    return json.dumps(
        {"query": params.query, "count": len(results), "results": results}, indent=2
    )


@mcp.tool(
    name="cn_get",
    annotations={
        "title": "Get File",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def cn_get(params: GetInput) -> str:
    """Return the full content of a file by its vault-relative path."""
    ensure_vault()
    file_path = VAULT_ROOT / params.rel_path
    if not file_path.exists():
        return json.dumps({"error": f"file not found: {params.rel_path}"})
    idx = load_index()
    meta = idx["notes"].get(params.rel_path, {})
    return json.dumps(
        {"path": params.rel_path, "meta": meta, "content": file_path.read_text()},
        indent=2,
    )


@mcp.tool(
    name="cn_append",
    annotations={
        "title": "Append to File",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def cn_append(params: AppendInput) -> str:
    """Append content to an existing file, with a timestamped divider.

    No fuzzy matching — the path must be exact. Use cn_search first if needed.

    Args:
        params: AppendInput
    """
    ensure_vault()
    file_path = VAULT_ROOT / params.rel_path
    if not file_path.exists():
        return json.dumps({"error": f"file not found: {params.rel_path}"})

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    # Read existing, then insert append BEFORE the trailing tag line so tags stay on the last line
    existing = file_path.read_text()
    lines = existing.splitlines()
    insert_at = len(lines)
    # Find trailing tag line position
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip() and _TAG_LINE_RE.match(lines[i]):
            insert_at = i
            break
        if lines[i].strip():
            break
    addition = f"\n---\n*Added {ts}*\n\n{params.content.strip()}\n"
    new_lines = lines[:insert_at] + addition.splitlines() + [""] + lines[insert_at:]
    file_path.write_text("\n".join(new_lines) + "\n")

    idx = load_index()
    if params.rel_path in idx["notes"]:
        idx["notes"][params.rel_path]["updated"] = ts
        save_index(idx)
    append_log("append", params.rel_path, "manual append")

    return json.dumps(
        {"path": params.rel_path, "message": f"appended to {params.rel_path}"}, indent=2
    )


@mcp.tool(
    name="cn_index",
    annotations={
        "title": "Get Vault Index",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def cn_index(
    folder: Optional[str] = None,
    shape: Optional[str] = None,
    tag: Optional[str] = None,
) -> str:
    """Return the vault index, optionally filtered.

    Args:
        folder: top-level or full folder path prefix
        shape: log | evergreen | index | daily | inbox
        tag: require this tag

    Returns:
        str: JSON with notes
    """
    ensure_vault()
    idx = load_index()
    notes = idx["notes"]
    if folder:
        prefix = folder.strip("/") + "/"
        notes = {k: v for k, v in notes.items() if k.startswith(prefix)}
    if shape:
        notes = {k: v for k, v in notes.items() if v.get("shape") == shape}
    if tag:
        notes = {k: v for k, v in notes.items() if tag in v.get("tags", [])}

    return json.dumps(
        {
            "total_notes": len(notes),
            "filters": {"folder": folder, "shape": shape, "tag": tag},
            "notes": notes,
        },
        indent=2,
    )


@mcp.tool(
    name="cn_daily",
    annotations={
        "title": "Get Today's Daily Note",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def cn_daily() -> str:
    """Return today's daily note, creating it with a header if it doesn't exist."""
    ensure_vault()
    date = datetime.now().strftime("%Y-%m-%d")
    daily = VAULT_ROOT / "daily" / f"{date}.md"
    if not daily.exists():
        tags = [shape_tag("daily")]
        daily.write_text(
            render_body(f"Daily Note — {date}", "", tags, f"Created {date}")
        )
        rel = str(daily.relative_to(VAULT_ROOT))
        idx = load_index()
        idx["notes"][rel] = {
            "title": f"Daily — {date}",
            "folder": "daily",
            "shape": "daily",
            "tags": tags,
            "description": f"Daily journal {date}",
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        save_index(idx)
        append_log("created-daily", rel, date)
    rel = str(daily.relative_to(VAULT_ROOT))
    return json.dumps(
        {"path": rel, "date": date, "content": daily.read_text()}, indent=2
    )


@mcp.tool(
    name="cn_recent",
    annotations={
        "title": "Recent Activity",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def cn_recent(lines: int = 20) -> str:
    """Recent activity log entries.

    Args:
        lines: how many recent lines to return (max 200)
    """
    ensure_vault()
    if not LOG_FILE.exists():
        return json.dumps({"recent": []})
    all_lines = LOG_FILE.read_text().splitlines()
    recent = all_lines[-min(lines, 200) :]
    return json.dumps({"count": len(recent), "recent": recent}, indent=2)


@mcp.tool(
    name="cn_clients",
    annotations={
        "title": "List Clients",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def cn_clients() -> str:
    """List every client folder under clients/.

    Returns the slug, file count, and the title from _index.md if present.
    """
    ensure_vault()
    base = VAULT_ROOT / "clients"
    out = []
    for sub in sorted([p for p in base.iterdir() if p.is_dir()]):
        idx_md = sub / "_index.md"
        title = sub.name
        if idx_md.exists():
            for line in idx_md.read_text().splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
        files = list(sub.glob("*.md"))
        out.append(
            {
                "slug": sub.name,
                "path": f"clients/{sub.name}",
                "title": title,
                "file_count": len(files),
            }
        )
    return json.dumps({"count": len(out), "clients": out}, indent=2)


@mcp.tool(
    name="cn_projects",
    annotations={
        "title": "List Projects",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def cn_projects() -> str:
    """List every project folder under projects/.

    Returns the slug, file count, and title from _index.md if present.
    """
    ensure_vault()
    base = VAULT_ROOT / "projects"
    out = []
    for sub in sorted([p for p in base.iterdir() if p.is_dir()]):
        idx_md = sub / "_index.md"
        title = sub.name
        if idx_md.exists():
            for line in idx_md.read_text().splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
        files = list(sub.glob("*.md"))
        out.append(
            {
                "slug": sub.name,
                "path": f"projects/{sub.name}",
                "title": title,
                "file_count": len(files),
            }
        )
    return json.dumps({"count": len(out), "projects": out}, indent=2)


# ── Entrypoint ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ensure_vault()
    mcp.run()
