# AANP 2026 CEU Planner — project handoff

Phone-friendly web app for **Sarah** (acute-care NP / AGACNP) to plan the **2026 AANP National
Conference** (Las Vegas, Jun 23–27) and track CEUs toward her **75-CE** renewal. No backend; all
state in the browser's localStorage.

- **Live:** https://tom4cam.github.io/aanp-ceu-planner/
- **Repo:** https://github.com/tom4cam/aanp-ceu-planner (public; GitHub Pages from `main` root)
- **Local:** `~/Library/CloudStorage/Dropbox/ai-other-projects/aanp-ceu-planner/`

> **⏪ Where we ended (2026-06-21):** My Notes → Drive is built, deployed, verified, and **fully
> wired end-to-end**. The Apps Script lives under sarahspendlovenp@gmail.com and copies exactly the
> checked sessions. The deployed `/exec` URL is now delivered to Sarah's device via a `?script=`
> seed link (no manual paste) — send her the one-tap link below; after she opens it once, *My Notes
> → 📥 Copy slide PDFs to Drive* is one tap. **Nothing left to do.**
>
> One-tap setup link (private — keep out of the public repo / commits):
> `https://tom4cam.github.io/aanp-ceu-planner/?plan=sarah&script=<the /exec URL>`
> The deployed `/exec` URL is in Sarah's deployment: script editor → Deploy → Manage deployments →
> Web app URL (ends in `/exec`). Not stored in this repo by design.

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
- **Home base (Palazzo Tower)**: `HOME` const + `homeDistanceTo()`/`homeTransitionHTML()` in index.html.
  Each day's first live session gets a "Start of day · from your Palazzo suite" walk line, and the
  Level 2 day map shows a purple **P** pin (the Expo entrance off the Palazzo walkway, with a dashed
  line to the first room there). Anchored at `{lvl:2, x:0.90, y:0.60}` — **approximate**; the exact
  guest-room position isn't in the AANP bundle, so adjust `HOME` once the room is assigned. Toggle:
  "Start each day from my Palazzo Tower suite" checkbox in My Map (`state.homeBase`, default on).
- **My Notes**: sessions where you checked **⭐ Save slides to My Notes** or typed a note.
- Private seeds via query string (kept only in local storage, never in source):
  `?plan=sarah` loads her picks · `?drive=<folder link or id>` seeds the Drive folder.
  The auto-updater preserves the query string across version bumps.

## My Notes → Google Drive (slide PDFs)
Goal: one tap copies the real slide-deck PDFs for chosen sessions into Sarah's Drive folder.
- App side: **📥 Copy slide PDFs to Drive** (`copySlidesToDrive()` in index.html) opens the user's
  deployed Apps Script `/exec` URL (stored in `state.driveScriptUrl`).
- **Seeding the `/exec` URL (preferred):** open the planner once with `?script=<exec url>` — the
  seed handler (index.html, near the `?drive=`/`?plan=` block) validates a
  `https://script.google.com/.../exec` URL, saves it to localStorage, and scrubs it from the
  address bar. So Sarah just taps one link instead of pasting the long URL into a phone prompt.
  The manual `prompt()` in `copySlidesToDrive()` remains as a fallback.
- Server side: `apps-script/copy-slides.gs` (in this repo; also lives at `~/aanp-capture/`) —
  `doGet(e)` reads `e.parameter.codes` and runs `copySlides(codes)`, which fetches
  `https://files.aanpdownload.org/2026/Natl/doc/{code}.pdf` per session, skips the ~57794-byte
  AANP placeholder and anything already in the folder (dedup), and copies the rest.
  Folder id is hardcoded (`FOLDER_ID` = "2026 AANP Slides and Notes", **owned by
  sarahspendlovenp@gmail.com**). The Apps Script therefore lives under Sarah's Google account
  (it must run as an account that can write that folder); deploy as Web app, Execute as Me
  (Sarah), Anyone with link. The deployed `/exec` URL is pasted once into the app
  (`state.driveScriptUrl`) on Sarah's device.
- The app now passes the checked session codes (`?codes=26.1.058,...`) so the script copies exactly
  what's checked. Opened directly with no codes, it falls back to every session in `SESSIONS`.
- **Redeploy needed when the .gs changes:** paste the file into script.google.com, Deploy →
  Manage deployments → edit → Version: New version. The `/exec` URL stays the same.

## Next steps / open threads
- [x] Deployed `apps-script/copy-slides.gs` under Sarah's account; verified the `?codes=` path
      copies exactly the passed sessions (17 decks copied; dedup confirmed). The `/exec` URL is
      stored privately in the app (local storage) — intentionally NOT committed to this public repo.
- [x] `/exec` URL delivery solved via `?script=` seed link (no manual paste). Send Sarah the one-tap
      link (see banner at top); opening it once stores the URL on her device.
- [ ] After AANP assigns/updates rooms, re-capture and rebuild (`build_data.py` merges `rooms.json`).

## Reverse-engineering notes (rooms, picks, slides)
Full capture details live in Claude's memory file
`~/.claude/projects/-Users-tom-caswell/memory/aanp-ceu-planner.md` (mitmproxy setup, the Floq S3
content bundle that holds rooms, the `eval.aanp.org/api/conference` endpoint, Sarah's selections).
