# Signal Layer — Early Trend Detection System
*ChannelFactory · V2 Component · Do not build until 30+ posts are live and converting*

---

## Core Principle: Velocity > Volume

The signal layer does not track what is popular. It tracks what is accelerating.

| Signal | Verdict |
|---|---|
| Topic: 50 → 500 mentions in 24h | ✅ Strong — high velocity, low saturation |
| Topic: 5,000 → 6,000 mentions | ❌ Dead — already saturated |

**We are not chasing trends. We are detecting systems forming in real time.**

---

## The Edge: Speed + Interpretation

Most creators are early OR insightful. The moat is being both.

```
Raw signal → filtered for narrative potential → transformed into an angle
```

This is not a trend aggregator. It is a narrative mining system.

---

## Filtering Principle (Most Important)

We do NOT keep generic trending topics.

We only keep topics that can be turned into:
- System reveals ("here's the hidden mechanism behind this")
- Counterintuitive insights ("everyone thinks X, the reality is Y")
- Economic incentive exposés ("who actually benefits from this")
- Psychological mechanism explanations ("why people do X even when it hurts them")

**Example:**

| Raw signal | Decision | Reason |
|---|---|---|
| "AI tools trending" | ❌ Discard | Generic — no hidden angle |
| "AI girlfriend apps exploding in revenue" | ✅ Keep | Hidden mechanism: loneliness monetization, subscription psychology, retention engineering |

---

## Signal Sources (by timing)

```
EARLIEST (6–12h ahead of platforms)
  └── Reddit (niche subreddits, comment threads, rising posts)
  └── HackerNews (Show HN, Ask HN threads)
  └── X/Twitter (small accounts, replies, emerging threads — not trending tab)

MID (3–6h ahead)
  └── X/Twitter (larger accounts picking it up)
  └── YouTube comments (emerging discussion threads)

LATE (platform native — already partially saturated)
  └── TikTok trending sounds/topics
  └── Instagram Explore page
```

**Strategic window: detect on Reddit/HN, publish before TikTok picks it up.**

---

## Signal Processing Pipeline

```
1. INGEST
   Raw text, source, timestamp, engagement count
   → Store in DB

2. CLASSIFY
   LLM prompt: "What type of signal is this?"
   Types: Problem / Fear / Opportunity / Confusion / Trend / Event
   → Tag each signal

3. SCORE (0–10 per dimension)
   - Relevance to account niche (0–10)
   - Emotional trigger strength: curiosity / fear / status anxiety (0–10)
   - Narrative potential: can this become a system reveal? (0–10)
   - Simplicity: can it be explained in 30 seconds? (0–10)
   - Velocity: how fast is this accelerating? (0–10)
   → Weighted score → threshold filter

4. FRAME
   LLM prompt: "Transform this raw signal into 3 content angles"
   Required output format:
   - Topic: [X]
   - Why it's trending: [1 sentence]
   - Angle 1: Hidden mechanism — [what's really happening]
   - Angle 2: Who benefits — [economic incentive]
   - Angle 3: Psychological mechanism — [why people react this way]

5. ROUTE
   High-score framed signals → Script Generation Agent
   Low-score signals → Discard or archive
```

---

## Account-Specific Signal Sources

### Dr. Wei (Sleep Optimization)
Primary subreddits: `r/sleep`, `r/insomnia`, `r/fitness`, `r/longevity`, `r/43plushealth`
Keywords to monitor: "waking up at 3am", "can't sleep", "magnesium sleep", "TCM insomnia", "sleep after 50", "melatonin stopped working"
RSS feeds: Sleep Foundation news, NIH sleep research, PubMed sleep alerts

### Future: Rabbi / Swiss Banker / Elite Insider (Finance)
Primary subreddits: `r/personalfinance`, `r/Entrepreneur`, `r/FIRE`, `r/investing`, `r/fatFIRE`
Keywords: tax optimization, wealth preservation, interest rate changes, geopolitical events + money

---

## Output Format (feeds Script Agent)

```json
{
  "signal_id": "uuid",
  "raw_text": "...",
  "source": "reddit/r/sleep",
  "timestamp": "...",
  "engagement": 847,
  "velocity_score": 8.2,
  "narrative_score": 9.1,
  "relevance_score": 9.5,
  "overall_score": 8.9,
  "classification": "Problem",
  "angles": [
    {
      "type": "hidden_mechanism",
      "hook_seed": "Your liver is why you wake at 3am",
      "body_seed": "TCM organ clock + cortisol rhythm explanation"
    },
    {
      "type": "counterintuitive",
      "hook_seed": "The reason you can't sleep isn't melatonin",
      "body_seed": "Magnesium deficiency + why melatonin masks not solves"
    }
  ],
  "account_target": "dr-wei",
  "priority": "high"
}
```

---

## Open Source Stack

| Component | Tool | Notes |
|---|---|---|
| Reddit scraping | PRAW / asyncpraw | Free, requires Reddit API key |
| RSS ingestion | feedparser (Python) | Trivially simple |
| Storage | PostgreSQL (shared with Postiz DB) | Add `signals` table |
| Classification + scoring | Claude API | Simple structured output prompt |
| Framing | Claude API | Same call as classification |
| Orchestration | n8n | Signal Agent as scheduled workflow |

---

## Build Phases

**Do NOT build this in V1.** Build the content pipeline first. Validate conversion. Then add signals.

**Phase 1 (V1 — now):** Manual signal sourcing. You identify topics, feed them as briefs to the script agent. No automation.

**Phase 2 (V2 — after 30 posts):** Automated Reddit + RSS ingestion. LLM scoring. Still human review on which angles to run.

**Phase 3 (V3 — after consistent conversion):** Full autonomous signal → content routing. Human reviews only flagged edge cases.

---

## One Line Summary

"Don't track what is trending. Track what is accelerating — then be the first to explain the mechanism."
