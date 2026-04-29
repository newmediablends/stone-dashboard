# KAIROS — Current Status

_Last updated: 2026-04-26 | v0.5.0_

**Live at:** https://kairos-ai.app
**Repo:** https://github.com/newmediablends/proofd-app
**Co-founders:** Mike Baird + Sakina Groth
**Stack:** Next.js 16 + Supabase + Apollo + Resend + Vercel

---

## Current State: LIVE — BETA

Version 0.4.1 is deployed. Core product is functional end-to-end:
- Landing page with beta signup
- Branded magic link invite flow
- Dashboard with pipeline tracking, company scanner, outreach drafts
- Full brand system (KAIROS identity, email templates, login page)

---

## What's Shipped (Recent)

| Version | Date | What |
|---|---|---|
| 0.4.1 | 2026-04-23 | Dashboard brand alignment — sharp buttons, PipelineCards (4rem Cinzel glow + tooltips), color scale pass (#364153→#9aa1af), Cinzel tagline, KAIROS casing |
| 0.4.0 | 2026-04-23 | Login page brand lockup (inscription + wordmark + tagline + closing statement w/ animation); Supabase auth template rewrite; hamburger desktop fix |
| 0.3.9 | 2026-04-23 | Email brand pass (all 5 Resend templates); Sign In nav link; mobile menu rebuild |
| 0.3.8 | 2026-04-23 | Email typography pass; landing page nav + spacing fixes |
| 0.3.0–0.3.7 | 2026-04-23 | Landing page, design system, mobile polish, brand identity |
| 0.1.0–0.2.0 | 2026-04-22 | Foundation — auth, scoring engine, Apollo, outreach, templates |

Full history: `KAIROS-Dev-Log.md`

---

## Access Flow (How Beta Users Get In)

1. Visitor signs up at kairos-ai.app → confirmation email fires + Mike gets alert
2. Mike adds email to `ALLOWED_EMAILS` in Vercel (NO Sensitive flag — recreate if needed so list stays visible)
3. Mike goes to `/admin` → enters email → Send Invite → branded magic link fires via Resend
4. User clicks link → `/login` → auth callback → `/dashboard`

---

## Priority 1 — Before Expanding Beta

- [x] **Rotate Resend API key** (MJB-33) — completed 2026-04-26
- [x] **Test invite + re-login flow** (MJB-29) — completed 2026-04-26. PKCE confirmed clean.
- [ ] **Test email templates in real clients** (MJB-37) — Gmail web, Gmail iOS, Apple Mail, Outlook

## Priority 2 — Product

- [ ] Signal digest email — weekly Vercel cron (MJB-30) — template built at `lib/emails/signal-report.ts`
- [ ] Auto-scan cron (MJB-31)
- [ ] Saved search criteria → Supabase (currently localStorage)
- [ ] ALLOWED_EMAILS → Supabase table (removes Vercel redeploy requirement per user)

---

## "Log It" Protocol — Always 4 Steps

When Mike says "log it" after any dev work:
1. **Dev Log** — bump version, add shipped row to `KAIROS-Dev-Log.md`
2. **GitHub** — confirm push to origin main
3. **Linear** — create issue (API key in `.env.local`, team ID `1a06ece1-ec8e-45b8-b342-42e57fbd5fa2`)
4. **PRD** — append to Google Doc `1uyTpDjMXhCP9Rg7WOYELbobu_Dq8Mcz6JrLiZOMYv9I`

All 4, every time.

---

## Key Links

| Resource | Link |
|---|---|
| Live app | https://kairos-ai.app |
| GitHub | https://github.com/newmediablends/proofd-app |
| Linear | https://linear.app/mjbaird-projects/team/MJB/active |
| PRD (Google Doc) | https://docs.google.com/document/d/1uyTpDjMXhCP9Rg7WOYELbobu_Dq8Mcz6JrLiZOMYv9I/edit |
| Codebase | `/Users/mikebairdm4mini/Desktop/proofd-app/` |

---

## Next Step
**What:** Phase 1 code sync — branch `design/token-reconciliation`, ticket MJB-46. Apply locked design tokens to codebase. Then fix Resend env vars in Vercel so email flow works. Both blocking beta expansion.
**Why it's 10x:** Design is locked. Until the code matches, every new user sees a misaligned product. Resend fix is a 10-min Vercel env var add — don't let it stay broken.
**Due:** This week
