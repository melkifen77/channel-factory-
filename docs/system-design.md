# ChannelFactory — System Design v3.0 (Simplified)

> Last updated: 2026-04-18  
> V1 goal: ONE account (Dr. Wei), prove end-to-end loop, get first conversion.  
> Principle: **the Slack gate is the quality system**. Everything else is glue.

---

## The Pipeline (9 stages, no fluff)

```
[Topic input]  ← manual trigger in n8n
      ↓
[1] Claude API       — script with pre-split segments
      ↓
[2] ElevenLabs API   — 3 audio files (one per segment) + word timestamps
      ↓
[3] fal.ai Kling 3.0 — 3 async video clips (avatar + audio per segment)
      ↓
[4] FFmpeg           — normalize + stitch + burn subtitles
      ↓
[5] Slack gate       — YOU review and approve/reject
      ↓
[6] Postiz           — publish TikTok / Instagram / YouTube Shorts
      ↓
[7] Airtable row     — log run as complete, store post IDs
```

**Orchestration:** n8n (standard mode, SQLite, no Redis).  
**Storage:** Cloudflare R2 (files) + Airtable (run log).  
**Human-in-loop:** Every video reviewed in Slack before publish. This replaces: quality scoring, content policy check, circuit breaker, monitoring digest.

---

## Stage 1: Script Generation

**Input:** `topic` (string), `account_id`  
**Output:** XML with pre-split segments — Claude does the segmentation, no NLP library needed

### What Claude returns
```xml
<script>
  <hook>If you wake at 3am, your liver is trying to tell you something</hook>
  <segment index="1">Western medicine calls it insomnia. In Chinese medicine, we call it the liver clock...</segment>
  <segment index="2">Between 1 and 3am the liver is most active. When it's overloaded, it wakes you up...</segment>
  <segment index="3">I spent 40 years treating patients who couldn't sleep. The ones who healed...</segment>
  <cta_keyword>sleep</cta_keyword>
  <topic_tags>["liver-clock", "tcm", "3am-waking"]</topic_tags>
</script>
```

### System prompt constraints
- Each `<segment>` must be 10–13 seconds when spoken aloud (~30–40 words)
- Total voiceover: 3 segments, under 110 words combined
- End last segment on an insight or observation, not a CTA
- CTA is text overlay added in post — do not include in voiceover

### Files loaded per run
- `accounts/{account_id}/character-spec.json` → `system_prompt` field
- `accounts/{account_id}/hook-library.md` → injected as context
- `accounts/{account_id}/persona-memory.md` → last 10 script summaries (drift prevention)

### No re-prompting. No policy check.
Accept first output. You review the script in the Slack gate anyway.  
Fix bad outputs by improving the system prompt, not by adding retry logic.

### Topic dedup (simple)
Before calling Claude: check Airtable `pipeline_runs` for same `account_id` + `topic` string in last 14 days.  
String match, no hashing. If found → abort with Slack message.

---

## Stage 2: Voice Synthesis

**Call ElevenLabs once per segment** — not one full audio then split.  
Claude already divided the script. Generate 3 independent audio files directly.

```python
for i, segment_text in enumerate(segments):
    audio, timestamps = elevenlabs.generate_with_timestamps(
        text=segment_text,
        voice_id=VOICE_ID,  # 1a0nAYA3FcNQcMMfbddY (Dr. Wei)
        model="eleven_turbo_v2",
        voice_settings={"stability": 0.75, "similarity_boost": 0.85, "style": 0.20}
    )
    save_to_r2(audio, f"runs/{run_id}/segment_{i+1:02d}.mp3")
    save_to_r2(timestamps, f"runs/{run_id}/segment_{i+1:02d}_timestamps.json")
```

**Why per-segment:** Eliminates the entire audio segmentation stage. No spaCy, no pydub splitting,  
no word-timestamp boundary mapping. Each Kling call gets audio generated for exactly that segment.

**Word timestamps** are saved per segment — used later for subtitle generation. No extra API call needed.

---

## Stage 3: Video Generation (Kling 3.0 via fal.ai)

### One-time setup (per account)
Pre-upload avatar image to fal.ai storage. Store the resulting URL in `character-spec.json`.  
**Never pass an external CDN URL to Kling** — it will fail intermittently.

```python
# Run once when setting up an account
fal_avatar_url = fal_client.upload_file("accounts/dr-wei/avatar.jpg")
# Store in character-spec.json → "avatar_fal_url": "https://storage.fal.run/..."
```

### Segment audio: also upload to fal.ai
fal.ai requires audio to be accessible via URL. Upload each segment MP3 to fal.ai before the Kling call.

```python
segment_fal_url = fal_client.upload_file(f"/tmp/{run_id}/segment_01.mp3")
```

### Async generation (run all 3 concurrently)
```python
async def generate_clip(segment_index, audio_fal_url, duration_s):
    return await fal_client.run_async(
        "fal-ai/kling-video/v1.6/lip-sync",
        arguments={
            "image_url": account["avatar_fal_url"],
            "audio_url": audio_fal_url,
            "duration": min(duration_s, 14),  # 1s safety buffer under 15s cap
            "aspect_ratio": "9:16"
        }
    )

clips = await asyncio.gather(
    generate_clip(1, seg1_url, seg1_duration),
    generate_clip(2, seg2_url, seg2_duration),
    generate_clip(3, seg3_url, seg3_duration)
)
```

### Retry (max 3 per segment)
You will look at every video in Slack. Automated quality scoring removed.  
Retry only on: HTTP error, timeout (>20min), or Kling returns a clearly broken response (0-byte file).  
Bad-but-passing clips → you catch them at Slack gate.

### Download clips to R2
`runs/{run_id}/clip_01_raw.mp4`, `clip_02_raw.mp4`, `clip_03_raw.mp4`

---

## Stage 4: FFmpeg — Normalize, Stitch, Subtitle

Everything in one Python script. No Captions.ai for V1.

### Step 1: Normalize all clips to identical spec
```bash
for i in 01 02 03; do
  ffmpeg -i runs/{run_id}/clip_{i}_raw.mp4 \
    -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2" \
    -r 30 -c:v libx264 -profile:v baseline -level 3.1 \
    -c:a aac -ar 44100 -ac 2 -b:v 4000k -b:a 128k \
    runs/{run_id}/clip_{i}_norm.mp4
done
```

### Step 2: Stitch clips
```bash
# Build concat list
printf "file 'clip_01_norm.mp4'\nfile 'clip_02_norm.mp4'\nfile 'clip_03_norm.mp4'" \
  > /tmp/{run_id}/concat.txt

ffmpeg -f concat -safe 0 -i /tmp/{run_id}/concat.txt \
  -c:v copy -c:a copy \
  runs/{run_id}/stitched.mp4
```

### Step 3: Generate subtitles from ElevenLabs timestamps
No Captions.ai. No external API. We already have word-level timestamps from ElevenLabs.  
A 30-line Python function converts them to `.ass` subtitle format:

```python
def timestamps_to_ass(timestamps_list, style):
    """
    timestamps_list: merged list from all 3 segment timestamp JSONs
                     with absolute timing (offset each segment by its start time)
    style: from accounts/{account_id}/caption_style.json
    """
    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, Bold, Alignment, MarginV
Style: Default,{style['font']},{style['size']},&H00FFFFFF,&H00000000,-1,8,80

[Events]
Format: Layer, Start, End, Style, Text
"""
    events = []
    # Group words into 2-3 word chunks for readable subtitle timing
    for chunk in group_words(timestamps_list, max_words=3):
        start = format_ass_time(chunk[0]["start_time"])
        end = format_ass_time(chunk[-1]["end_time"])
        text = " ".join(w["word"] for w in chunk)
        events.append(f"Dialogue: 0,{start},{end},Default,,{text}")
    
    return ass_header + "\n".join(events)
```

### Step 4: Burn subtitles
```bash
ffmpeg -i runs/{run_id}/stitched.mp4 \
  -vf "ass=/tmp/{run_id}/captions.ass" \
  -c:v libx264 -c:a copy \
  runs/{run_id}/final.mp4
```

### Output
`runs/{run_id}/final.mp4` — 1080×1920, H.264, subtitles burned, 25–45s.  
Upload to R2. Generate a signed URL for Slack preview.

**What this replaces:** Captions.ai Edit API (async polling + exponential backoff + 429 handling +  
rate limits + fallback logic). FFmpeg + 30 lines of Python does the job synchronously, for free.

**What's missing vs Captions.ai:** Auto B-roll insertion, zoom punches, color grading.  
These are V2 additions once the core loop is proven. A well-subtitled talking head is enough to test  
whether the persona and hook convert — which is all V1 needs to answer.

---

## Stage 5: Slack Gate

The human review step. This single node replaces: automated quality scoring, content policy checking,  
video validation, circuit breaker, monitoring digest, and shadow ban detection.

### n8n Slack node sends:
```
🎬 New video ready — Dr. Wei
Topic: "3am liver clock"
Hook: "If you wake at 3am, your liver is trying to tell you something"
Duration: 34s | Run: dr-wei-20260418-a3f9b2

[Preview thumbnail]
[▶ Watch video] → signed R2 URL (valid 1h)

✅ Approve → publishes immediately
❌ Reject  → logs to Airtable, pipeline stops
```

### Timeout
If no response within 2 hours → auto-reject, Slack reminder message.  
Don't auto-approve. You need to see every video in V1.

### What you're checking in review
- Face looks realistic (not melting, no artifacts)
- Lip sync acceptable (not perfect, just not distracting)
- Subtitles readable and timed correctly
- Hook landed in first 5 seconds
- No major script issues slipped through

---

## Stage 6: Publishing (Postiz)

### Payload per platform
```json
{
  "type": "now",
  "settings": {
    "TikTok": {
      "caption": "{hook}\n\nComment '{cta_keyword}' and I'll DM you more.\n\n{hashtags}",
      "is_ai_generated": true
    },
    "Instagram": {
      "caption": "{hook}\n\nComment '{cta_keyword}' below. Link in bio.\n\n{hashtags}"
    },
    "Youtube": {
      "title": "{hook}",
      "description": "{voiceover_text}\n\n{hashtags}"
    }
  },
  "media": [{ "url": "{r2_signed_url}" }]
}
```

### Posting time
Hardcoded: 7pm local time. No optimization logic.  
Revisit after 30 posts when you have data to make a decision.

### Hashtags
Single Claude Haiku call after approval (not before — no point generating if rejected):
`"5 hashtags for TikTok sleep niche content about {topic}. JSON array only."`

### Token management
Check token expiry at pipeline start (Stage 0). If any platform token expires within 48h → Slack alert.  
You refresh manually in Postiz UI. No automated refresh for V1. TikTok tokens last 24h with auto-refresh  
via Postiz's built-in OAuth handling — verify Postiz handles this before going live.

---

## Stage 7: Airtable Log

Simple record. No state machine, no dead letter queue, no resume-on-crash.  
If a run fails, you fix it and rerun. At 1-2 posts/day you'll never lose more than one run.

### `pipeline_runs` table (minimal)
| Field | Type | Notes |
|---|---|---|
| `run_id` | Text | `dr-wei-{yyyymmdd}-{uuid8}` |
| `account_id` | Text | |
| `topic` | Text | For dedup lookup |
| `status` | Select | `running / approved / rejected / failed` |
| `stage` | Text | Last stage reached |
| `hook` | Text | For quick reference |
| `tiktok_id` | Text | Post ID after publish |
| `instagram_id` | Text | |
| `youtube_id` | Text | |
| `error` | Long text | What broke, if anything |
| `created_at` | DateTime | |
| `published_at` | DateTime | |

Update the record at: run start, approval, publish, failure.  
That's 4 Airtable writes per run. No polling, no state machine complexity.

---

## Infrastructure

### VPS: Hetzner CX21
2 vCPU, 4GB RAM, 40GB disk. ~€4.5/month.  
Runs: n8n (Docker), Python pipeline scripts, ffmpeg.  
No Redis. No worker processes. Standard n8n SQLite mode.

### Storage: Cloudflare R2
One bucket: `channel-factory`. Free up to 10GB storage, zero egress fees.  
Structure: `runs/{run_id}/` — all intermediates + final.  
Cleanup: delete `*_raw.mp4` and `*_norm.mp4` after successful publish. Keep `final.mp4` 90 days.  
No lifecycle automation for V1 — delete manually or via a monthly cron once you care.

### Account files (VPS local)
```
/app/accounts/dr-wei/
  character-spec.json     ← includes avatar_fal_url
  hook-library.md
  brand-voice-guidelines.md
  persona-memory.md       ← updated after each run
  caption_style.json      ← font, size, color for .ass generator
```

### `.env` (VPS, never committed)
```
ANTHROPIC_API_KEY=
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID_DR_WEI=1a0nAYA3FcNQcMMfbddY
FAL_KEY=
AIRTABLE_API_KEY=
AIRTABLE_BASE_ID=
POSTIZ_API_KEY=
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET=channel-factory
SLACK_WEBHOOK_URL=
```

---

## n8n Workflow Structure

4 nodes. That's it.

```
[Manual Trigger]  ← input: {account_id, topic}
      ↓
[Execute Command]
  python /app/pipeline.py \
    --account {{ $json.account_id }} \
    --topic "{{ $json.topic }}"
  # Runs stages 1–4, sends video to Telegram bot at the end
  # Outputs: run_id (used by next node)
      ↓
[Wait node]  ← n8n waits for webhook callback from Telegram bot
  Telegram bot handles the full review + iteration loop independently
  When user taps ✅ Publish → Telegram bot fires webhook back to n8n with run_id
  Timeout: 24h → auto-discard
      ↓
[Execute Command]  ← only fires on ✅ from Telegram
  python /app/publish.py \
    --account {{ $json.account_id }} \
    --run-id {{ $json.run_id }}
  # Calls Postiz API, updates Airtable with post IDs
```

**Telegram bot runs as a separate persistent process** (`telegram_bot.py`) on the VPS.  
It handles the full review/iterate loop independently of n8n.  
When the user approves, it fires a webhook back to n8n to trigger publish.  
n8n handles: scheduling, triggering pipeline, waiting for approval signal, triggering publish.  
Python handles: all API calls, FFmpeg, Telegram UX, iteration routing.

---

## Python Script Structure

```
/app/
  pipeline.py         ← stages 1–4 (script → voice → video → stitch → send to Telegram)
  publish.py          ← stage 6 (Postiz + Airtable update), triggered by n8n webhook
  telegram_bot.py     ← persistent bot process: review UI, iterate loop, webhook to n8n
  utils/
    claude.py         ← Claude API wrapper
    elevenlabs.py     ← ElevenLabs wrapper
    kling.py          ← fal.ai async wrapper
    ffmpeg.py         ← normalize, stitch, subtitle burn
    subtitles.py      ← ElevenLabs timestamps → .ass format
    r2.py             ← upload/download/signed URL (URL generated fresh at publish time)
    airtable.py       ← read/write pipeline_runs
    telegram.py       ← send video, inline buttons, receive callbacks
    whisper.py        ← transcribe voice feedback (OpenAI Whisper API)
  accounts/
    dr-wei/
      character-spec.json   ← includes avatar_fal_url, is_ai_generated: true (permanent)
      hook-library.md
      persona-memory.md     ← updated after each run with feedback patterns
      caption_style.json
```

`pipeline.py` runs top to bottom. `telegram_bot.py` runs as a persistent systemd service on VPS.  
On iterate: pipeline.py is called again with `--extra-context "{feedback}"` flag. Full rerun. Simple.

### VPS process collision fix (lockfile — 3 lines)
```python
# Top of pipeline.py
import fcntl, sys
lock = open("/tmp/pipeline.lock", "w")
try:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    sys.exit("Pipeline already running. Try again shortly.")
```
If a run is in progress, any new trigger exits immediately with a Slack/Telegram message.

### R2 URL fix (generate at publish time, not creation time)
```python
# In publish.py — NOT in pipeline.py
r2_url = r2.generate_signed_url(
    key=f"runs/{run_id}/final.mp4",
    expires_in=3600  # 1 hour — plenty for Postiz to fetch and upload
)
postiz.publish(video_url=r2_url, ...)
```
The video sits safely in R2. The signed URL is only generated the moment publish.py runs.
No expiry risk regardless of how long the Telegram review takes.

---

## What's Cut (and when it comes back)

| Removed | Why | When to add |
|---|---|---|
| Claude Vision quality scoring | Slack gate covers it | V2: when running unattended overnight |
| Motion detection (frame diff) | Rare edge case; you'll see it | V2: same |
| Captions.ai Edit API | FFmpeg .ass is sufficient for V1 | V2: when B-roll + zoom punches matter |
| spaCy segmentation | Claude pre-segments in XML | Never needed |
| Preflight quota checks | Catch on API error instead | V2: 4+ accounts |
| Content policy check | Human review covers it | V2: unattended publishing |
| Token refresh CRON | Manual reminder sufficient | V2: when you can't babysit tokens |
| Account circuit breaker | You'll notice shadow bans manually | V2: multi-account |
| Daily monitoring CRON | Slack gate + Airtable is enough | V2: 4+ accounts |
| Redis / n8n queue mode | 1 account doesn't need it | V2: multi-account |
| Bio link auto-update | Set static Dub.co link, update manually | V2: when conversion volume justifies it |
| ManyChat DM automation | No comments yet to automate | V2: after traction |
| Video validation (ffprobe) | If FFmpeg ran clean, it's fine | Never needed |
| Optimal posting time logic | Hardcode 7pm, revisit with data | After 30+ posts |
| Lifecycle policies on R2 | Delete manually, no volume yet | V2 |

---

## Cost Model

| Stage | Tool | Per Video |
|---|---|---|
| Script gen | Claude Sonnet | ~$0.01 |
| Voice (3 segments) | ElevenLabs Turbo v2 | ~$0.04 |
| Video (3 clips) | Kling via fal.ai | ~$1.05 |
| Hashtags | Claude Haiku | ~$0.00 |
| Storage | Cloudflare R2 | ~$0.01 |
| **Total** | | **~$1.11/video** |

At 1 video/day: ~$34/month. At 2/day: ~$68/month.  
First conversion target: within first 50 posts.

---

## Compliance (non-optional)

**FTC:** Every post with an affiliate link needs `#ad` in caption. Add to account bio: "Content may include affiliate links." Non-negotiable.

**TikTok AI label:** `is_ai_generated: true` in Postiz payload. Required since 2024.

**Music:** `background_music: false` always. Captions.ai (V2) must be configured to not add music.  
Platform music = potential mute/takedown on API-uploaded content.

**TikTok API ToS:** Multi-account automation under one developer app is a ToS grey area.  
V1 with single account + human Slack gate is low risk. Before V2 multi-account: review ToS.

---

## Build Sequence

```
Day 1 — Validate core assumption before building anything
  □ Make 1 ElevenLabs call with a segment of Script #1 → inspect timestamp response format
  □ Upload Dr. Wei avatar to fal.ai → make 1 Kling call with a 40s audio file (single clip, no segmentation)
  □ Watch output: is quality good enough? Does Kling handle 40s or does it degrade?
  □ Decision: if single 40s clip works → drop 3-segment architecture entirely (major simplification)
               if Kling caps at 15s → keep 3-segment architecture as designed
  □ This takes 2 hours and determines 30% of the pipeline complexity

Week 1 — Infrastructure (after Day 1 validation)
  □ Hetzner CX21: Docker, Python 3.11, ffmpeg, n8n
  □ Cloudflare R2: bucket + credentials
  □ Airtable: pipeline_runs table
  □ fal.ai: avatar already uploaded from Day 1
  □ Telegram: create bot via BotFather, store token in .env
  □ Connect existing accounts to Postiz (OAuth — no API approval needed, Postiz handles it)
  □ ManyChat: set up in Week 3 once first posts are live and getting comments

Week 2 — Core scripts
  □ utils/ (claude, elevenlabs, kling, ffmpeg, subtitles, r2, airtable, telegram, whisper, iterate)
  □ pipeline.py (stages 1–4, end to end)
  □ publish.py (Postiz + Airtable update)
  □ Test pipeline.py locally with Script #1
  □ Test Telegram bot: send video, tap iterate, send voice note, verify routing

Week 3 — n8n + first real run
  □ Wire 4-node n8n workflow (Manual Trigger → pipeline.py → Telegram gate → publish.py)
  □ Test full loop: trigger → video → Telegram review → iterate once → approve → publish
  □ Manual Week 1 warmup: post daily, approve everything, watch platform response

Week 4 — Iteration loop tuning + scripts #2 and #3
  □ Run scripts #2 and #3 through full pipeline
  □ Iterate at least once on each to test the feedback routing
  □ Verify ManyChat DM firing on test comment
  □ Verify Dub.co link tracking in dashboard

After first conversion
  □ Add minimal analytics CRON: 48h metrics pull → Claude flags best-performing hook/structure
  □ Update style-template.json based on first 20-post learnings
  □ Activate The Rabbi account
```

---

## Open Questions (need answers before building)

| Question | Why it matters |
|---|---|
| What is the current fal.ai endpoint for Kling 3.0 lip sync? | Endpoint names change — verify at build time |
| Does Kling handle a single 40s audio file well, or does quality degrade past 15s? | Determines whether 3-segment architecture is needed at all |
| Does Captions.ai have a public API or is it waitlist? | Determines V2 timeline for B-roll/zoom punches |
| Which affiliate programs accept sleep content creators? | Impact, HealthTrader, Amazon Associates — confirm approval |

**Not blockers:**
- TikTok/Instagram API approval — Postiz uses its own developer credentials via OAuth. Connect accounts through Postiz UI, done.
- Account warmup — existing aged accounts used, not new. Trust already established.

---

## Stage 5: Review & Iteration Loop (Telegram)

**Tool:** Telegram Bot API  
**Why Telegram, not Slack:** Native video playback, inline buttons, voice messages, works from anywhere on mobile. Slack requires opening links; Telegram plays video inline.

### Bot sends on video ready
```
🎬 Dr. Wei — new video ready
Topic: 3am liver clock
Hook: "If you wake at 3am, your liver is trying to tell you something"
Duration: 34s

[video plays inline in Telegram]

[✅ Publish]   [🔄 Iterate]
```

### On ✅ Publish
Trigger Postiz publish immediately. Log to Airtable. Done.

### On 🔄 Iterate
Bot replies: *"What should change? Send voice note or text."*

You respond — voice note on mobile or typed text. Examples:
- *"the hook is too aggressive, she should sound warmer"*
- *"clip 2 looks stiff, regenerate it"*
- *"subtitles are too small and hard to read"*
- *"redo the whole thing with a softer tone, more grandmother less professor"*

### Iteration: always full rerun with feedback injected
Whisper transcribes voice note → feedback appended to Claude system prompt → full pipeline reruns from Stage 1.

No per-stage routing. No partial reruns. Full rerun costs ~$1.11. You'll iterate at most 2-3 times per video.
The simplicity is worth the $2-3 in extra API spend.

```python
# On iterate:
feedback_note = whisper.transcribe(voice_note_path)
# Append to script gen call:
extra_context = f"\n\nPrevious version was rejected. User feedback: '{feedback_note}'. Adjust accordingly."
# Re-run pipeline.py with extra_context injected into Claude system prompt
```

### Confirmation before rerun
Bot replies with the transcribed feedback: *"Got it: 'hook too aggressive, warmer tone.' Regenerating — confirm?"*
[✅ Yes] [✏️ Edit note]
One extra tap prevents misfires from Whisper mishearing.

### Iteration limit + learning
Max 3 iterations per run. On 3rd rejection → discard, log to Airtable as `needs_rework`.
After each accepted video → Claude appends 1-line summary to `persona-memory.md` noting any feedback that shaped the final version. Recurring patterns get baked into the character spec.

### Telegram bot setup
- `python-telegram-bot` library (well-maintained, async)
- Webhook on Hetzner VPS (n8n can trigger it or it runs as a separate process)
- Bot token from BotFather → stored in `.env`
- One bot per account (or one bot managing all accounts with account label in message)

---

## ManyChat: Comment → DM Automation

Set up before first post. This is the conversion mechanism — not optional.

### Flow
```
User comments "sleep" on any post
    ↓
ManyChat detects keyword trigger
    ↓
Auto-DM: "Hi! Dr. Wei here 🌿 Here's the resource I mentioned: {dub_co_link}
          Sweet dreams — and let me know if you have questions."
    ↓
Dub.co tracks click → conversion attributed to video via UTM
```

### Setup (2 hours, do before first post)
1. ManyChat.com → connect TikTok + Instagram accounts
2. Create keyword trigger: "sleep" (or whatever `cta_keyword` is for that account)
3. Write DM template with Dub.co link
4. Test with a friend's account

### One static Dub.co link per account
Update the link manually when the affiliate offer changes. Don't automate bio updates for V1.  
`utm_source=tiktok&utm_medium=bio&utm_campaign=dr-wei` — consistent across all posts.  
Individual video attribution handled by asking ManyChat to log which post triggered the DM (available in ManyChat analytics).
