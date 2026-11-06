---
name: video-editing
description: AI-assisted video editing workflows for cutting, structuring, and augmenting
  real footage. Covers the full pipeline from raw capture through FFmpeg, Remotion,
  local TTS and image generation, and final polish in Descript or CapCut. Use when
  the user wants to edit video, cut footage, create vlogs, or build video content.
metadata:
  promptSignals:
    phrases:
    - edit a video
    - cut footage into a vlog
    - ai assisted video editing
    - structure a video from raw capture
    - polish a video in descript
    - final cut and export
    - search my video library
    - find a moment in a recording
    - search my footage
    - extract frames from a video
    - index a video for search
    - locate a clip in a long recording
---

# Video Editing

AI-assisted editing for real footage. Not generation from prompts. Editing existing video fast.

## When to Activate

- User wants to edit, cut, or structure video footage
- Turning long recordings into short-form content
- Building vlogs, tutorials, or demo videos from raw capture
- Adding overlays, subtitles, music, or voiceover to existing video
- Reframing video for different platforms (YouTube, TikTok, Instagram)
- User says "edit video", "cut this footage", "make a vlog", or "video workflow"

## Core Thesis

AI video editing is useful when you stop asking it to create the whole video and start using it to compress, structure, and augment real footage. The value is not generation. The value is compression.

## The Pipeline

```
Screen Studio / raw footage
  → Claude / Codex
  → FFmpeg
  → Remotion
  → local TTS / local diffusion
  → Descript or CapCut
```

Each layer has a specific job. Do not skip layers. Do not try to make one tool do everything.

## Layer 1: Capture (Screen Studio / Raw Footage)

Collect the source material:
- **Screen Studio**: polished screen recordings for app demos, coding sessions, browser workflows
- **Raw camera footage**: vlog footage, interviews, event recordings
- **Desktop capture**: session recording via the OS's own screen recorder, then import the file (see `media-transcode-pipeline` for preparing the capture for the timeline)

Output: raw files ready for organization.

## Layer 2: Organization (Claude / Codex)

Use Claude Code or Codex to:
- **Transcribe and label**: generate transcript, identify topics and themes
- **Plan structure**: decide what stays, what gets cut, what order works
- **Identify dead sections**: find pauses, tangents, repeated takes
- **Generate edit decision list**: timestamps for cuts, segments to keep
- **Scaffold FFmpeg and Remotion code**: generate the commands and compositions

```
Example prompt:
"Here's the transcript of a 4-hour recording. Identify the 8 strongest segments
for a 24-minute vlog. Give me FFmpeg cut commands for each segment."
```

This layer is about structure, not final creative taste.

## Layer 3: Deterministic Cuts (FFmpeg)

FFmpeg handles the boring but critical work: splitting, trimming, concatenating, and preprocessing.

### Extract segment by timestamp

```bash
ffmpeg -i raw.mp4 -ss 00:12:30 -to 00:15:45 -c copy segment_01.mp4
```

### Batch cut from edit decision list

```bash
#!/bin/bash
# cuts.txt: start,end,label
while IFS=, read -r start end label; do
  ffmpeg -i raw.mp4 -ss "$start" -to "$end" -c copy "segments/${label}.mp4"
done < cuts.txt
```

### Concatenate segments

```bash
# Create file list
for f in segments/*.mp4; do echo "file '$f'"; done > concat.txt
ffmpeg -f concat -safe 0 -i concat.txt -c copy assembled.mp4
```

### Create proxy for faster editing

```bash
ffmpeg -i raw.mp4 -vf "scale=960:-2" -c:v libx264 -preset ultrafast -crf 28 proxy.mp4
```

### Extract audio for transcription

```bash
ffmpeg -i raw.mp4 -vn -acodec pcm_s16le -ar 16000 audio.wav
```

### Normalize audio levels

```bash
ffmpeg -i segment.mp4 -af loudnorm=I=-16:TP=-1.5:LRA=11 -c:v copy normalized.mp4
```

## Layer 4: Programmable Composition (Remotion)

Remotion turns editing problems into composable code. Use it for things that traditional editors make painful:

### When to use Remotion

- Overlays: text, images, branding, lower thirds
- Data visualizations: charts, stats, animated numbers
- Motion graphics: transitions, explainer animations
- Composable scenes: reusable templates across videos
- Product demos: annotated screenshots, UI highlights

### Basic Remotion composition

```tsx
import { AbsoluteFill, Sequence, Video, useCurrentFrame } from "remotion";

export const VlogComposition: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill>
      {/* Main footage */}
      <Sequence from={0} durationInFrames={300}>
        <Video src="/segments/intro.mp4" />
      </Sequence>

      {/* Title overlay */}
      <Sequence from={30} durationInFrames={90}>
        <AbsoluteFill style={{
          justifyContent: "center",
          alignItems: "center",
        }}>
          <h1 style={{
            fontSize: 72,
            color: "white",
            textShadow: "2px 2px 8px rgba(0,0,0,0.8)",
          }}>
            The AI Editing Stack
          </h1>
        </AbsoluteFill>
      </Sequence>

      {/* Next segment */}
      <Sequence from={300} durationInFrames={450}>
        <Video src="/segments/demo.mp4" />
      </Sequence>
    </AbsoluteFill>
  );
};
```

### Render output

```bash
npx remotion render src/index.ts VlogComposition output.mp4
```

See the [Remotion docs](https://www.remotion.dev/docs) for detailed patterns and API reference.

## Layer 5: Generated Assets (local models)

Generate only what you need. Do not generate the whole video.

This corpus is open-source and local-hostable only: every generator below runs
on your own machine. See the `local-tts-engines`, `music-generation`,
`local-diffusion-suite`, and `comfyui-image-workflows` skills for setup and
checkpoint choices.

### Voiceover with a local TTS engine

Use `local-tts-engines` (Piper / Coqui / Kokoro / Bark) for narration:

```bash
# Piper — fast, CPU-friendly, good default for narration
echo "Your narration text here" | piper --model en_US-lessac-medium.onnx \
  --output_file voiceover.wav
```

For a voice cloned from a specific person, use `voice-cloning-rvc` to build a
speaker model first, then drive it from the same TTS pipeline.

### Music and SFX locally

Use the `music-generation` skill for background music (MusicGen, AudioCraft,
ACE-Step) and `audio-separation` to isolate stems from a finished track so you
can swap one layer without regenerating everything.

### Generated visuals locally

Use `local-diffusion-suite` (SDXL, FLUX) or `comfyui-image-workflows` for
insert shots, thumbnails, or B-roll that does not exist:

```bash
# FLUX via diffusers
python3 -c "
from diffusers import FluxPipeline
import torch
pipe = FluxPipeline.from_pretrained('black-forest-labs/FLUX.1-schnell', torch_dtype=torch.bfloat16)
img = pipe('professional thumbnail for a tech vlog, dark background', num_inference_steps=4).images[0]
img.save('thumbnail.png')
"
```

### VideoDB generative audio

If VideoDB is configured:
```python
voiceover = coll.generate_voice(text="Narration here", voice="alloy")
music = coll.generate_music(prompt="lo-fi background for coding vlog", duration=120)
sfx = coll.generate_sound_effect(prompt="subtle whoosh transition")
```

## Layer 6: Final Polish (Descript / CapCut)

The last layer is human. Use a traditional editor for:
- **Pacing**: adjust cuts that feel too fast or slow
- **Captions**: auto-generated, then manually cleaned
- **Color grading**: basic correction and mood
- **Final audio mix**: balance voice, music, and SFX levels
- **Export**: platform-specific formats and quality settings

This is where taste lives. AI clears the repetitive work. You make the final calls.

## Social Media Reframing

Different platforms need different aspect ratios:

| Platform | Aspect Ratio | Resolution |
|----------|-------------|------------|
| YouTube | 16:9 | 1920x1080 |
| TikTok / Reels | 9:16 | 1080x1920 |
| Instagram Feed | 1:1 | 1080x1080 |
| X / Twitter | 16:9 or 1:1 | 1280x720 or 720x720 |

### Reframe with FFmpeg

```bash
# 16:9 to 9:16 (center crop)
ffmpeg -i input.mp4 -vf "crop=ih*9/16:ih,scale=1080:1920" vertical.mp4

# 16:9 to 1:1 (center crop)
ffmpeg -i input.mp4 -vf "crop=ih:ih,scale=1080:1080" square.mp4
```

### Reframe with VideoDB

```python
# Smart reframe (AI-guided subject tracking)
reframed = video.reframe(start=0, end=60, target="vertical", mode=ReframeMode.smart)
```

## Scene Detection and Auto-Cut

### FFmpeg scene detection

```bash
# Detect scene changes (threshold 0.3 = moderate sensitivity)
ffmpeg -i input.mp4 -vf "select='gt(scene,0.3)',showinfo" -vsync vfr -f null - 2>&1 | grep showinfo
```

### Silence detection for auto-cut

```bash
# Find silent segments (useful for cutting dead air)
ffmpeg -i input.mp4 -af silencedetect=noise=-30dB:d=2 -f null - 2>&1 | grep silence
```

### Highlight extraction

Use Claude to analyze transcript + scene timestamps:
```
"Given this transcript with timestamps and these scene change points,
identify the 5 most engaging 30-second clips for social media."
```

### Searching your own footage

To find a moment in a large library without watching it end to end, index it
locally and search the index. Nothing here needs an account or a per-call
fee.

**Transcript search** — transcribe once, then grep the text:

```bash
# Transcribe with local Whisper (see the subtitle-generation skill)
whisper.cpp -m models/ggml-medium.en.bin -f input.mp4 -otxt -osrt

# Find every mention, with the timestamp alongside it
grep -in "coffee\|espresso" transcript.txt
```

The timestamps in the `.srt` give you the in/out points directly, so a
transcript hit maps to a cut without any further work.

**Visual search** — when the thing you are looking for is in the picture,
not the audio, embed the frames and search them. CLIP-style models run on
CPU:

```bash
# Sample one frame per second
ffmpeg -i input.mp4 -vf fps=1 frames/%06d.png

# Embed the frames (open_clip, or any CLIP checkpoint)
python3 embed_frames.py frames/ --model ViT-B-32 --out embeddings.npy

# Rank frames against a text query
python3 search_frames.py embeddings.npy --query "a dog running on grass" --top 10
```

Because the frames were sampled at 1 fps, a frame index maps back to a
timestamp as `index` seconds into the video.

**Combining them** — the two indexes answer different questions and are
worth having side by side. The transcript finds what was *said*; the frame
embeddings find what was *seen*. A clip of someone pouring coffee with no
speech is invisible to a transcript search and obvious to a visual one.

When the answer is a specific moment rather than a topic, combine the
scene-change timestamps from the section above with a transcript or visual
search, so the candidates are already at cut boundaries.

## What Each Tool Does Best

| Tool | Strength | Weakness |
|------|----------|----------|
| Claude / Codex | Organization, planning, code generation | Not the creative taste layer |
| FFmpeg | Deterministic cuts, batch processing, format conversion | No visual editing UI |
| Remotion | Programmable overlays, composable scenes, reusable templates | Learning curve for non-devs |
| Screen Studio | Polished screen recordings immediately | Only screen capture |
| Local TTS / diffusion | Voice, narration, music, SFX, insert shots | Not the center of the workflow |
| Descript / CapCut | Final pacing, captions, polish | Manual, not automatable |

## Key Principles

1. **Edit, don't generate.** This workflow is for cutting real footage, not creating from prompts.
2. **Structure before style.** Get the story right in Layer 2 before touching anything visual.
3. **FFmpeg is the backbone.** Boring but critical. Where long footage becomes manageable.
4. **Remotion for repeatability.** If you'll do it more than once, make it a Remotion component.
5. **Generate selectively.** Only use AI generation for assets that don't exist, not for everything.
6. **Taste is the last layer.** AI clears repetitive work. You make the final creative calls.

## Related Skills

- `local-tts-engines` — Local narration and voiceover synthesis
- `music-generation` — Local background music and SFX
- `local-diffusion-suite` — Local insert shots and stills
- `media-transcode-pipeline` — Server-side transcoding, packaging, and normalization
- `content-engine` — Platform-native content distribution

## Reference tools

Other open-source video tools worth knowing, each over 1,000
GitHub stars — see `references/video-reference-tools.md`.

