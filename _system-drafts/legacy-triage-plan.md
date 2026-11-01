# Legacy Stacks — Census & Triage Plan

*Draft 2026-07-24. The plan for the ~730 untriaged legacy notes.*

## Census (from the first full-vault scan)

**Vault total: 850 notes.** Legacy portion: `logseq-mattie-aran/` (533: 331 pages + 202 journals) and `imported-unsorted/` (196: 115 loose Reflect exports, 80 Craft-processed, 1 daily). Plus ~14 loose root files.

Topic clusters (filename + content sniff, both stacks combined):

- dev/coding (~167): neovim, svelte/nextjs/storybook, git, terminal, emacs
- 418 / client IT (~99): intune, autopilot, entra, deep freeze, fleet
- music/audio (~70): ableton, MPC, synths, VSTs, guitars/pedals, qobuz
- life/personal (~55): housing (Preble Street), finances, people, skincare, letters
- notes-apps meta (~21): reflect, craft, obsidian, logseq migration notes
- windows-admin (~15)
- journals (204): 2025-08-31 → 2026-11-01 (one future-dated — likely typo)
- genuinely misc (~127): people pages (Eric Rubenstein, Aaron, Heriberto), Vet Sweet, piano voicings, samples lists, one-offs

Hollow/stub notes (≤3 lines or wiki-links only): **108** — mostly Logseq navigation anchors, per the Reflect/Logseq bullet-first style. Real content lives in journals.

## Proposed triage passes (each pass reviewable before the next)

1. **Stubs to bin.** Retire the ~108 hollow navigation anchors via `cn_retire` (nothing lost; they're in bin/ forever). Cheap, big clarity win.
2. **418 material → `clients/418-productions/`.** ~99 notes; merge-or-move decisions against the 61 already-organized notes there. Logs keep date prefixes.
3. **Reference bodies → `library/`.** The dev, music, and windows clusters become evergreen reference notes; near-duplicates consolidated with `cn_update` (old versions auto-archived).
4. **People & life → `life/`.** People pages, housing, finance.
5. **Projects extraction.** Vet Sweet, LEMR, pedal-UI etc. → `projects/<slug>/`.
6. **Journals last.** 204 Logseq journals: keep in place until passes 1–5 mine them (per IMPORT_RULES, journals are the source of truth for content under topic anchors), then move wholesale into `daily/` with normalized names, or leave frozen — Mattie's call.

Estimated shape: passes 1 and 4 are quick; 2, 3, 5 are judgment work best done a batch at a time in dedicated sessions; 6 is a decision plus a mechanical move.

## Ground rules during triage

Every move is a true move (bytes preserved). Anything doubtful goes to `inbox/` rather than guessed. Nothing is deleted — dupes and husks go to `bin/`. Each pass ends with `cn_reindex` and a summary for Mattie.
