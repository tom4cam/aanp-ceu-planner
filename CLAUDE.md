# AANP 2026 CEU Planner — project handoff

Phone-friendly web app for **Sarah** (acute-care NP / AGACNP) to plan the **2026 AANP National
Conference** (Las Vegas, Jun 23–27) and track CEUs toward her **75-CE** renewal. No backend; all
state in the browser's localStorage.

- **Live:** https://tom4cam.github.io/aanp-ceu-planner/
- **Repo:** https://github.com/tom4cam/aanp-ceu-planner (public; GitHub Pages from `main` root)
- **Local:** `~/Library/CloudStorage/Dropbox/ai-other-projects/aanp-ceu-planner/`

## How to resume work later
1. Open this folder, read this file (current state + next steps below).
2. From inside the folder, run `claude --continue` (most recent chat here) or `claude --resume`
   (pick from a list). Claude sessions are scoped to the directory you launch from.
3. Deploy a change: edit files → `git add -A && git commit && git push`. GitHub Pages rebuilds
   in ~1 min. Bump `version.txt` (format `YYYY-MM-DD.N`) so the app's auto-updater reloads clients.

## Files
- `index.html` — the entire app (HTML + CSS + JS inline, ~1300 lines). The only file that runs.
- `data.js` — 393 sessions (`window.DATA`). Built by `build_data.py`.
- `details.js` — per-session description, presenters, handout URL (`window.DETAILS[code]`).
- `rooms.json` / floor plans — room names + Level 2–5 floorplan JPGs with pin coordinates.
- `build_data.py` — rebuilds `data.js` from `source-aanp-sessions.html` + `rooms.json`.
- `version.txt` — bump on every deploy to trigger client auto-reload.

## Key behaviors
- Per-session status: Live / Watch Later / Skip. CEU dashboard sums prior + live + recordings + manual toward 75.
- **My Map**: live picks drawn on real floorplans with walk-distance warnings (foot-injury aid).
- **My Notes**: sessions where you checked **⭐ Save slides to My Notes** or typed a note.
- Private seeds via query string (kept only in local storage, never in source):
  `?plan=sarah` loads her picks · `?drive=<folder link or id>` seeds the Drive folder.
  The auto-updater preserves the query string across version bumps.

## My Notes → Google Drive (slide PDFs)
Goal: one tap copies the real slide-deck PDFs for chosen sessions into Sarah's Drive folder.
- App side: **📥 Copy slide PDFs to Drive** (`copySlidesToDrive()` in index.html) opens the user's
  deployed Apps Script `/exec` URL (stored once via prompt in `state.driveScriptUrl`).
- Server side: `~/aanp-capture/copy-slides.gs` — `doGet()` runs `copySlides()`, which fetches
  `https://files.aanpdownload.org/2026/Natl/doc/{code}.pdf` per session, skips the ~57794-byte
  AANP placeholder and anything already in the folder (dedup), and copies the rest.
  Folder id is hardcoded (`FOLDER_ID`); deploy as Web app, Execute as Me, Anyone with link.
- **Open thread:** the script's `SESSIONS` list is a static snapshot of Sarah's 23 picks. The app
  passes no parameters, so it copies that fixed list — NOT whatever is currently checked in the app.
  Next step is to have the app pass the checked session codes and the script copy exactly those.

## Next steps / open threads
- [ ] Close the loop above: app passes `?codes=...` to the Apps Script; `doGet(e)` copies only those.
- [ ] After AANP assigns/updates rooms, re-capture and rebuild (`build_data.py` merges `rooms.json`).

## Reverse-engineering notes (rooms, picks, slides)
Full capture details live in Claude's memory file
`~/.claude/projects/-Users-tom-caswell/memory/aanp-ceu-planner.md` (mitmproxy setup, the Floq S3
content bundle that holds rooms, the `eval.aanp.org/api/conference` endpoint, Sarah's selections).
