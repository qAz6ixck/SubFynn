"""
Generate modern high-resolution icon for SubFynn.
A sleek dark squircle with glowing neon soundwave and subtitle badge.
Outputs assets/app_icon.png and assets/app_icon.ico.
"""

import os
import math
from PIL import Image, ImageDraw, ImageFilter

def create_subfynn_icon():
    size = 1024  # Draw in high resolution for supersampling
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Background Squircle with subtle gradient
    margin = 48
    corner_radius = 220
    rect = [margin, margin, size - margin, size - margin]

    # Create mask for rounded rectangle
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(rect, radius=corner_radius, fill=255)

    # Base background gradient
    bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg_draw = ImageDraw.Draw(bg)
    for y in range(margin, size - margin):
        ratio = (y - margin) / (size - 2 * margin)
        # Deep dark #1c1a24 to #2a243a
        r = int(28 + ratio * 14)
        g = int(26 + ratio * 10)
        b = int(36 + ratio * 22)
        bg_draw.line([(margin, y), (size - margin, y)], fill=(r, g, b, 255))

    # Ambient radial glow inside squircle
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    cx, cy = size // 2, int(size * 0.42)
    for rad in range(350, 0, -10):
        alpha = int(45 * (1 - rad / 350))
        glow_draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(99, 102, 241, alpha))

    bg = Image.alpha_composite(bg, glow)
    # Apply squircle mask to background
    bg.putalpha(mask)

    # Specular border
    border = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(border)
    b_draw.rounded_rectangle(rect, radius=corner_radius, outline=(255, 255, 255, 45), width=6)
    # Top highlight
    b_draw.line([margin + corner_radius, margin + 3, size - margin - corner_radius, margin + 3], fill=(255, 255, 255, 120), width=6)

    final_base = Image.alpha_composite(bg, border)

    # 2. Glowing Waveform Soundbars
    wave_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    w_draw = ImageDraw.Draw(wave_layer)

    # 7 Soundwave bars centered
    bar_heights = [120, 220, 340, 420, 360, 240, 140]
    bar_width = 38
    bar_spacing = 30
    total_w = len(bar_heights) * bar_width + (len(bar_heights) - 1) * bar_spacing
    start_x = (size - total_w) // 2
    center_y = int(size * 0.42)

    # Gradient colors for bars from Cyan to Indigo to Violet
    colors = [
        (56, 189, 248),   # #38bdf8 Cyan
        (79, 140, 245),
        (99, 102, 241),   # #6366f1 Indigo
        (139, 92, 246),   # #8b5cf6 Violet
        (168, 85, 247),   # #a855f7 Purple
        (192, 132, 252),
        (236, 72, 153),   # #ec4899 Pink
    ]

    for i, (h, col) in enumerate(zip(bar_heights, colors)):
        x1 = start_x + i * (bar_width + bar_spacing)
        y1 = center_y - h // 2
        x2 = x1 + bar_width
        y2 = center_y + h // 2
        # Glow around bar
        w_draw.rounded_rectangle([x1 - 10, y1 - 10, x2 + 10, y2 + 10], radius=24, fill=(*col, 50))
        # Solid bar
        w_draw.rounded_rectangle([x1, y1, x2, y2], radius=19, fill=(*col, 240))
        # White highlight dot at top
        w_draw.ellipse([x1 + 8, y1 + 6, x2 - 8, y1 + 24], fill=(255, 255, 255, 180))

    # 3. Subtitle Pill Badge at bottom
    sub_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(sub_layer)

    pill_w = 440
    pill_h = 130
    pill_x1 = (size - pill_w) // 2
    pill_y1 = int(size * 0.70)
    pill_x2 = pill_x1 + pill_w
    pill_y2 = pill_y1 + pill_h

    # Subtitle glass plate
    s_draw.rounded_rectangle([pill_x1, pill_y1, pill_x2, pill_y2], radius=32, fill=(15, 23, 42, 220), outline=(56, 189, 248, 120), width=4)
    # Inner subtitle text bars
    # First line (longer)
    s_draw.rounded_rectangle([pill_x1 + 45, pill_y1 + 32, pill_x2 - 45, pill_y1 + 52], radius=10, fill=(248, 250, 252, 240))
    # Second line (shorter)
    s_draw.rounded_rectangle([pill_x1 + 90, pill_y1 + 72, pill_x2 - 90, pill_y1 + 92], radius=10, fill=(56, 189, 248, 220))

    # Combine all layers
    composite = Image.alpha_composite(final_base, wave_layer)
    composite = Image.alpha_composite(composite, sub_layer)

    # Downsample cleanly with Lanczos to 512x512
    icon_512 = composite.resize((512, 512), Image.Resampling.LANCZOS)

    # Save PNG master
    os.makedirs("assets", exist_ok=True)
    png_path = os.path.join("assets", "app_icon.png")
    icon_512.save(png_path, "PNG")
    print(f"Saved {png_path}")

    # Generate multi-size .ico
    ico_path = os.path.join("assets", "app_icon.ico")
    icon_512.save(
        ico_path,
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    )
    print(f"Saved {ico_path}")

if __name__ == "__main__":
    create_subfynn_icon()
