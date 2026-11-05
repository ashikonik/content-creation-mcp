---
name: local-tts-engines
description: Generate speech locally with open-source TTS engines — Piper, Coqui XTTS, Kokoro, Bark, VoxCPM, CosyVoice, Qwen3-TTS, Dia, ChatTTS, and Supertonic — with model comparison, installation, voice cloning support, emotion control, and API usage. Use when the user wants to generate a voiceover, synthesize speech, do text-to-speech locally, or needs a free offline TTS engine.
metadata:
  promptSignals:
    phrases:
      - text to speech
      - generate voiceover
      - tts engine
      - piper tts
      - coqui xtts
      - kokoro tts
      - bark tts
      - local speech synthesis
      - offline voice generation
      - elevenlabs alternative
      - voiceover audio
---

# Local Text-to-Speech

Open TTS engines that run offline. Most produce speech good enough for
voiceover; the differences are in voice quality, cloning support, and control.

## Engine comparison

| Engine | Repo | Licence | Cloning | Emotion | Speed | VRAM |
|---|---|---|---|---|---|---|
| **Piper** | `rhasspy/piper` | MIT | No | No | Very fast (RTF <0.1) | None (CPU) |
| **Kokoro** | `hexgrad/kokoro` | Apache-2.0 | No | No | Fast | <1GB |
| **Coqui XTTS v2** | `coqui-ai/TTS` | MPL-2.0 | ✅ 6s sample | Some | Moderate | 2GB |
| **VoxCPM** | `OpenBMB/VoxCPM` | Apache-2.0 | ✅ | ✅ | Moderate | 4GB |
| **CosyVoice** | `QwenAudio/CosyVoice` | Apache-2.0 | ✅ | ✅ | Moderate | 4GB |
| **Qwen3-TTS** | `QwenLM/Qwen3-TTS` | Apache-2.0 | ✅ | ✅ | Moderate | 4GB |
| **Dia** | `nari-labs/dia` | Apache-2.0 | No | ✅✅ | Fast | 2GB |
| **Bark** | `suno-ai/bark` | MIT | Yes (loose) | ✅ | Slow | 4GB |
| **ChatTTS** | `2noise/ChatTTS` | AGPL-3.0 | No | ✅ | Fast | 2GB |
| **Supertonic** | `supertone-oss/supertonic` | MIT | No | No | Very fast | <1GB |

**Recommendations:**
- **Bulk narration, no cloning** → Piper (fastest, tiny, MIT) or Kokoro (better quality)
- **Clone a specific voice** → XTTS v2 or CosyVoice
- **Expressive dialogue with tags** → Dia
- **Multilingual** → CosyVoice or Qwen3-TTS (strong Chinese and English)
- **No GPU at all** → Piper or Kokoro, both CPU-only

## Piper — fastest, CPU-only

```bash
pip install piper-tts
piper --model en_US-lessac-medium --output_file out.wav
```

```bash
# list voices
piper --list-voices

# with a specific voice
echo "Your text here" | piper \
  --model en_US-amy-medium \
  --output_file out.wav \
  --length_scale 1.1 \
  --noise_scale 0.667 \
  --noise_w 0.8
```

`length_scale` > 1.0 slows delivery, < 1.0 speeds it up. `noise_scale` controls
variation — lower is more deterministic, higher is more expressive.

## Kokoro — best quality for a small model

```bash
pip install kokoro
```

```python
from kokoro import KPipeline

pipeline = KPipeline(lang_code="a")   # "a" = American English, "b" = British

for i, (gs, ps, audio) in enumerate(
        pipeline("Your text here", voice="af_heart")):
    import soundfile as sf
    sf.write(f"out_{i}.wav", audio, 24000)
```

`voice` names: `af_heart`, `af_bella`, `am_michael`, `bf_emma`, `bm_george`.

**Kokoro is the strongest default** for English voiceover — clean, natural, and
runs on CPU in real time.

## Coqui XTTS v2 — cloning from 6 seconds

```bash
pip install TTS
```

```python
from TTS import TTS
import torch

tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)

tts.tts_to_file(
    text="Your text here.",
    speaker_wav="reference.wav",          # 6+ seconds of clean speech
    language="en",
    file_path="out.wav",
)
```

```python
# generate for multiple speakers at once
tts.tts_to_file(text="Line one.", speaker_wav="a.wav", language="en",
                file_path="a_out.wav", split_sentences=True)
```

**Reference audio quality matters more than reference length.** 6–30 seconds of
clean, single-speaker audio with no music and no reverb. A 6-second clip of a
noisy recording clones the noise too.

## CosyVoice — cloning plus emotion

```bash
git clone https://github.com/QwenAudio/CosyVoice.git
pip install -r CosyVoice/requirements.txt
```

```python
from cosyvoice.cli.cosyvoice import CosyVoice2

m = CosyVoice2("pretrained_models/CosyVoice2-0.5B", load_jit=True, load_trt=True)

for j in m.inference_cross_lingual('你 好', prompt_speech_16k='zero_shot_prompt.wav'):
    print(j['tts_speech'])
```

## Qwen3-TTS — multilingual with strong Chinese

```python
from qwen_tts import QwenTTS

tts = QwenTTS(model="Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice")
audio = tts.generate("Your text here", language="English", speaker="Aiden")
```

## Dia — dialogue with audio tags

```bash
pip install dia-ns
```

```python
import soundfile as sf
from dia.model import Dia

model = Dia.from_pretrained("nari-labs/Dia-1.6B")
audio = model.generate(
    "[laughs] Oh, that's terrible. [sighs] I really thought it would work."
)
sf.write("out.wav", audio, 44100)
```

Dia understands non-verbal tags: `[laughs]`, `[sighs]`, `[clears throat]`,
`[gasps]`, `[coughs]`. This is what makes it good for dialogue and bad for
straight narration — the tags make it wander.

## Bark — the original expressive one

```bash
pip install bark
```

```python
import bark

bark.generate_audio(
    "Your text here. [laughs]",
    history_prompt=None,
    model_name="suno/bark-small",
    voice_preset="v2/en_speaker_6",
)
```

Bark hallucinates background noise and breathing — charming for character work,
unusable for clean voiceover. It also drifts on long text.

## Voice selection criteria

For narration, pick on: **clarity at 16kHz**, **no reverb**, **consistent pace**,
and **no unusual accent**. For character work, pick on expressiveness.

Test by generating the **same 30-second script** in 3–4 voices and listening at
1× on phone speakers, not headphones. That is where most voiceover is heard.

## Post-processing

```bash
# normalise loudness to -14 LUFS (social) or -16 (broadcast)
ffmpeg -i raw.wav -af loudnorm=I=-14:TP=-1.5:LRA=11 out.wav

# trim silence at start and end
ffmpeg -i out.wav -af silenceremove=start_periods=1:start_silence=0.05 \
  -af areverse,silenceremove=start_periods=1:start_silence=0.05,areverse out_trim.wav

# high-pass to remove rumble
ffmpeg -i out.wav -af "highpass=f=80" out_clean.wav
```

Trim silence **before** loudness normalisation, not after.

## Common failures

**Cloned voice sounds wrong** — the reference audio is poor. Re-record in a
quiet room, 10+ seconds, single speaker, no music.

**Output is choppy or slow** — sample rate mismatch when concatenating. Force
everything to the same rate: `ffmpeg -i in.wav -ar 24000 -ac 1 out.wav`.

**Different engines produce different loudness** — normalise each to the same
LUFS target before assembly.

**Kokoro/Piper pronunciation is wrong** — they do not support phoneme overrides
well. Add spacing or use a different engine for that phrase.

**Bark adds background chatter** — that is the model. Use Kokoro or Piper for
clean narration.

**Long text drifts** — generate in sentence-sized chunks and concatenate, rather
than passing a whole page.

## Related skills

`voice-cloning-rvc` · `lip-sync` · `subtitle-generation` · `tts-to-video` ·
`music-generation` · `audio-separation` · `shorts-reels-pipeline`
