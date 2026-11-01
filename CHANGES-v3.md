# C-Note MCP v3 — Changes

New file: `cnote-mcp-server-v3.py`. The running v2 server is untouched until you swap it in.

## Principles

Reads are structure-agnostic (every tool sees the whole vault, including legacy folders and loose root files). Writes are structure-aware (guided into canonical folders, with warnings instead of walls). Nothing is ever deleted — no delete function exists in the codebase. Moves never rewrite content.

## Fixed

- **Path traversal hole** — `cn_get`/`cn_append`/`cn_move`/`cn_update`/`cn_retire` now reject `..`, absolute paths, and anything resolving outside the vault.
- **Lossy moves** — `cn_move` is now a real `shutil.move`; body bytes are never touched. Optional retag edits only the trailing tag line.
- **Fragile tag parsing** — a line counts as a tag line only if *every* token matches `#word[/sub]`. `#!/bin/bash`, `#include`, `# Heading` are safe.
- **Blind search** — `cn_search` scans the filesystem directly (filenames, titles, tags, content). The 158-entry/52%-stale index is no longer a gatekeeper; it survives only as a description cache.
- **Silent duplicates** — collisions still auto-suffix but are reported in a `warnings` field.
- **Daily-note bugs** — tags no longer dropped when appending to an existing daily note.

## Added

- `cn_list` — browse any folder (recursive option), structure-agnostic.
- `cn_update` — rewrite a note; **snapshots the old version to `archive/<path>/<name>--<timestamp>.md` by default**. `snapshot_old=false` for trivial edits only.
- `cn_retire` — the only removal mechanism: moves to `bin/<original-path>`. Restore via `cn_move` from a `bin/...` path.
- `cn_reindex` — rebuild the index from disk (with `dry_run`). Heals all drift.
- **Git auto-commit** after every write (config flag `git_autocommit`, on by default). Second safety net under archive/bin.
- `archive/` and `bin/` excluded from search/list unless `include_archive`/`include_bin` is passed.
- `cn_recent` now also reports recently *modified* files (catches direct Obsidian edits).
- Proactive-use language in read-tool docstrings, so any Claude consults c-note unprompted.

## Relaxed

- `clients/` and `projects/` allow 3 levels (`clients/418-productions/diy-deep-freeze/` is now legal); `library/` and `life/` allow one subfolder level.
- Non-canonical folders (`logseq-mattie-aran/`, `imported-unsorted/`, `Music/`, root files) are fully readable/searchable/listable. New writes still go to canonical folders.
- Folder segments are auto-slugified with a warning instead of rejected.

## Removed

- Human-facing `_system/index.md` generation (per Mattie: index.json is Claude-side plumbing only).
- Vestigial `structure.md`/`tag-taxonomy.md` references (those files no longer exist).

## To switch over

1. Point the `cnote` entry in `claude_desktop_config.json` at `cnote-mcp-server-v3.py` (or rename files).
2. Restart Claude Desktop.
3. Ask Claude to run `cn_reindex` once — it will index all ~850 notes and drop the 83 stale entries.
4. In connector settings, set the read tools (`cn_search`, `cn_get`, `cn_list`, `cn_index`, `cn_recent`, `cn_clients`, `cn_projects`, `cn_inbox_list`, `cn_daily`) to always-allow; leave writes on ask.

## Tested

12 scenario groups against a scratch vault: path guard, whole-vault search (deep legacy nesting + loose root files), collision reporting, snapshot-on-update with tag preservation, retire/bin exclusion/restore, byte-identical moves, shebang-vs-tag-line safety, depth-3 inbox filing, reindex drift healing, list exclusions, daily/recent, git auto-commit. All passed.
