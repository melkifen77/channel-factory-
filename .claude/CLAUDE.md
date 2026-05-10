# ChannelFactory — Agent Context

Read this file completely at the start of every session before touching anything.

---

## What This Is

An AI-powered multi-account social media content engine. Each account is an AI persona that autonomously generates, produces, reviews, and publishes short-form video with affiliate monetization.

**One sentence:** Claude writes the script, ElevenLabs speaks it, Kling animates it, Telegram reviews it, Postiz publishes it.

---

## Current Build State

| Item | State |
|------|-------|
| Architecture | ✅ Locked — do not redesign |
| Dr. Wei persona | ✅ Complete — `accounts/dr-wei/character-spec.json` |
| Avatar on fal.ai | ✅ Permanent URL in character-spec.json |
| Kling test | ✅ Passed — 34s clip, all quality checks green |
| ElevenLabs voice | 🔲 Pending — need Creator plan + voice selection |
| pipeline.py | 🔲 Next task |
| Telegram bot | 🔲 After pipeline.py |
| publish.py | 🔲 After Telegram bot |
| n8n workflow | 🔲 Skeleton exists, needs pipeline.py first |
| VPS / Postiz | 🔲 After local pipeline works end-to-end |

---

## The Pipeline — LOCKED ARCHITECTURE

```
n8n CRON or Manual Trigger
  → pipeline.py
      1. Claude API  →  script text
      2. ElevenLabs  →  audio .mp3 (one file, full script)
      3. fal.ai Kling ai-avatar  →  .mp4 video (~12 min)
      4. Telegram bot  →  sends video to operator
  → Operator: [Publish] or [Iterate + feedback]
      [Publish] → publish.py → Postiz API → TikTok / Instagram / YouTube Shorts
      [Iterate] → Whisper transcribes → Claude routes stage → re-run from that stage
```

### What was decided and why

| Decision | Rationale |
|----------|-----------|
| Single clip (not 3 segments) | Kling accepted full 34s audio. No stitching needed. Simpler. |
| fal.ai Kling over HeyGen | Tested and validated. HeyGen not used. |
| Telegram over Slack | Telegram plays video inline on mobile. |
| Iteration = full re-run from routed stage | Clean. No partial state to manage. |
| n8n = scheduling + Telegram only | All logic lives in Python. n8n has 4 nodes. |
| No spaCy, no pydub | Dropped with 3-segment architecture. |
| No Captions.ai in V1 | FFmpeg .ass subtitles from ElevenLabs timestamps if needed. |
| Lockfile before each run | Prevents OOM on VPS with concurrent jobs. |

---

## Validated API Details — Use These, Don't Guess

```python
# Kling lip sync
ENDPOINT = "fal-ai/kling-video/v1/pro/ai-avatar"
# Input: image_url, audio_url
# Use subscribe_async() — NOT run_async() (run_async hits fal.run which gives 404)

result = await fal_client.subscribe_async(
    "fal-ai/kling-video/v1/pro/ai-avatar",
    arguments={"image_url": AVATAR_URL, "audio_url": AUDIO_URL},
    with_logs=True,
    on_queue_update=lambda u: print(u),
)
video_url = result["video"]["url"]

# Generation time: ~12 minutes for 34s video
# Avatar permanent URL: see character-spec.json → avatar_fal_url (already uploaded, reuse it)
```

```python
# ElevenLabs (once Creator plan active)
# Voice ID: TBD — save to .env as ELEVENLABS_VOICE_ID
# Use word-level timestamps for subtitle generation
```

```python
# Claude API — Dr. Wei script generation
# System prompt: character-spec.json → system_prompt field (inject verbatim)
# User turn prefix: character-spec.json → context_injection_template (fill fields, prepend to request)
```

---

## Account #1: Dr. Mei Wei

- **Full name:** Dr. Mei Wei (NOT James Wei — old placeholder, ignore it)
- **Age:** 68, Chinese-American, retired sleep physician, SF Bay Area
- **Core tension:** 40 years dismissing her grandmother's TCM → patient she couldn't help → opened the notebooks → spent 20 years figuring out the mechanism
- **Voice:** Warm, measured, grandmother energy. First-person clinical observation. Never cites studies as primary evidence — patient observation IS the evidence.
- **System prompt:** `accounts/dr-wei/character-spec.json → system_prompt` — inject as Claude API `system` param verbatim
- **Avatar:** `accounts/dr-wei/avatar.jpg` — also at `character-spec.json → avatar_fal_url` (permanent, skip re-upload)

### Content Rules
- Hook FIRST on TikTok. Never self-intro before hook.
- One idea per video. Always.
- Always pick a hook template from `hook-library.md` before generating. Never freeform.
- No product CTAs before Day 60.
- Forbidden: "What Western medicine won't tell you", miracle claims, detox language, passive voice.

### Monetization Path
1. Days 1–60: Trust only. No CTAs.
2. Days 61–90: Free newsletter signup ("Dr. Wei's Weekly Sleep Brief")
3. Month 3+: $47 Sleep Protocol PDF + affiliate links (Thorne magnesium 20%, Headspace 20%, weighted blankets 15%)

---

## Script Generation — Always Follow This Order

1. Pick signal/topic
2. Open `accounts/dr-wei/hook-library.md` → select hook template H1–H7
3. Select body structure B1–B5 using the mapping table in that file
4. Call Claude API with:
   - `system` = `character-spec.json → system_prompt`
   - `user` = filled `context_injection_template` + actual request
5. Output: 3–5 hook variants + full script + caption

Skipping step 2 = generic content. Templates + persona = differentiated content.

---

## Folder Map

```
.claude/CLAUDE.md                    ← THIS FILE
accounts/dr-wei/
  character-spec.json                ← Single source of truth for Dr. Wei
  avatar.jpg                         ← Avatar image
  hook-library.md                    ← Hook + body templates (use before every script)
  brand-voice-guidelines.md          ← Voice QA
  content/                           ← Generated scripts ready for production
docs/system-design.md                ← Full architecture (v3.0)
docs/market-research.md              ← Affiliate programs + content angles
docs/signal-layer.md                 ← V2 trend detection (DO NOT BUILD YET)
pipeline/n8n/                        ← n8n Docker setup + workflow skeleton
test/test_kling.py                   ← Validated Kling test (already passed)
test/test_elevenlabs.py              ← ElevenLabs test (needs Creator plan)
```

---

## What To Build Next — In Strict Order

### Step 1: ElevenLabs voice (blocked on Creator plan upgrade)
- Upgrade to Creator plan ($22/mo)
- Browse voice library OR use Voice Design with this prompt:
  `Native English, subtle Asian-American cadence. Female, 65–72. Excellent audio quality. Persona: wise retired sleep physician. Emotion: warm, calm, quietly authoritative. Smooth, slightly lower-pitched voice, measured unhurried pacing, natural pauses, clear emphasis.`
- Save Voice ID to `.env` as `ELEVENLABS_VOICE_ID`

### Step 2: pipeline.py
Build a single script that:
- Accepts a topic/hook direction as input
- Calls Claude API with Dr. Wei system prompt → gets script
- Calls ElevenLabs with Voice ID → saves audio to temp file
- Calls fal.ai Kling ai-avatar → polls until done → downloads video
- Saves video to R2 or local
- Returns video file path

### Step 3: Telegram review bot
- `utils/telegram.py` — send video with inline buttons [✅ Publish] [🔄 Iterate]
- On Iterate: accept voice note or text → Whisper → Claude route → re-run pipeline.py from routed stage
- Max 3 iterations per run. Feedback patterns → appended to persona-memory.md

### Step 4: publish.py
- Postiz API integration
- Pull R2 signed URL at publish time (not before)
- Post to TikTok + Instagram + YouTube Shorts
- Log run to Airtable

### Step 5: n8n wiring
- Node 1: Manual Trigger or CRON
- Node 2: Execute Command → `python3 pipeline.py --topic "..." --hook H3`
- Node 3: Wait (Telegram bot handles this async)
- Node 4: Execute Command → `python3 publish.py --run-id ...`

### Step 6: VPS deploy
- Hetzner CX21 (2 vCPU, 4GB RAM)
- Docker: n8n + Postiz
- systemd: Telegram bot (persistent process)
- Cloudflare R2 for video storage

---

## Environment Variables

All in `pipeline/n8n/.env` (never commit — gitignored):

```
FAL_KEY=                     # format: uuid:hex
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=         # Set after voice selection
ANTHROPIC_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
POSTIZ_API_KEY=
AIRTABLE_API_KEY=
AIRTABLE_BASE_ID=
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=
```

---

## Multi-Account Architecture (V2+)

Pipeline is account-agnostic. New account = new `accounts/<name>/character-spec.json` + Postiz social connections.
Pending V2 accounts: `rabbi` (personal finance), `swiss-banker` (wealth), `elite-insider` (elite mindset).
Do not start V2 until Dr. Wei is posting and converting.

---

## Compliance (Non-Negotiable)

- `character-spec.json → compliance.is_ai_generated = true` — permanent
- TikTok AI label: required on every video
- YouTube altered content disclosure: required
- Caption: `#AIGenerated` appended always
- Bio: "AI-generated content. May include affiliate links."
