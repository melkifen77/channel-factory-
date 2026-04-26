"""
TEST 1: ElevenLabs voice + word timestamps
What we're validating:
  - Voice sounds right for Dr. Wei
  - Word-level timestamps are available and in a usable format
  - Audio duration matches expected ~35-40s for 100 words

Run:
  cd /Users/melchior/channel-factory-/test
  pip install elevenlabs --break-system-packages
  ELEVENLABS_API_KEY=your_key python test_elevenlabs.py
"""

import os, json, time
from elevenlabs import ElevenLabs

API_KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip().replace("\xa0", "").replace("\u200b", "")
VOICE_ID = "1a0nAYA3FcNQcMMfbddY"  # Dr. Wei voice

# Script #1 voiceover — full text
VOICEOVER = """If you wake between 1 and 3am, Western medicine calls it insomnia.
In Chinese medicine, we call it the liver clock.

Between 1 and 3am, the liver is most active. When it carries too much — 
stress, alcohol, processed food — it cannot complete its work quietly.
It wakes you up instead.

I spent 40 years watching this pattern in patients. The ones who healed 
did not take more supplements. They asked what the waking was trying to say.

Your body is not broken. It is communicating.
Start there."""

def test_voice_with_timestamps():
    client = ElevenLabs(api_key=API_KEY)
    
    print("Generating audio with timestamps...")
    start = time.time()
    
    response = client.text_to_speech.convert_with_timestamps(
        voice_id=VOICE_ID,
        text=VOICEOVER,
        model_id="eleven_turbo_v2",
        voice_settings={
            "stability": 0.75,
            "similarity_boost": 0.85,
            "style": 0.20,
            "use_speaker_boost": True
        }
    )
    
    elapsed = time.time() - start
    print(f"API call took: {elapsed:.1f}s")
    
    # Save audio
    audio_path = "output_dr_wei_test.mp3"
    with open(audio_path, "wb") as f:
        f.write(response.audio)
    print(f"Audio saved: {audio_path}")
    
    # Inspect timestamps
    alignment = response.alignment
    print(f"\nTimestamp format: {type(alignment)}")
    print(f"Number of entries: {len(alignment.characters) if hasattr(alignment, 'characters') else 'N/A'}")
    
    # Show first 10 entries to understand format
    print("\nFirst 10 timestamp entries:")
    if hasattr(alignment, 'characters'):
        for i, (char, start_t, end_t) in enumerate(zip(
            alignment.characters[:30],
            alignment.character_start_times_seconds[:30],
            alignment.character_end_times_seconds[:30]
        )):
            print(f"  '{char}' → {start_t:.3f}s – {end_t:.3f}s")
    
    # Save full timestamps to file for inspection
    timestamp_data = {
        "characters": alignment.characters if hasattr(alignment, 'characters') else [],
        "character_start_times_seconds": alignment.character_start_times_seconds if hasattr(alignment, 'character_start_times_seconds') else [],
        "character_end_times_seconds": alignment.character_end_times_seconds if hasattr(alignment, 'character_end_times_seconds') else []
    }
    with open("timestamps_raw.json", "w") as f:
        json.dump(timestamp_data, f, indent=2)
    print("\nFull timestamps saved to: timestamps_raw.json")
    
    # Estimate total duration
    if hasattr(alignment, 'character_end_times_seconds') and alignment.character_end_times_seconds:
        duration = max(alignment.character_end_times_seconds)
        print(f"\nEstimated audio duration: {duration:.1f}s")
        print(f"Word count: {len(VOICEOVER.split())}")
    
    print("\n✅ WHAT TO CHECK:")
    print("  1. Open output_dr_wei_test.mp3 — does the voice sound right?")
    print("  2. Check timestamps_raw.json — are they character-level or word-level?")
    print("  3. Is the duration ~35-40 seconds for ~100 words?")
    print("  4. Note the exact JSON structure — this drives the subtitle pipeline")

if __name__ == "__main__":
    test_voice_with_timestamps()
