# ChannelFactory — Claude Code Project Context

## What This Is
An AI-powered multi-account niche social media content engine. The system autonomously runs niche content accounts across platforms — handling ideation → production → publishing → analytics → optimization. Tagline: "Cursor for marketing."

**Two goals per account:**
1. Distribution asset — build audience, redirect to newsletter/product
2. Monetized channel — affiliate revenue

**Success metric: Conversions only.** Affiliate purchases, newsletter signups. Not views or followers.

---

## Current Status
- ✅ Market research complete (see `docs/market-research.md`)
- ✅ System architecture designed (see `docs/system-design.md`)
- ✅ First account (Dr. Wei) fully defined (see `accounts/dr-wei/`)
- 🔲 Postiz deployment (next)
- 🔲 n8n workflow setup (next)
- 🔲 HeyGen API integration
- 🔲 First content pipeline test

---

## Architecture (Read `docs/system-design.md` for full detail)

```
n8n (orchestration) → Claude API (Dr. Wei persona) → HeyGen + ElevenLabs (production) → Postiz (publishing) → Analytics feedback loop
```

**Key decision:** ElizaOS is NOT used for orchestration (wrong paradigm — reactive, not pipeline). n8n is the workflow engine. ElizaOS is reserved for Phase 3 comment/DM engagement layer.

**Stack:**
- Orchestration: n8n (self-hosted)
- Persona/content generation: Claude API with character spec as system prompt
- Avatar video: HeyGen API (stock actor)
- Voiceover: ElevenLabs API
- Carousels: Canva Connect API
- Publishing: Postiz (self-hosted, gitroomhq/postiz-app)
- Link tracking: Dub.co
- Analytics: Airtable + Postiz analytics API

---

## Account #1: Dr. Wei (Sleep Optimization)

**Persona:** Dr. James Wei, 68-year-old Chinese-American retired sleep physician.
**Origin story:** Grandmother (Wei Mingzhu) was TCM herbalist in Guangzhou. Dismissed for 30 years of Western practice. A patient he couldn't help led him to open her notebooks.
**Angle:** Ancient TCM wisdom + modern sleep science, from a physician who bridges both.
**Platforms:** TikTok → Instagram → YouTube Shorts
**Monetization:** Thorne (magnesium, 20%), Weighting Comforts (blankets, 15%), Headspace (app, 20%) + others
**End-state:** Free newsletter → $47 Sleep Protocol PDF

Full character spec: `accounts/dr-wei/character-spec.json`
Brand voice guidelines: `accounts/dr-wei/brand-voice-guidelines.md`

---

## Folder Structure

```
channel-factory/
├── .claude/
│   ├── CLAUDE.md                    ← You are here
│   └── brand-voice-guidelines.md   ← Dr. Wei guidelines (for /enforce-voice)
├── accounts/
│   ├── README.md                    ← Account roster + expansion strategy
│   ├── dr-wei/                      ← ACTIVE — sleep optimization
│   │   ├── character-spec.json      ← Full persona + Claude API system prompt
│   │   ├── brand-voice-guidelines.md
│   │   ├── hook-library.md          ← Hook templates + body structures + first 10 scripts
│   │   └── content/                 ← Generated content pieces (future)
│   ├── rabbi/                       ← PENDING V2 — personal finance
│   │   └── character-spec.json
│   ├── swiss-banker/                ← PENDING V2 — wealth preservation
│   │   └── character-spec.json
│   └── elite-insider/               ← PENDING V2 — elite financial mindset
│       └── character-spec.json
├── docs/
│   ├── system-design.md             ← Full architecture document
│   ├── market-research.md           ← Dr. Wei validated research + affiliate products
│   └── signal-layer.md             ← V2 early trend detection system design
├── pipeline/                        ← n8n workflow configs (future)
├── scripts/                         ← Automation scripts (future)
└── README.md
```

---

## Build Sequence

**Phase 1 (Weeks 1–4):**
1. Deploy Postiz (Docker) + connect TikTok, Instagram, YouTube accounts
2. Deploy n8n (self-hosted)
3. Build: n8n CRON → Claude API (Dr. Wei system prompt) → log to Airtable
4. Integrate HeyGen API → automate video production
5. Add Slack human-review gate before Postiz publishes
6. End-to-end test: brief → video → Slack review → Postiz publish

**Phase 2 (Weeks 5–10):** Canva carousel format + UTM tracking + analytics feedback loop

**Phase 3 (Month 3+):** Second account launch + ElizaOS engagement layer + auto-approval

---

## Key Files to Read Before Starting Any Session

1. `accounts/dr-wei/character-spec.json` — the Dr. Wei system prompt lives in `system_prompt` field
2. `accounts/dr-wei/hook-library.md` — use this before generating any script; pick hook template + body structure first
3. `docs/system-design.md` — full architecture, all API integration patterns
4. `docs/market-research.md` — affiliate programs to join, content angles, competitive landscape
5. `docs/signal-layer.md` — V2 component; read to understand the future direction but don't build yet

## Script Generation Protocol

Every script must follow this sequence — no exceptions:

1. Select a signal / topic (manually in V1)
2. Open `accounts/dr-wei/hook-library.md`
3. Choose a hook template (H1–H7) that fits the topic
4. Choose a body structure (B1–B5) using the mapping table
5. Pass to Claude API with `dr-wei/character-spec.json` system prompt
6. Output: hook variants (3–5) + full script + caption

Never generate content without first selecting a hook template. Generating from scratch = generic content. Recombining proven templates = high-retention content.

## Multi-Account Architecture

The pipeline is account-agnostic. Adding a new account = new character spec + Postiz integration.
Active: `dr-wei` only. Pending V2: `rabbi`, `swiss-banker`, `elite-insider`.
See `accounts/README.md` for launch sequencing.

---

## Important Constraints

- **No Amazon Associates** for supplements (1–2% commission, not worth it). Use DTC brands.
- **No product CTAs before Day 60** of account age. Trust-building phase.
- **No anti-medicine framing** ("what Western medicine won't tell you" — forbidden). Use instead: "what took me 40 years to understand."
- **One idea per video.** Always.
- **Hook before credentials** on TikTok. Never introduce Dr. Wei before the hook fires.


---

## Architecture Update — v3.0 (2026-04-18)

### Review & Iteration: Telegram (not Slack)
Human review happens via Telegram bot, not Slack. Telegram plays video inline on mobile.
- ✅ Publish button → trigger Postiz immediately
- 🔄 Iterate button → user sends voice note or text feedback → Whisper transcribes → Claude routes to correct stage for re-run
- Max 3 iterations per run. Recurring feedback patterns → appended to persona-memory.md

### Iteration routing logic
Claude classifies user feedback into: SCRIPT / VOICE / CLIP (index) / SUBTITLES / FULL
Returns JSON with stage(s) to re-run and specific instruction. Pipeline resumes from that stage.

### Conversion funnel: ManyChat (set up BEFORE first post)
Comment keyword trigger (e.g. "sleep") → auto-DM with Dub.co affiliate link.
One static Dub.co link per account. No per-post bio automation needed.

### Clip variation is intentional
Kling generates independent clips per segment — position/background/prop changes between cuts
are treated as editing variety, not bugs. Character FACE consistency maintained via consistent
source avatar image. IP-Adapter/ComfyUI available as fallback if needed.

### Video engine: Kling 3.0 via fal.ai (confirmed)
3 segments × (ElevenLabs audio → Kling clip) → FFmpeg normalize + stitch + burn .ass subtitles
No Captions.ai for V1. No automated quality scoring — Telegram review covers it.

### n8n workflow: 4 nodes
Manual Trigger → Execute Command (pipeline.py) → Telegram bot (wait for approval) → Execute Command (publish.py)
All logic in Python. n8n handles scheduling and Telegram integration only.

### Key files added to pipeline
- `utils/telegram.py` — bot send/receive, inline buttons, voice message download
- `utils/whisper.py` — transcribe voice feedback (OpenAI Whisper API)
- `utils/iterate.py` — Claude feedback routing, stage re-run orchestration

## Kling Test Results (April 19, 2026)
- Endpoint: fal-ai/kling-video/v1/pro/ai-avatar (NOT v1.6/lip-sync — that doesn't exist)
- Full 34s clip: ACCEPTED — no duration cap
- Face quality: PASS — matches avatar
- Body movement: PASS — natural head/shoulder motion
- Lip sync: PASS — good enough for production
- Artifacts: NONE
- Generation time: ~12 minutes for 34s video → plan scheduling accordingly

## Architecture Decision: SINGLE CLIP
3-segment architecture is DROPPED. Pipeline is:
  Script (Claude) → Full audio (ElevenLabs, one call) → Single video (Kling ai-avatar, one call) → Telegram review → Postiz publish
No FFmpeg stitching. No segment splitting. No spaCy.
