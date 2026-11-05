---
name: video-upscale-interpolate
description: Upscale video resolution and increase frame rate using local open-source tools — Real-ESRGAN, video2x, Waifu2x, and RIFE frame interpolation — including tiling for large videos, model selection, batch processing, and artifact avoidance. Use when the user wants to upscale a video, improve resolution, make a video smoother, increase FPS, or convert 24fps to 60fps.
metadata:
  promptSignals:
    phrases:
      - upscale video
      - video super resolution
      - increase frame rate
      - 24fps to 60fps
      - frame interpolation
      - real esrgan video
      - video2x
      - rife interpolation
      - make video smoother
      - 4k video
---

# Video Upscaling and Frame Interpolation

Two separate operations that are often confused:

- **Upscaling** raises resolution (720p → 4K). Adds detail.
- **Frame interpolation** raises frame rate (24fps → 60fps). Adds motion
  smoothness. Does not add detail.

They compose: upscale first, then interpolate, because interpolation needs good
frames to interpolate between.

## Tool selection

| Tool | Upscale | Interpolate | Notes |
|---|---|---|---|
| [video2x](https://github.com/k4yt3x/video2x) | ✅ | ✅ (RIFE) | Wraps both. Simplest combined path. AGPL-3.0. |
| [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) | ✅ | ❌ | Best photo/detail quality. BSD-3-Clause. |
| [Waifu2x](https://github.com/AaronFeng753/Waifu2x-Extension-GUI) | ✅ | ✅ | Strong on anime/illustration. |
| [RIFE](https://github.com/hzwer/ECVF-RIFE) | ❌ | ✅ | Best interpolation quality. |
| [Real-ESRGAN-ncnn](https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan) | ✅ | ❌ | Single binary, no Python. Easiest install. |

**Use the ncnn Vulkan build if you just need results** — no Python environment,
no CUDA setup.

## Real-ESRGAN via ncnn (fastest path)

```bash
# download the release binary for your platform, then:
realesrgan-ncnn-vulkan -i input.mp4 -o output_4k.mp4 \
  -s 4 -n realesrgan-x4plus -f video
```

Frame extraction and reassembly happen automatically for video input.

## video2x (upscale + interpolate together)

```bash
pip install video2x
video2x upscale -i in.mp4 -o out_4k.mp4
video2x interpolate -i in.mp4 -o out_60fps.mp4 -t 2.0
video2x hybrid -i in.mp4 -o out_4k60.mp4   # both
```

## Model selection

| Model | Use for |
|---|---|
| `realesrgan-x4plus` | General footage, photographic content |
| `realesrgan-x4plus-anime` | Anime, illustration, line art |
| `RealESRGAN_x2plus` | 2× when 4× is too aggressive |
| `realesr-general-x4v3` | Adjustable denoise; good on compressed source |
| `rife-v4.6` | Interpolation; `-m` model quality |
| `rife-v3.1` | Faster, slightly less stable on motion |

## Tiling for large videos

Upscaling a 4K frame to 8K needs far more VRAM than the whole frame at 4K.
Tile it:

```bash
realesrgan-ncnn-vulkan -i in.mp4 -o out.mp4 -s 2 \
  -t 512 -m realesr-general-x4v3   # 512px tiles
```

Smaller tiles use less VRAM but can produce visible seams. 512 is a good
balance; 256 if you OOM, 1024 if you have VRAM to spare.

## Interpolation with RIFE

```bash
# 24fps -> 48fps
python RIFE.py -i in.mp4 -o out_48.mp4 -u 2.0

# interpolate to 60fps (2.5x)
python RIFE.py -i in.mp4 -o out_60.mp4 -u 2.5

# use a specific model
python RIFE.py -i in.mp4 -o out.mp4 -m rife-v4.6
```

The `-u` multiplier is the target frame rate multiplier. `2.0` doubles;
`2.5` gives 60fps from 24fps.

## Frame-by-frame with Real-ESRGAN (Python)

```python
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer
from basicsr.utils import imwrite
import cv2, glob, os

model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64,
                 num_block=23, num_grow_ch=32, scale=4)
upsampler = RealESRGANer(
    scale=4, model_path="weights/RealESRGAN_x4plus.pth", model=model,
    tile=512, tile_pad=10, pre_pad=0, half=True)

for path in sorted(glob.glob("frames/*.png")):
    img = cv2.imread(path)
    out, _ = upsampler.enhance(img, outscale=4)
    imwrite(out, os.path.join("out_frames", os.path.basename(path)))
```

Then reassemble:

```bash
ffmpeg -y -framerate 24 -i out_frames/%05d.png -c:v libx264 -crf 16 -pix_fmt yuv420p out.mp4
```

**Preserve the original frame rate** when reassembling. If the source was
24fps and you write at 30fps, the motion speeds up.

## Order of operations

```
source (720p, 24fps)
  → upscale ×2 or ×4        (Real-ESRGAN, tiled)
  → interpolate to 48/60fps (RIFE)
  → encode                   (see media-transcode-pipeline)
```

Do not interpolate before upscaling — RIFE interpolates between source frames,
and low-resolution source frames yield low-resolution interpolated frames.

## Artifact avoidance

**Warping / ghosting** — the classic interpolation failure on fast motion.
Fix: use a newer RIFE (`v4.6`), or reduce the multiplier to 2.0.

**Shimmer on edges** — temporal inconsistency in the upscaler. Use
`realesr-general-x4v3` with denoise rather than `x4plus`, or upscale without
interpolation.

**Flicker between frames** — the source is already compressed badly. Upscaling
cannot restore information that is not there. Re-encode the source cleanly first
at a high bitrate, then upscale.

**Detail too sharp, plastic look** — the model is over-sharpening. Use
`x2plus` instead of `x4plus`, or denoise first.

## Common failures

**OOM** — enable tiling (`-t 256`), use the ncnn build, or process in chunks.

**Output video plays at wrong speed** — you changed the frame rate during
reassembly. Keep it identical to the source.

**Colours shift after upscale** — the upscaler works in YUV; convert RGB→YUV
with the correct matrix before processing, or use the ncnn build which handles
this internally.

**Very slow on CPU** — expected. Real-ESRGAN on video is minutes per second of
footage. Use the ncnn Vulkan build with `--gpu` if supported.

## Related skills

`text-to-video-local` · `comfyui-video-workflows` · `media-transcode-pipeline` ·
`video-background-removal` · `shorts-reels-pipeline`
