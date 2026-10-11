#!/usr/bin/env python3
"""Erzeugt die Social-Media-Bilder (Link-Vorschau und Profilbild) mit dem finalen Logo nach site/social/."""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sellcheck_logo as L  # noqa: E402

OUT = os.path.join(HERE, "..", "..", "site", "social")
FONT = L.FONT


def font(idx, size):
    return ImageFont.truetype(FONT, size, index=idx)


def og_image():
    W, H = 1200, 630
    im = Image.new("RGB", (W, H), L.INK)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([1040 - 360, 560 - 360, 1040 + 360, 560 + 360], fill=(*L.LIME, 26))
    im.paste(glow, (0, 0), glow)
    d = ImageDraw.Draw(im)
    L.draw_lockup(d, 80, 70, 84, True)
    d.text((80, 360), "Check, was", font=font(1, 92), fill=L.PAPER, anchor="ls")
    d.text((80, 460), "wirklich bleibt.", font=font(1, 92), fill=L.LIME, anchor="ls")
    d.text((80, 548), "Vinted · Kleinanzeigen · eBay · Etsy · Amazon · bar", font=font(10, 32), fill=(162, 168, 179), anchor="ls")
    im.save(os.path.join(OUT, "og-image.png"))


def profile():
    im = Image.new("RGB", (800, 800), L.LIME)
    h = 440
    L.draw_mark(ImageDraw.Draw(im), (800 - L.mark_width(h)) / 2, (800 - h) / 2, h, False)
    im.save(os.path.join(OUT, "profilbild.png"))


def svgs():
    pts = " ".join(f"{a},{b}" for a, b in L.RECEIPT)
    cp = " ".join(f"{a},{b}" for a, b in L.CHECK)

    def mark(x, y, s, fill, chk):
        return (f'<g transform="translate({x} {y}) scale({s})"><polygon points="{pts}" fill="{fill}" stroke="{fill}" stroke-width="{L.STROKE}" stroke-linejoin="round"/>'
                f'<polyline points="{cp}" fill="none" stroke="{chk}" stroke-width="6.4" stroke-linecap="round" stroke-linejoin="round"/></g>')
    ff = "'Helvetica Neue',Helvetica,Arial,sans-serif"
    og = (f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="420" viewBox="0 0 1200 630">'
          f'<rect width="1200" height="630" fill="#0E1116"/><circle cx="1040" cy="560" r="360" fill="#C8F169" opacity="0.10"/>'
          f'{mark(70, 60, 1.6, "#C8F169", "#0E1116")}'
          f'<text x="190" y="130" font-family="{ff}" font-size="80" font-weight="700" letter-spacing="-2.8" fill="#F6F4EE">Sell<tspan fill="#C8F169">Check</tspan></text>'
          f'<text x="80" y="360" font-family="{ff}" font-size="92" font-weight="700" fill="#F6F4EE">Check, was</text>'
          f'<text x="80" y="460" font-family="{ff}" font-size="92" font-weight="700" fill="#C8F169">wirklich bleibt.</text>'
          f'<text x="80" y="548" font-family="{ff}" font-size="32" font-weight="500" fill="#A2A8B3">Vinted · Kleinanzeigen · eBay · Etsy · Amazon · bar</text></svg>')
    open(os.path.join(OUT, "og-image.svg"), "w", encoding="utf-8").write(og)
    pf = (f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="800" viewBox="0 0 800 800"><rect width="800" height="800" fill="#C8F169"/>'
          f'{mark(190, 80, 11, "#0E1116", "#C8F169")}</svg>')
    open(os.path.join(OUT, "profilbild.svg"), "w", encoding="utf-8").write(pf)


if __name__ == "__main__":
    og_image()
    profile()
    svgs()
    print("Social-Bilder geschrieben")
