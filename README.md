# ChannelFactory

An AI-powered multi-account social media content engine. Each "account" is a fully-defined AI persona that autonomously generates, produces, reviews, and publishes short-form video content across TikTok, Instagram Reels, and YouTube Shorts — with affiliate monetization built in from day one.

**Tagline:** Cursor for content marketing.

---

## What This Actually Does

1. A Claude API call generates a script in the persona's voice
2. ElevenLabs converts the script to audio (persona's voice)
3. fal.ai (Kling v1 pro ai-avatar) generates a lip-synced talking-head video from a single avatar image + audio
4. A Telegram bot sends the video to the human operator for review
5. Operator approves (publish) or sends voice/text feedback (iterate)
6. Postiz publishes to TikTok / Instagram / YouTube Shorts

One n8n workflow. Four nodes. All logic in Python.

---

## Current Status

| Component | Status | Notes |
|-----------|--------|-------|
| System architecture | ✅ Locked | See `docs/system-design.md` |
| Dr. Wei persona | ✅ Complete | `accounts/dr-wei/character-spec.json` |
| Avatar image | ✅ Uploaded | Permanent fal.ai URL in character-spec.json |
| Kling lip-sync test | ✅ Passed | Face ✓ Lip sync ✓ Body movement ✓ No artifacts |
| ElevenLabs voice | 🔲 Pending | Need Creator plan — voice selection next |
| pipeline.py | 🔲 Not built | Next after voice |
| n8n workflow | 🔲 Skeleton only | `pipeline/n8n/` |
| Telegram review bot | 🔲 Not built | After pipeline.py |
| Postiz deployment | 🔲 Not built | Self-hosted Docker |
| VPS (Hetzner) | 🔲 Not deployed | After pipeline works locally |

**Active account:** Dr. Wei (sleep optimization)
**V2 accounts (not started):** rabbi, swiss-banker, elite-insider

---

## The Pipeline (Single-Clip Architecture — LOCKED)

```
CRON / Manual Trigger (n8n)
        ↓
pipeline.py
  1. Claude API → script (Dr. Wei system prompt from character-spec.json)
  2. ElevenLabs API → full audio file (one call, one file)
  3. fal.ai Kling ai-avatar → talking-head video (one call, ~12 min generation)
  4. Telegram bot → sends video to operator for review
        ↓
Operator decision (Telegram inline buttons)
  [Publish] → publish.py → Postiz API → TikTok + Instagram + YouTube Shorts
  [Iterate] → voice note or text → Whisper transcribe → Claude routes to correct stage → re-run
```

**Important:** 3-segment architecture was evaluated and DROPPED. Single 34s clip is accepted by Kling with no quality degradation. No FFmpeg stitching needed.

---

## Validated Technical Findings

| Finding | Value |
|---------|-------|
| Kling endpoint | `fal-ai/kling-video/v1/pro/ai-avatar` |
| Kling input params | `image_url`, `audio_url` |
| fal.ai client method | `fal_client.subscribe_async()` — NOT `run_async()` (wrong host) |
| Generation time (34s video) | ~12 minutes |
| Max audio duration tested | 34s — accepted, no cap hit |
| Video output quality | 22MB MP4, 34s, no artifacts |
| Avatar fal.ai URL | See `accounts/dr-wei/character-spec.json → avatar_fal_url` |
| Test video URL | See `accounts/dr-wei/character-spec.json → kling_test_video` |

---

## Account #1: Dr. Mei Wei

**Persona:** Dr. Mei Wei, 68-year-old Chinese-American retired sleep physician, San Francisco Bay Area.
**Core angle:** 40 years of Western sleep medicine + rediscovering her grandmother's TCM notebooks. Bridges both traditions.
**Voice:** Warm, measured, deliberate. Grandmother energy. First-person clinical observation — never cites studies as primary evidence.
**Platforms:** TikTok (primary) → Instagram Reels → YouTube Shorts
**Monetization path:** Affiliate links (Thorne, Headspace, weighted blankets) → Free newsletter → $47 Sleep Protocol PDF

Full spec: `accounts/dr-wei/character-spec.json`
The `system_prompt` field is injected directly as the Claude API system parameter on every call.

---

## Stack

| Role | Tool | Notes |
|------|------|-------|
| Orchestration | n8n (self-hosted) | 4-node workflow, Docker |
| Script generation | Claude API (`claude-sonnet-4-5`) | Dr. Wei system prompt from character-spec.json |
| Voice synthesis | ElevenLabs API | Creator plan required for API + voice library |
| Video generation | fal.ai — Kling v1 pro ai-avatar | `fal-ai/kling-video/v1/pro/ai-avatar` |
| Human review | Telegram bot | Inline buttons: Publish / Iterate |
| Voice feedback | OpenAI Whisper API | Transcribes operator voice notes |
| Publishing | Postiz (self-hosted) | gitroomhq/postiz-app, Docker |
| Link tracking | Dub.co | One static link per account |
| Affiliate DMs | ManyChat | Comment keyword → auto-DM (Week 3+) |
| Run log | Airtable | Simple, each run = one row |
| Asset storage | Cloudflare R2 | Signed URLs generated at publish time only |

---

## Folder Structure

```
channel-factory/
├── .claude/
│   └── CLAUDE.md                         ← Agent context. Read this first every session.
├── accounts/
│   ├── README.md                         ← Account roster + expansion notes
│   └── dr-wei/                           ← ACTIVE — sleep optimization
│       ├── avatar.jpg                    ← Avatar image (also on fal.ai permanently)
│       ├── character-spec.json           ← SINGLE SOURCE OF TRUTH for Dr. Wei
│       │                                    system_prompt → Claude API system param
│       │                                    avatar_fal_url → skip re-upload
│       │                                    kling_endpoint → confirmed working
│       ├── brand-voice-guidelines.md     ← Voice QA reference
│       ├── hook-library.md               ← Hook templates H1–H7 + body structures B1–B5
│       └── content/                      ← Generated scripts (numbered, ready to produce)
├── docs/
│   ├── system-design.md                  ← Full architecture (v3.0)
│   ├── market-research.md                ← Affiliate programs, validated niches
│   └── signal-layer.md                   ← V2 trend detection (don't build yet)
├── pipeline/
│   └── n8n/
│       ├── docker-compose.yml            ← n8n self-hosted setup
│       ├── .env.example                  ← Required env vars (copy to .env, never commit .env)
│       └── workflows/
│           └── dr-wei-generate-script.json ← n8n workflow export (skeleton)
├── test/
│   ├── test_kling.py                     ← Kling validation script (PASSED)
│   ├── test_elevenlabs.py                ← ElevenLabs validation (needs Creator plan)
│   └── README.md                         ← How to run tests
└── scripts/                              ← Automation scripts (TBD)
```

---

## Environment Variables Required

Copy `pipeline/n8n/.env.example` → `pipeline/n8n/.env` and fill in:

```
FAL_KEY=                    # fal.ai API key — format: uuid:secret
ELEVENLABS_API_KEY=         # ElevenLabs API key (Creator plan required)
ANTHROPIC_API_KEY=          # Claude API key
TELEGRAM_BOT_TOKEN=         # From @BotFather
TELEGRAM_CHAT_ID=           # Your personal Telegram chat ID
POSTIZ_API_KEY=             # After Postiz deployment
AIRTABLE_API_KEY=
AIRTABLE_BASE_ID=
R2_ACCOUNT_ID=              # Cloudflare R2
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=
```

---

## What To Build Next (In Order)

1. **ElevenLabs voice** — Upgrade to Creator plan → pick/clone Dr. Wei voice → save Voice ID to .env
2. **`pipeline.py`** — Single script: Claude → ElevenLabs → fal.ai Kling → save video
3. **Telegram bot** — Send video, receive Publish/Iterate, route feedback
4. **`publish.py`** — Postiz API integration
5. **n8n wiring** — Connect the 4 nodes around pipeline.py
6. **VPS deploy** — Hetzner, Docker, systemd for Telegram bot

---

## Key Rules (Don't Break These)

- **No product CTAs before Day 60** of account age. Trust-building only.
- **No anti-medicine framing.** Never "what Western medicine won't tell you."
- **One idea per video.** Always.
- **Hook before credentials** on TikTok. Never introduce Dr. Wei before the hook fires.
- **Script → hook template first.** Always pick from hook-library.md before generating. Freeform = generic.
- **Lockfile** before any generation run — prevents VPS OOM with concurrent jobs.
