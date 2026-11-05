---
name: voice-cloning-rvc
description: Clone and convert voices locally with open-source tools — GPT-SoVITS for zero-shot cloning, RVC for voice conversion with training, OpenVoice for instant cloning, and So-VITS-SVC for singing conversion — covering model training, reference audio requirements, and where each fits. Use when the user wants to clone a voice, convert speech to sound like someone, train a voice model, or do AI voice covers.
metadata:
  promptSignals:
    phrases:
      - clone a voice
      - voice conversion
      - rvc model
      - gpt sovits
      - train a voice model
      - openvoice cloning
      - ai voice cover
      - so-vits-svc
      - make my voice sound like
      - voice identity
---

# Voice Cloning and Conversion

Two different things, often confused:

- **Cloning** — generate speech in a target voice from text.
- **Conversion** — take existing speech and re-voice it.

Conversion preserves the original performance (timing, emotion, inflection).
Cloning produces new speech from a script. Most "AI voice" requests are
conversion; most "AI narrator" requests are cloning.

## Tool comparison

| Tool | Repo | Task | Training data | Quality |
|---|---|---|---|---|
| **GPT-SoVITS** | `RVC-Boss/GPT-SoVITS` | Clone + convert | 1 min (zero-shot) or 5 min (fine-tune) | Best overall |
| **RVC** | `RVC-Project/Retrieval-based-Voice-Conversion-WebUI` | Convert | 10 min | Excellent, large model zoo |
| **OpenVoice** | `myshell-ai/OpenVoice` | Clone (instant) + convert | Instant from 30s | Fast, good tone transfer |
| **So-VITS-SVC** | `svc-develop-team/so-vits-svc` | Convert + singing | 30+ min | Best for singing |
| **Real-Time-Voice-Cloning** | `CorentinJ/Real-Time-Voice-Cloning` | Clone (streaming) | Instant | Low latency, lower quality |

**GPT-SoVITS is the default.** It does both tasks, needs the least data, and
has the most active community.

## GPT-SoVITS

```bash
git clone https://github.com/RVC-Boss/GPT-SoVITS.git
cd GPT-SoVITS
pip install -r requirements.txt
```

### Zero-shot cloning (no training)

```python
from GPT_SoVITS.inference_tts import get_tts_wav

wav_file = get_tts_wav(
    text="Your text goes here.",
    ref_wav_path="reference.wav",      # 3-10 seconds of clean speech
    prompt_text="The exact words said in reference.wav",
    text_lang="en",
    ref_lang="en",                      # "zh" for Chinese
    bottleneck_size=256,
)
```

`prompt_text` must be the **verbatim transcript of the reference audio**. This
is how GPT-SoVITS captures the voice's cadence, not just timbre.

### Fine-tuning (better quality)

You need:
- 1 minute of audio for a quick result
- 5 minutes for a good one
- 30+ minutes for an excellent one

```bash
python tools/prepare_datasets.py --input ./raw_audio --output ./prepared
python tools/1-get-text.py --input_dir ./prepared --output_dir ./prepared
python tools/2-get-hubert-wav32k.py --input_dir ./prepared --output_dir ./prepared
python tools/3-get-semantic.py --input_dir ./prepared --output_dir ./prepared
python s1_train.py --config configs/s1longer.yaml --input_dir ./prepared --output_dir ./weights
python s2_train.py --config configs/s2config.yaml --input_dir ./prepared --output_dir ./weights
```

```python
from GPT_SoVITS.inference_tts import get_tts_wav

wav = get_tts_wav(
    text="Your text.",
    ref_wav_path="prepared/ref.wav",
    ref_text="Reference transcript",
    text_lang="en", ref_lang="en",
    sovits_path="weights/s2G_0.pth",
    config_path="configs/tts_infer.yaml",
)
```

## RVC — voice conversion

RVC converts existing audio. It has a large community model zoo.

```bash
git clone https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI.git
cd Retrieval-based-Voice-Conversion-WebUI
pip install -r requirements.txt
python gui.py
```

```python
from RVCProject.RVCInference import RVCInference

infer = RVCInference(device="cuda")
infer.load_model("assets/weights/character.pth",
                  "assets/weights/character.index")

result = infer.process(
    input_path="source.wav",
    output_path="converted.wav",
    index_rate=0.75,      # 0.0 = no timbre retention, 1.0 = full
    f0_up_key=0,         # shift pitch: +12 = one octave up
    f0_method="rmvpe",   # pitch extraction method
    use_f0=True,
)
```

| Parameter | Effect |
|---|---|
| `index_rate` | **The important one.** 0.6–0.8 for a convincing target voice. Below 0.4 sounds like the original with a filter. |
| `f0_up_key` | Semitones to shift. Use to match the source and target pitch ranges, or to avoid chipmunk artefacts. |
| `f0_method` | `rmvpe` is best and fastest. `harvest` is slower but more accurate on breathy voices. |
| `use_f0` | Keep the original pitch contour. Set `False` for speech-to-speech where you want a flat read. |
| `split_threshold` | 0.5 default. Lower for cleaner vocals. |

### Training an RVC model

```bash
python infer-web.py --model_dir "logs/[name]/G_*.pth" --index_dir "logs/[name]/added_*.index"
```

Requirements:
- 10+ minutes of clean, single-speaker audio
- 44.1kHz WAV
- No background music, no other speakers, minimal reverb

```bash
# preprocess
python tools/preprocess_f0.py "dataset/raw" "dataset/44k" f0 rmvpe
python tools/extract_f0_feature.py "dataset/44k" "dataset/44k" f0 rmvpe
python tools/train_nsf_sim_cache.py "dataset/44k" "dataset/cache" 0 1 0 %GPU%
python tools/train_nsf_sim.py \
  --model_dir "logs/experiment" --data_dir "dataset/cache" \
  --exp_name "experiment" --n_layers 3 --sampler_rate 44100
```

The index file (`.index`) improves timbre retention. Build it after training.

## OpenVoice — instant cloning

```python
from openvoice import se_extractor
from openvoice.api import ToneColorConverter

reference_speaker = "reference.wav"
target_se, audio_name = se_extractor.get_se(reference_speaker,
                                            tone_color_converter, sv=True)

converter = ToneColorConverter(
    f'checkpoints_v2/converter/config.json',
    device='cuda')
converter.load_ckpt('checkpoints_v2/converter/checkpoint.pth')

source_se = torch.load(f'checkpoints_v2/base_speakers/ses/en-default.pth')
converter.convert(
    audio_src_path="source.mp3",
    src_se=source_se,
    tgt_se=target_se,
    output_path="converted.wav",
)
```

Tone colour conversion only — it transfers timbre, not speaking style. Faster
and lighter than GPT-SoVITS, less expressive.

## Reference audio requirements

This is where most projects fail. The rules:

1. **Clean** — no music, no keyboard, no traffic, no other speakers.
2. **Single speaker** — no overlap, no responses to questions.
3. **5–30 seconds** — under 5 is too short for the model to characterise;
   over 30 is usually compiled from bad segments.
4. **Consistent tone** — pick one emotional register. Excited-to-calm audio
   produces a voice that sounds unstable.
5. **No effects** — no reverb, no pitch shift, no noise reduction artefacts.
6. **Varied content** — not the same word repeated. The model learns prosody
   from real sentences.

Check it before use:

```bash
ffmpeg -i reference.wav -af "silencedetect=n=-40dB:d=0.3" -f null - 2>&1 | grep silence
ffmpeg -i reference.wav -af astats=metadata=1 -f null - 2>&1 | grep RMS
```

## Ethical and legal use

- Only clone voices you have **consent** to clone — the speaker's own, or
  explicitly licensed.
- Disclose synthetic voice in contexts where it could mislead.
- Some jurisdictions have specific rules about synthetic media in
  advertising, elections, and journalism.
- Do not train on third-party voice performances from songs or films.

## Common failures

**Cloned voice sounds like a robot** — insufficient or noisy training data.
Use a cleaner reference.

**Conversion keeps the original voice** — `index_rate` too low, or the model was
trained on audio that already resembles the source.

**Chipmunk / deep voice** — `f0_up_key` is pushing the pitch outside the model's
training range. Use 0 and let the model handle it.

**Model outputs are 44.1kHz and the pipeline wants 16kHz** — resample
explicitly: `ffmpeg -i out.wav -ar 16000 -ac 1 out16k.wav`.

**Training diverges or outputs garbage** — the dataset has inconsistent
loudness. Normalise first: `ffmpeg -i in.wav -af loudnorm=I=-20 out.wav`.

**Licence issue** — RVC and GPT-SoVITS themselves are permissive, but the
**voice** is not yours to clone. Check the source audio's licence too.

## Related skills

`local-tts-engines` · `lip-sync` · `music-generation` · `tts-to-video` ·
`audio-separation`
