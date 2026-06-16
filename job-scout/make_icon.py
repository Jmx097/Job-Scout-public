"""
Generates icon.ico for the Job Scout executable.
Run once: python make_icon.py
"""

from PIL import Image, ImageDraw, ImageFont
import os

def make_icon():
    sizes = [16, 32,48, 64, 128, 256]
    images = []

    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Background circle — teal gradient approximation
        pad = max(1, size // 12)
        draw.ellipse(
            [pad, pad, size - pad, size - pad],
            fill=(0, 212, 170),
        )
        # Inner accent ring
        ring = max(1, size // 8)
        draw.ellipse(
            [ring * 2, ring * 2, size - ring * 2, size - ring * 2],
            fill=(0, 180, 140),
        )

        # Magnifying glass
        cx, cy = size // 2, size // 2 - size // 10
        r  = size // 4
        lw = max(1, size // 16)

        # Circle of glass
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            outline=(13, 17, 23),
            width=lw,
        )
        # Handle
        angle_start = (cx + int(r * 0.7), cy + int(r * 0.7))
        angle_end   = (cx + int(r * 1.5), cy + int(r * 1.5))
        draw.line([angle_start, angle_end], fill=(13, 17, 23), width=lw)

        images.append(img)

    out = os.path.join(os.path.dirname(__file__), "icon.ico")
    images[0].save(out, format="ICO", sizes=[(s, s) for s in sizes], append_images=images[1:])
    print(f"✓  icon.ico written to {out}")

if __name__ == "__main__":
    make_icon()
