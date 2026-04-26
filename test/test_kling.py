"""
TEST 2: Kling 3.0 lip sync via fal.ai
What we're validating:
  A) Single long clip: can Kling handle 35-40s audio without quality degrading?
     → If YES: drop 3-segment architecture entirely. One API call, no stitching.
     → If NO: cap is around 15s, keep 3-segment architecture.
  B) Face quality: does Dr. Wei's avatar look convincing?
  C) Body movement: does she move naturally, or is it a static talking head?
  D) Lip sync: is it good enough or distracting?

Run:
  pip install fal-client requests --break-system-packages
  FAL_KEY=your_key python test_kling.py --avatar /path/to/dr_wei.jpg --audio output_dr_wei_test.mp3

IMPORTANT: Check fal.ai/models for the exact Kling lip sync endpoint before running.
Search "kling lip sync" on fal.ai — the endpoint name may have changed.
"""

import os, sys, time, argparse, asyncio
import fal_client

FAL_KEY = os.environ.get("FAL_KEY")

# ⚠️  Verify this endpoint at https://fal.ai/models — search "kling lip sync"
# Common candidates:
#   fal-ai/kling-video/v1.6/lip-sync
#   fal-ai/kling-video/v2/lip-sync  
#   fal-ai/kling-video/master/lip-sync
KLING_ENDPOINT = "fal-ai/kling-video/v2.1/lip-sync"  # UPDATE IF NEEDED

def upload_file(path, label):
    """Upload a local file to fal.ai storage and return the public URL."""
    print(f"Uploading {label}...")
    url = fal_client.upload_file(path)
    print(f"  → {url}")
    return url

async def run_kling_test(avatar_url, audio_url, duration_s, test_label):
    """Run one Kling lip sync call and return the result video URL."""
    print(f"\n🎬 Starting Kling test: {test_label}")
    print(f"   Avatar: {avatar_url[:60]}...")
    print(f"   Audio duration: {duration_s}s")
    print(f"   Endpoint: {KLING_ENDPOINT}")
    
    start = time.time()
    
    result = await fal_client.run_async(
        KLING_ENDPOINT,
        arguments={
            "image_url": avatar_url,
            "audio_url": audio_url,
            "duration": duration_s,
            "aspect_ratio": "9:16",
            "mode": "pro",             # use pro mode for best quality
        }
    )
    
    elapsed = time.time() - start
    print(f"   ✅ Done in {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"   Result: {result}")
    
    return result, elapsed

def download_video(url, filename):
    import requests
    print(f"\nDownloading result to {filename}...")
    r = requests.get(url, stream=True)
    with open(filename, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    size_mb = os.path.getsize(filename) / 1e6
    print(f"  Saved: {filename} ({size_mb:.1f}MB)")

async def main(avatar_path, audio_path):
    os.environ["FAL_KEY"] = FAL_KEY
    
    print("=" * 60)
    print("KLING 3.0 LIP SYNC TEST")
    print("=" * 60)
    
    # Step 1: Upload avatar (do once, reuse URL)
    avatar_url = upload_file(avatar_path, "Dr. Wei avatar")
    print(f"\n📌 SAVE THIS URL — store it in character-spec.json as 'avatar_fal_url':")
    print(f"   {avatar_url}\n")
    
    # Step 2: Upload audio
    audio_url = upload_file(audio_path, "test audio")
    
    # Step 3: Run the key test — full length clip (~35-40s)
    # This is the most important test: does Kling handle long audio?
    print("\n--- TEST A: Full-length clip (35-40s) ---")
    print("This determines if we need 3-segment architecture or not.")
    
    try:
        result_long, time_long = await run_kling_test(
            avatar_url, audio_url,
            duration_s=38,  # adjust to match your actual audio length
            test_label="Full 38s clip"
        )
        
        # Extract video URL from result
        video_url = None
        if isinstance(result_long, dict):
            video_url = (
                result_long.get("video", {}).get("url") or
                result_long.get("url") or
                result_long.get("video_url")
            )
        
        if video_url:
            download_video(video_url, "test_long_clip.mp4")
        else:
            print(f"⚠️  Could not extract video URL. Full result: {result_long}")
            
    except Exception as e:
        print(f"❌ Long clip test failed: {e}")
        print("   This may mean Kling has a duration cap. Check the error message.")
        print("   If it says max duration exceeded → 3-segment architecture is needed.")
    
    # Step 4: Also test a short clip to compare quality
    print("\n--- TEST B: Short clip (12s) for quality comparison ---")
    
    # For short test, we need a short audio segment
    # If you ran test_elevenlabs.py first, trim the audio manually for this
    # Or just note: the short test needs a 12s audio file
    print("⚠️  For the short clip test, trim your audio to 12s first:")
    print("   ffmpeg -i output_dr_wei_test.mp3 -t 12 test_short_audio.mp3")
    print("   Then re-run: python test_kling.py --avatar ... --audio test_short_audio.mp3 --short-only")
    
    print("\n" + "=" * 60)
    print("WHAT TO EVALUATE (watch test_long_clip.mp4)")
    print("=" * 60)
    print("""
  1. DURATION: Did Kling accept the full 38s clip?
     → YES: Drop 3-segment architecture. One API call. Major simplification.
     → NO (error or capped): Note the max duration. Keep 3-segment.

  2. FACE: Does Dr. Wei look like the avatar image?
     → Look for: consistency of face shape, skin tone, eye position
     → Acceptable: minor variations between clips
     → Dealbreaker: different person entirely, melting features

  3. BODY MOVEMENT: Does she move naturally?
     → Look for: head movement, shoulder/upper body animation
     → This is what makes it feel like a real video vs a talking photo

  4. LIP SYNC: Is it convincing?
     → It won't be perfect. Is it close enough to not be distracting?
     → Test: watch without looking at the mouth. Does it feel off?
     
  5. GENERATION TIME: How many minutes did it take?
     → This is the pipeline wall-clock time. Plan your posting schedule around it.
     
  6. VISUAL QUALITY: Is it 4K? Is there banding/artifacts?
     → Important for platform compression (TikTok recompresses heavily)
""")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--avatar", required=True, help="Path to Dr. Wei avatar image")
    parser.add_argument("--audio", required=True, help="Path to test audio MP3 (from test_elevenlabs.py)")
    args = parser.parse_args()
    
    if not FAL_KEY:
        print("❌ Set FAL_KEY environment variable first")
        sys.exit(1)
    
    if not os.path.exists(args.avatar):
        print(f"❌ Avatar not found: {args.avatar}")
        sys.exit(1)
        
    if not os.path.exists(args.audio):
        print(f"❌ Audio not found: {args.audio}")
        print("  Run test_elevenlabs.py first to generate the audio")
        sys.exit(1)
    
    asyncio.run(main(args.avatar, args.audio))
