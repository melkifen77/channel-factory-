# ChannelFactory — System Design
**Version:** 0.1 | **Date:** April 10, 2026 | **Status:** Pre-build

---

## 0. Critical Architecture Decision First

**ElizaOS is NOT the right orchestration layer for this system.**

ElizaOS is a reactive agent framework — it listens for messages, mentions, and events, then responds. That's the wrong paradigm for a content production engine, which is fundamentally *proactive and scheduled* (brief → produce → publish → measure → repeat).

**The right tool for pipeline orchestration is n8n** (open-source, self-hostable). It's built for exactly this: scheduled triggers, multi-step workflows, API integrations, human-in-the-loop gates, and conditional routing.

**Where ElizaOS belongs:** Phase 3 — building an interactive engagement layer where Dr. Wei autonomously responds to comments, DMs, and audience interactions.

**Where the Dr. Wei "character" lives:** A well-crafted system prompt + Claude API. The character file concept from ElizaOS is valuable as a *document* — implemented as a JSON character spec that feeds Claude API calls.

---

## 1. What We're Actually Building

```
"Cursor for marketing" — an autonomous system that:

  [IDEATION]        [PRODUCTION]        [PUBLISHING]        [OPTIMIZATION]
  Brief → Script → Format Route → Video/Carousel/Text → Postiz → Analytics → Repeat
                                                              ↑
                                                     Conversion tracking
                                                     feeds back to ideation
```

**Two loops:**
1. **Content Loop (daily):** Generates and publishes 1–3 pieces per platform per day
2. **Optimization Loop (weekly):** Analyzes performance signals, adjusts content strategy

**One success metric:** Affiliate conversions + newsletter signups. Not views.

---

## 2. Full Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CONTROL PLANE                            │
│                   n8n (Self-hosted)                             │
│                                                                 │
│  Trigger → Brief → Script → Route → Produce → Review → Publish │
│       ↑                                                    │    │
│       └──────────── Weekly Optimization Loop ──────────────┘    │
└─────────────────────────────────────────────────────────────────┘
           │              │              │              │
           ▼              ▼              ▼              ▼
   ┌──────────────┐ ┌──────────┐ ┌──────────────┐ ┌──────────────┐
   │   PERSONA    │ │PRODUCTION│ │  PUBLISHING  │ │  ANALYTICS   │
   │    LAYER     │ │  LAYER   │ │    LAYER     │ │    LAYER     │
   │              │ │          │ │              │ │              │
   │ Claude API   │ │  HeyGen  │ │   Postiz     │ │Postiz API    │
   │ + Dr. Wei    │ │ElevenLabs│ │  (self-host) │ │UTM tracking  │
   │ system prompt│ │  Canva   │ │  /public/v1  │ │Airtable      │
   │ + char. JSON │ │  Kling   │ │  /posts API  │ │ClickBank API │
   └──────────────┘ └──────────┘ └──────────────┘ └──────────────┘

   ┌──────────────────────────────────────────────────────────────┐
   │                    PHASE 3 (FUTURE)                          │
   │          ElizaOS — Interactive Engagement Layer              │
   │   Auto-responds to comments, DMs, mentions as Dr. Wei        │
   └──────────────────────────────────────────────────────────────┘
```

---

## 3. Component Deep Dive

### 3.1 Control Plane: n8n

**Why n8n over alternatives:**
| | n8n | Zapier | Make | Airflow |
|---|---|---|---|---|
| Self-hostable | ✅ | ❌ | ❌ | ✅ |
| AI nodes built-in | ✅ | Partial | Partial | ❌ |
| Code nodes (JS/Python) | ✅ | ❌ | Limited | ✅ |
| Cost at scale | Free (self-host) | $$$ | $$ | Free |
| Human-in-loop gates | ✅ | ❌ | ❌ | ✅ |

**Core workflows to build (in order):**

```
Workflow 1: Daily Content Trigger
  CRON (9am) → Generate Brief → Generate Script → Route to Format
                                                          │
                               ┌──────────────────────────┤
                               │                          │
                          Talking Head               Carousel
                          (HeyGen + EL)            (Canva API)
                               │                          │
                               └─────────── Postiz API ───┘

Workflow 2: Human Review Gate
  Content ready → Slack notification → Wait for approval
  → Approved → Postiz schedule
  → Rejected → Regenerate with feedback

Workflow 3: Analytics Feedback (weekly, Sunday)
  Poll Postiz analytics → Poll UTM affiliate data → Score content
  → Generate "what worked" brief → Seed into next week's ideation
```

---

### 3.2 Persona Layer: Dr. Wei Character Spec

**Format:** JSON character file at `accounts/dr-wei/character-spec.json`
**Runtime:** Claude API with `system` parameter

The `system_prompt` field is injected into every Claude API call as the `system` parameter. The `context_injection_template` is injected in the `user` turn before the content request.

---

### 3.3 Production Layer

**Format routing logic (n8n decision node):**

```
Script → Analyze content type
  │
  ├── Personal story / Explainer → Talking Head Video (HeyGen + ElevenLabs)
  ├── Tutorial / How-to with steps → Carousel (Canva API)
  ├── Quick tip / Hook-first → Short talking head or text post
  └── Product recommendation → Talking head with B-roll
```

**Talking Head Video (primary format):**
```
Script → ElevenLabs API (voice) → HeyGen API (lip-sync avatar) → MP4
       → Optional: B-roll insertion
       → Final assembly → Upload to Postiz via /public/v1/upload-from-url
```

**Key decisions on production tools:**

| Tool | Use | API? | Cost model |
|---|---|---|---|
| HeyGen | Avatar video generation | ✅ REST | Per credit |
| ElevenLabs | Voiceover | ✅ REST | Per character |
| Canva | Carousels | ✅ Connect API | Per org/month |
| Kling | AI animation / B-roll | ✅ | Per generation |

**MoneyPrinterTurbo reference:** Open-source project (55K GitHub stars) at `harry0703/MoneyPrinterTurbo`. The subtitle generation, B-roll timing, and script chunking logic are directly applicable. Don't rebuild what's already proven.

---

### 3.4 Publishing Layer: Postiz

**Why Postiz:**
- Only open-source scheduler with a proper programmatic API designed for agents
- 28+ platforms natively including TikTok, Instagram, YouTube
- Temporal-based scheduling (reliable, distributed, retries automatically)
- Multi-account native

**API integration pattern:**

```typescript
// Step 1: Upload media
const media = await fetch('https://postiz.internal/public/v1/upload-from-url', {
  method: 'POST',
  headers: { Authorization: `Bearer ${API_KEY}` },
  body: JSON.stringify({ url: heygenVideoUrl })
})
const { id: mediaId } = await media.json()

// Step 2: Schedule post
await fetch('https://postiz.internal/public/v1/posts', {
  method: 'POST',
  headers: { Authorization: `Bearer ${API_KEY}` },
  body: JSON.stringify({
    integrations: ['tiktok-drwei', 'instagram-drwei', 'youtube-drwei'],
    content: generatedCaption,
    media: [mediaId],
    schedule: nextSlot,
    type: 'schedule'
  })
})
```

**Self-hosting stack:**
```yaml
services:
  postiz:        # Main app
  postgres:      # Database
  redis:         # Cache + sessions
  temporal:      # Reliable job scheduling
  elasticsearch: # Temporal workflow history
```
Minimum VPS: 4 vCPU, 8GB RAM. ~$40–60/month on Hetzner or DigitalOcean.

---

### 3.5 Analytics Layer

**Three signals to collect:**

```
Signal 1: Engagement (from Postiz)
  GET /public/v1/analytics/post/:postId
  → Likes, comments, shares, impressions, reach
  → Stored in Airtable per post

Signal 2: Traffic (from UTM links)
  Every bio link / caption link = unique UTM
  ?utm_source=tiktok&utm_medium=social&utm_campaign=drwei&utm_content=post_id_123
  → Dub.co → Click-through rates per post

Signal 3: Conversions (from affiliate platforms)
  → Weekly manual pull initially, automate later
  → Map conversion timestamps back to UTM source post
```

**Weekly optimization workflow (Sunday 8pm):**
1. Pull all post analytics from Postiz (past 7 days)
2. Pull UTM click data
3. Pull affiliate conversion data
4. Score each post: engagement + click + conversion score
5. Generate "optimization brief" via Claude
6. Store brief → seeds Monday's content generation

---

## 4. Human-in-the-Loop Design

**What runs autonomously:**
- Brief generation (n8n CRON trigger)
- Script generation (Claude API)
- Format routing decision
- Video/carousel production (API calls)
- Analytics collection

**What requires human approval (Phase 1):**
- ✅ Every piece before it publishes (Slack notification + approve/reject)
- ✅ Any piece mentioning affiliate products
- ✅ Any medical claim or health advice

**Human review gate:**
```
n8n: Content ready → Send to Slack channel
  → Post preview: script + thumbnail + format + affiliate context
  → Two buttons: [✅ Approve + Schedule] [❌ Reject + Feedback]
  → If no response in 2 hours → Auto-queue as draft
  → Feedback text → Stored → Used in next generation attempt
```

---

## 5. Infrastructure

```
Cloud (Hetzner/DigitalOcean):
├── VPS 1 (4 vCPU, 8GB): Postiz + Postgres + Redis + Temporal
├── VPS 2 (2 vCPU, 4GB): n8n self-hosted
└── Object Storage (Cloudflare R2): Media files

Tracking:
├── Dub.co — UTM link management
└── Airtable — performance data warehouse
```

**Estimated monthly infrastructure cost:**
| Item | Cost |
|---|---|
| VPS 1 (Hetzner CX32) | €13/month |
| VPS 2 (Hetzner CX22) | €8/month |
| Cloudflare R2 (10GB) | $0.15/month |
| Dub.co Pro | $19/month |
| Airtable Pro | $20/month |
| **Infrastructure total** | **~$65/month** |

**API costs per talking-head video:** ~$1–3 (Claude + ElevenLabs + HeyGen)

---

## 6. Build Sequence

### Phase 1: Content Pipeline (Weeks 1–4)

1. **Postiz setup** (Day 1–2): Deploy Docker stack. Connect TikTok, Instagram, YouTube. Test API with curl.
2. **n8n setup** (Day 3): Deploy n8n. Build first workflow: manual trigger → Claude API → log to Airtable.
3. **Character spec integration** (Day 4): Load Dr. Wei JSON into n8n. Pass to Claude API as system prompt. Verify voice consistency.
4. **HeyGen API integration** (Day 5–7): Automate video generation from script. Upload to Postiz via URL.
5. **Slack review gate** (Day 8): n8n notifies Slack, waits for approval, then schedules via Postiz API.
6. **Full pipeline test** (Day 9–10): End-to-end: trigger → script → video → Slack review → Postiz publish.

### Phase 2: Format Expansion + Analytics (Weeks 5–10)

1. Canva API integration (carousels)
2. UTM system: Dub.co integration in n8n
3. Analytics collection: Weekly n8n workflow
4. Optimization brief: Sunday workflow, score content, seed Monday ideation
5. A/B hook testing: 2 variants of same topic, compare at 48 hours

### Phase 3: Scale + Engagement (Month 3+)

1. Second account launch (new character spec only — pipeline reused)
2. Auto-approval pre-filter (LLM reviews before human)
3. ElizaOS engagement layer for comments/DMs
4. ClickBank integration (email list → higher-commission offers)

---

## 7. Open Source Reference Architecture

| Repo | Stars | What to learn |
|---|---|---|
| `harry0703/MoneyPrinterTurbo` | 55K ⭐ | Video production pipeline, subtitle generation, B-roll timing |
| `RayVentura/ShortGPT` | 7K ⭐ | Modular content generation, script → video flow |
| `elizaOS/eliza` | 18K ⭐ | Character file format, plugin architecture (Phase 3) |
| `gitroomhq/postiz-app` | Active | Publishing API, Temporal scheduling patterns |
| `n8n-io/n8n` | 50K+ ⭐ | Self-host setup, workflow patterns |
| `hl897tech/xhs_content_agent` | 91 ⭐ | Only project with analytics feedback loop — study this |

---

## 8. API References

| Service | Docs | Auth method |
|---|---|---|
| Postiz Public API | `postiz.com/docs/api` | Bearer token |
| HeyGen API | `docs.heygen.com` | API key header |
| ElevenLabs API | `docs.elevenlabs.io` | xi-api-key header |
| Claude API | `docs.anthropic.com` | x-api-key header |
| Canva Connect | `www.canva.com/developers` | OAuth2 |
| Dub.co API | `dub.co/docs/api-reference` | Bearer token |
