# Tests — Run These Before Building Anything

## Order matters. Run 1 before 2.

---

## Test 1: ElevenLabs voice + timestamps

```bash
cd /Users/melchior/channel-factory-/test
pip install elevenlabs --break-system-packages

ELEVENLABS_API_KEY=your_key python test_elevenlabs.py
```

**What it produces:**
- `output_dr_wei_test.mp3` — the voiceover audio
- `timestamps_raw.json` — the timestamp data structure

**What you're checking:**
1. Play `output_dr_wei_test.mp3` — does the voice sound right? Warm, older female, calm?
2. Open `timestamps_raw.json` — are timestamps character-level or word-level?
3. Is the total duration ~35-40 seconds?

---

## Test 2: Kling 3.0 lip sync

**Before running:** Go to https://fal.ai/models and search "kling lip sync"
Verify the endpoint name and update `KLING_ENDPOINT` in test_kling.py if needed.

```bash
pip install fal-client requests --break-system-packages

FAL_KEY=your_key python test_kling.py \
  --avatar /path/to/dr_wei_avatar.jpg \
  --audio output_dr_wei_test.mp3
```

**What it produces:**
- `test_long_clip.mp4` — the full-length Kling output
- Console output with the fal.ai avatar URL (save this → goes in character-spec.json)

**The critical question:**
Did Kling accept a 38-second audio file and produce a good output?

- **YES** → Drop the 3-segment architecture. One Kling call per video. Massive simplification.
- **NO** (error or duration cap) → Note the max duration. Keep 3-segment.

**What to evaluate in the video:**
1. Face consistency with the avatar image?
2. Body movement (not just lips)?
3. Lip sync quality (close enough, not distracting)?
4. Generation time (affects pipeline scheduling)?

---

## After both tests

Fill in `/Users/melchior/channel-factory-/.env` with real values:

```
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID_DR_WEI=1a0nAYA3FcNQcMMfbddY
FAL_KEY=...
DR_WEI_AVATAR_FAL_URL=<url printed by test_kling.py>
```

Then report back:
1. Does the voice sound right?
2. Did long clip work?
3. What did the video look like?

→ These answers determine 30% of the pipeline architecture.
