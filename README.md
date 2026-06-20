# Sarah's AANP 2026 CEU Planner

A simple, phone-friendly web app to plan sessions and track CEUs for the **2026 AANP National Conference** (Las Vegas, June 23–27) toward AGACNP board-certification renewal (**75 CE hours**).

**Live app:** https://tom4cam.github.io/aanp-ceu-planner/

## What it does
- **Browse** all 393 real conference sessions. Filter by day, type, content level, free/paid, and recording availability. Search by keyword.
- For each session, choose **Attend Live**, **Watch Recording**, or **Skip** — and fill in the **room number** as AANP announces them.
- **Live Schedule** lays out live picks by day, enforces one-live-per-time-block (flags overlaps), and warns about tight transitions between rooms (helpful with a foot injury 🦶).
- **Recordings** queue everything to watch on-demand after the conference for extra CEUs — no time conflicts.
- **CEU Dashboard** tracks progress toward 75: already-earned credits + planned live + planned recordings + any other/external CEUs. Prominent running total.
- **My Plan** is a concise, print-/PDF-friendly view showing only what you plan to attend or watch, with CEU totals.

## Data & privacy
Everything saves in your browser (localStorage). No accounts, no server. Use **Export / Import** on the Dashboard to back up your plan or move it to another device.

Session data extracted from sessions.aanp.org. Rooms are unpublished at build time and are entered by the user.
