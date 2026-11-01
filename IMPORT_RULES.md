# Claude Code: Reflect Import Ground Rules

# C-Note Vault — Reflect → Markdown Migration

---

## Your Mission

You are importing a Reflect Notes export into a structured plain-text vault.
The vault already exists with a folder structure, an MCP server, and documented conventions.
Your job is to read, understand, reorganize, reformat, and index the imported notes.

This is a judgment task, not a mechanical one. You are expected to read content,
infer meaning and intent, and make reasonable categorization decisions.

---

## Read These First

Before doing anything else, read the following files in order:

```
/Users/lupin/_Workspace/Docs/C-Note/_system/README.md
/Users/lupin/_Workspace/Docs/C-Note/_system/tag-taxonomy.md
```

These contain the vault structure, category definitions, note types, and tag conventions
you must follow when writing any file.

---

## Vault Location

```
/Users/lupin/_Workspace/Docs/C-Note
```

## Import Source

```
/Users/lupin/_Workspace/Docs/C-Note/imported-unsorted/
/Users/lupin/_Workspace/Docs/C-Note/imported-unsorted/daily-notes/
```

---

## Background: How Reflect Works

Reflect is a backlink-first note-taking app. The owner used it like this:

- Almost everything was entered in **daily notes** as bullet points
- A bullet under a `[[Topic Reference]]` link means that content _belongs to_ that topic
- The standalone topic files (e.g. `LEMR.md`, `Ableton Live.md`) are often **hollow** —
  they just contain wiki-links to sub-topics, not real content
- The **real content** lives in daily notes as indented blocks beneath topic references

This means:

1. Daily notes are the **source of truth** for most content
2. Topic files are often just navigation anchors — useful as index files but not content files
3. Some topic files DO contain real content (pasted reference material, structured notes,
   cheatsheets, etc.) — these should be kept and reformatted

---

## What You Need To Do

### Pass 1 — Daily Notes

Files in: `imported-unsorted/daily-notes/YYYY-MM-DD.md`
Destination: `daily/YYYY-MM-DD.md`

- Copy all daily notes to `daily/`
- Reformat them: clean up any broken formatting, normalize heading levels
- Keep `[[wiki-links]]` intact — Obsidian uses these for backlinks
- Do NOT try to extract or move content out of daily notes in this pass
- If the file already exists in `daily/`, skip it

### Pass 2 — Topic Note Classification

Files in: `imported-unsorted/*.md`

For each file, read it and make one of these decisions:

**A) Real content note** — Has actual substance (reference material, instructions,
cheatsheet, structured data, pasted docs, project notes). Reformat and place in the
correct vault folder. See _Categorization Guide_ below.

**B) Index/anchor note** — Mostly wiki-links, sub-topic lists, or a brief description
with links. Save as `_index.md` inside the appropriate topic folder.
Example: `topics/dev/lemr/_index.md`

**C) Daily note fragment** — Short, clearly a momentary capture or a single thought.
If it can be appended to an existing topic file, do that. If not, drop it into today's
daily note area or discard if it's truly empty.

**D) Discard** — Duplicate, empty after cleanup, purely navigational with no content
value, or clearly superseded. Log the filename and reason in the batch summary.

---

## Categorization Guide

Use your judgment. When ambiguous, prefer the broader category over a narrow one.

| Content type                                   | Destination folder     | Category tag    |
| ---------------------------------------------- | ---------------------- | --------------- |
| LEMR app (medical notes app)                   | `topics/dev/lemr/`     | `#dev/lemr`     |
| Other code projects (LTD, Phantom Power, etc.) | `topics/dev/projects/` | `#dev/projects` |
| Dev tools, editors, languages, workflows       | `topics/dev/general/`  | `#dev/general`  |
| Music production, songs, ideas, beats          | `topics/music/`        | `#music`        |
| Audio plugins, gear, engineering               | `topics/audio/`        | `#audio`        |
| Job search, resume, career                     | `topics/career/`       | `#career`       |
| Home, apartment, life admin                    | `topics/home/`         | `#home`         |
| Personal, therapy, relationships               | `topics/personal/`     | `#personal`     |
| Pasted code docs, tutorials, how-tos           | `reference/code/`      | `#ref/code`     |
| Software setup guides                          | `reference/software/`  | `#ref/software` |
| Audio plugin manuals, gear guides              | `reference/audio/`     | `#ref/audio`    |
| Everything else reference                      | `reference/general/`   | `#ref/general`  |

**Known projects and their categories:**

- LEMR → `dev/lemr`
- Lupine Tech Design / LTD → `dev/projects`
- Phantom Power → `dev/projects`
- Work Sweet / Vet Sweet → `dev/projects`
- SnipFlow → `dev/projects`
- Note Sweet → `dev/projects`
- Ableton Live → `music` (unless it's a plugin reference, then `audio`)
- Doom Emacs, NeoVim, LazyVim → `dev/general`
- Resume, job postings → `career`
- 371 Preble Street, neighbors → `home`

---

## File Naming

- Strip the Reflect UUID from filenames: `LEMR-079c644115fd.md` → `lemr.md`
- Lowercase, hyphens for spaces: `Ableton Live 12 Minimal Setup 2025` → `ableton-live-12-minimal-setup-2025.md`
- Remove emoji from filenames (keep them in content if present)
- Index files are always named `_index.md` inside their folder
- If a destination file already exists, append the new content under a `---` divider
  with a note: `*Merged from Reflect import, [original filename]*`

---

## Formatting Rules

When writing or reformatting a note:

1. **First line** must be a `# Title` heading
2. **Second line** should be the creation context if known:
   `*Imported from Reflect · Original: [filename]*`
3. **Content** — reformat Reflect's nested bullet structure into readable markdown.
   Deeply nested bullet trees are fine to keep as bullets. Prose should be prose.
4. **Wiki-links** — keep `[[Like This]]` intact. Do not convert them.
5. **Code blocks** — wrap any code in proper fenced blocks with language tag
6. **Tags line** — bottom of every file, space-separated inline tags per tag-taxonomy.md
   Example: `#dev/lemr  #type/reference  #imported/reflect`
7. **No frontmatter** — never add YAML frontmatter

---

## Index File (.cnote/index.json)

After each batch, update the index. The index lives at:

```
/Users/lupin/_Workspace/Docs/C-Note/.cnote/index.json
```

Format for each entry:

```json
"topics/dev/lemr/lemr.md": {
  "title": "LEMR",
  "category": "dev/lemr",
  "type": "log",
  "tags": ["#dev/lemr", "#type/log", "#imported/reflect"],
  "updated": "2026-02-24 21:00"
}
```

---

## Batch Size and Process

Work in batches of **20 files at a time**. After each batch:

1. Print a summary:
   - Files processed
   - Where each one was placed (or discarded and why)
   - Any ambiguous decisions you made and what you chose
   - Any files you want a human to review (flag with `⚠️`)

2. Pause and ask: _"Ready for the next batch?"_ before continuing.

This keeps the work reviewable and recoverable without having to process 300+ files
in one shot.

**Suggested batch order:**

1. Daily notes first (mechanical, safest)
2. Named topic files with clear categories (LEMR, Ableton, Resume, etc.)
3. Named topic files that are ambiguous
4. Any remaining files

---

## What NOT To Do

- Do not delete anything from `imported-unsorted/` — it is the backup
- Do not create frontmatter / YAML blocks
- Do not flatten or destroy wiki-link structure
- Do not merge two notes that are clearly distinct topics just because they share a keyword
- Do not invent content — if a note is sparse, keep it sparse
- Do not add your own commentary or summaries to notes unless explicitly asked
- Do not create new categories not listed in the tag taxonomy

---

## When In Doubt

- Broader category > narrower category
- Keep > discard (when content value is unclear)
- Flag with `⚠️` in batch summary > make a bad decision silently
- `reference/general` is the catch-all for anything truly uncategorizable

---

## Git

A clean commit should exist before you start. If it doesn't, run:

```bash
cd /Users/lupin/_Workspace/Docs/C-Note
git init
git add .
git commit -m "pre-import snapshot"
```

This gives a rollback point if anything goes wrong.
