from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "social"
NAVY = "#0B1420"
NAVY_2 = "#121F2F"
CARD = "#19283A"
WHITE = "#F3F7FA"
MUTED = "#A9B7C6"
MINT = "#A4EACB"
BLUE = "#8EA2FF"
LINE = "#2C3D51"


def font(size, weight="regular"):
    paths = {
        "regular": "/System/Library/Fonts/SFNS.ttf",
        "medium": "/System/Library/Fonts/SFNS.ttf",
        "bold": "/System/Library/Fonts/SFNS.ttf",
        "serif": "/System/Library/Fonts/NewYork.ttf",
    }
    try:
        return ImageFont.truetype(paths[weight], size=size)
    except OSError:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size=size)


def fit_cover(im, size):
    target_w, target_h = size
    scale = max(target_w / im.width, target_h / im.height)
    resized = im.resize((round(im.width * scale), round(im.height * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def rounded_mask(size, radius):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    return mask


def paste_rounded(canvas, im, box, radius=26, shadow=True):
    x, y, w, h = box
    fitted = fit_cover(im, (w, h))
    if shadow:
        layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(layer)
        sd.rounded_rectangle((x + 10, y + 18, x + w + 10, y + h + 18), radius=radius, fill=(0, 0, 0, 115))
        canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(18)))
    canvas.paste(fitted, (x, y), rounded_mask((w, h), radius))
    ImageDraw.Draw(canvas).rounded_rectangle((x, y, x + w, y + h), radius=radius, outline="#526176", width=2)


def wordmark(canvas, x, y, width=286):
    logo = Image.open(OUT.parent / ".." / "public" / "assets" / "tickr-digest-logo.png") if False else Image.open(ROOT / "public" / "assets" / "tickr-digest-logo.png")
    logo = logo.convert("RGBA")
    height = round(width * logo.height / logo.width)
    canvas.alpha_composite(logo.resize((width, height), Image.Resampling.LANCZOS), (x, y))


def wrap(draw, text, fnt, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        trial = word if not current else current + " " + word
        if draw.textbbox((0, 0), trial, font=fnt)[2] <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def text_block(draw, xy, text, fnt, fill, max_width, gap=8):
    x, y = xy
    for line in wrap(draw, text, fnt, max_width):
        draw.text((x, y), line, font=fnt, fill=fill)
        bbox = draw.textbbox((x, y), line, font=fnt)
        y = bbox[3] + gap
    return y


def base_portrait(use_art=True):
    if use_art:
        art = Image.open(OUT / "abstract-data-ribbon.png").convert("RGB")
        art = fit_cover(art, (1080, 1350))
        art = ImageEnhance.Brightness(art).enhance(0.68)
        overlay = Image.new("RGBA", art.size, (5, 15, 27, 90))
        art = Image.alpha_composite(art.convert("RGBA"), overlay)
        return art
    return Image.new("RGBA", (1080, 1350), NAVY)


def pill(draw, box, label, fill, fg=WHITE, size=25):
    draw.rounded_rectangle(box, radius=18, fill=fill, outline=(255, 255, 255, 22), width=1)
    f = font(size, "bold")
    l, t, r, b = draw.textbbox((0, 0), label, font=f)
    x = box[0] + (box[2] - box[0] - (r - l)) / 2
    y = box[1] + (box[3] - box[1] - (b - t)) / 2 - 2
    draw.text((x, y), label, font=f, fill=fg)


def build_ig_hero():
    canvas = base_portrait(True)
    draw = ImageDraw.Draw(canvas)
    wordmark(canvas, 64, 54, 282)
    draw.text((64, 190), "YOUR PERSONAL STOCK DASHBOARD", font=font(22, "bold"), fill=BLUE, spacing=2)
    draw.text((64, 238), "Follow your stocks.", font=font(76, "bold"), fill=WHITE)
    draw.text((64, 322), "See the whole picture.", font=font(70, "serif"), fill=MINT)
    text_block(draw, (66, 420), "Market moves, price landmarks, earnings, financial health, AI context and company news — in one clear view.", font(29), MUTED, 750, 9)

    shot = Image.open(OUT / "current-home-1080x1350.png").convert("RGB")
    crop = shot.crop((550, 145, 1055, 1015))
    paste_rounded(canvas, crop, (485, 575, 520, 700), radius=30)

    draw.rounded_rectangle((64, 1125, 428, 1198), radius=18, fill=MINT)
    draw.text((96, 1145), "Start for free  ↗", font=font(30, "bold"), fill=NAVY)
    draw.text((64, 1240), "mydailydigest.online", font=font(27, "bold"), fill=WHITE)
    draw.text((64, 1290), "Information, not investment advice.", font=font(18), fill=MUTED)
    canvas.convert("RGB").save(OUT / "tickr-instagram-01-bigger-picture.png", quality=95)


def build_ig_signals():
    canvas = base_portrait(False)
    draw = ImageDraw.Draw(canvas)
    wordmark(canvas, 64, 52, 282)
    draw.text((64, 186), "SIX SIGNALS. ONE CLEARER VIEW.", font=font(22, "bold"), fill=BLUE)
    draw.text((64, 236), "Spend less time searching.", font=font(64, "bold"), fill=WHITE)
    draw.text((64, 307), "More time understanding.", font=font(58, "serif"), fill=BLUE)

    labels = [
        ("01", "Watchlist moves"),
        ("02", "Price context"),
        ("03", "Earnings"),
        ("04", "Financial health"),
        ("05", "AI context"),
        ("06", "Company coverage"),
    ]
    for i, (icon, label) in enumerate(labels):
        col, row = i % 2, i // 2
        x, y = 64 + col * 485, 440 + row * 152
        draw.rounded_rectangle((x, y, x + 450, y + 118), radius=20, fill=CARD, outline=LINE, width=2)
        draw.rounded_rectangle((x + 22, y + 24, x + 88, y + 90), radius=15, fill="#27385B")
        draw.text((x + 55, y + 57), icon, font=font(22, "bold"), fill=BLUE, anchor="mm")
        draw.text((x + 112, y + 40), label.upper(), font=font(20, "bold"), fill=MUTED)
        draw.text((x + 112, y + 72), "In your dashboard", font=font(24, "bold"), fill=WHITE)

    draw.rounded_rectangle((64, 940, 1016, 1117), radius=25, fill="#29294D", outline="#5B56A1", width=2)
    draw.text((94, 972), "AI CONTEXT", font=font(20, "bold"), fill=BLUE)
    draw.text((94, 1018), "Connect the themes across your watchlist.", font=font(32, "serif"), fill=WHITE)
    draw.text((64, 1185), "One sign-in. Check in anytime.", font=font(33, "bold"), fill=WHITE)
    draw.text((64, 1240), "mydailydigest.online", font=font(27, "bold"), fill=MINT)
    draw.text((64, 1290), "Illustrative examples. Market data may be delayed.", font=font(18), fill=MUTED)
    canvas.convert("RGB").save(OUT / "tickr-instagram-02-six-signals.png", quality=95)


def build_linkedin():
    w, h = 1200, 627
    art = Image.open(OUT / "abstract-data-ribbon.png").convert("RGB")
    art = fit_cover(art, (w, h))
    art = ImageEnhance.Brightness(art).enhance(0.45).convert("RGBA")
    canvas = Image.alpha_composite(art, Image.new("RGBA", (w, h), (3, 12, 22, 82)))
    draw = ImageDraw.Draw(canvas)
    wordmark(canvas, 56, 42, 240)
    draw.text((56, 156), "TWO MARKETS. ONE DASHBOARD.", font=font(18, "bold"), fill=BLUE)
    draw.text((56, 196), "From Wall Street", font=font(55, "bold"), fill=WHITE)
    draw.text((56, 254), "to Dalal Street.", font=font(54, "serif"), fill=MINT)
    text_block(draw, (58, 342), "Follow US stocks, ETFs and NSE equities in one personal watchlist.", font(25), MUTED, 470, 7)
    pill(draw, (58, 438, 230, 492), "NYSE + NASDAQ", "#23334A", size=19)
    pill(draw, (246, 438, 357, 492), "NSE", "#1C5945", fg=MINT, size=20)
    draw.text((58, 542), "Open anytime  •  Free to start", font=font(24, "bold"), fill=WHITE)
    draw.text((58, 582), "mydailydigest.online", font=font(21, "bold"), fill=MINT)

    shot = Image.open(OUT / "current-home-1080x1350.png").convert("RGB")
    crop = shot.crop((575, 180, 1048, 755))
    paste_rounded(canvas, crop, (690, 56, 442, 535), radius=24)
    canvas.convert("RGB").save(OUT / "tickr-linkedin-01-us-india.png", quality=95)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    build_ig_hero()
    build_ig_signals()
    build_linkedin()
    print("Built 3 social visuals in", OUT)
