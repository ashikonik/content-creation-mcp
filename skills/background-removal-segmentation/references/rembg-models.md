# rembg models

```bash
pip install "rembg[gpu]"
```

```python
from rembg import remove, new_session

session = new_session("u2net_human_seg")   # or "isnet-general-use"
out = remove("in.png", session=session)
```

| Model | Size | Best for |
|---|---|---|
| `u2net` | 176 MB | General objects |
| `u2net_human_seg` | 176 MB | People, portraits |
| `u2netp` | 4.7 MB | Low resource, poor edges |
| `isnet-general-use` | 179 MB | Best general quality |
| `birefnet-general` | 900 MB | Best edges, heaviest |
| `birefnet-portrait` | 900 MB | Portraits, hair |
| `silueta` | 44 MB | Small, decent |

## SAM 2 for promptable segmentation

```python
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor

predictor = SAM2ImagePredictor(build_sam2("sam2_hiera_l.yaml"))
predictor.set_image("in.png")
masks, scores, _ = predictor.predict(
    point_coords=np.array([[x, y]]),
    point_labels=np.array([1]),
    multimask_output=True,
)
```

SAM 2 also has a video mode that propagates the mask through frames — this is
what fixes the flicker that per-frame methods produce.

## Alpha matting

A binary mask has hard edges. Matting refines the boundary:

```python
from pymatting import estimate_alpha_cf
alpha = estimate_alpha_cf(image, mask)
```

## Compositing

```python
from PIL import Image

fg = Image.open("cutout.png")
bg = Image.open("bg.jpg").convert("RGBA")
bg.alpha_composite(fg, (x, y))
bg.convert("RGB").save("composited.png")
```

## Inpainting instead of removal

```bash
python IOPaint/cli.py --model=lama --image=in.png --mask=mask.png --device=cuda
```
