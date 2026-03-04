from flask import Flask, Response
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import datetime
import os
from datetime import timezone

app = Flask(__name__)

@app.route('/signature.png')
def signature():
    # Fetch TZ data
    current = 'PENDING'
    next_zone = 'PENDING'
    try:
        r = requests.get('https://d2emu.com/tz', timeout=8)
        if r.status_code == 200:
            text = r.text.upper()
            lines = [line.strip() for line in text.splitlines() if line.strip()]

            zones_blocks = []
            current_block = []

            for line in lines:
                # Skip obvious non-zone lines (headers, dashes, empty, short words, known junk)
                if len(line) < 8 or 'TERROR' in line or 'ZONE' in line or 'IMMUN' in line or '-----' in line or line.startswith('#'):
                    if current_block:
                        zones_blocks.append(current_block)
                        current_block = []
                    continue

                # Likely a zone name: multiple words, capitalized, no ':' or buttons
                words = line.split()
                if len(words) >= 1 and all(w[0].isupper() or w.isdigit() for w in words if len(w) > 2):
                    current_block.append(line)

            if current_block:
                zones_blocks.append(current_block)

            # First block = current, second = next (common pattern on the page)
            if len(zones_blocks) >= 1:
                current = ' + '.join(zones_blocks[0])
            if len(zones_blocks) >= 2:
                next_zone = ' + '.join(zones_blocks[1])

            # Fallback cleanup: if parsing grabbed junk, reset
            if 'BUTTON' in current or 'NAV' in current or 'PROFILE' in current:
                current = 'PENDING'
            if 'BUTTON' in next_zone or 'NAV' in next_zone or 'PROFILE' in next_zone:
                next_zone = 'PENDING'

    except Exception:
        current = next_zone = 'FETCH ERROR'

    # 30-minute countdown (to next :00 or :30 UTC)
    now = datetime.datetime.now(timezone.utc)
    minutes = now.minute
    seconds = now.second
    mins_to_next = 30 - (minutes % 30)
    secs_to_next = mins_to_next * 60 - seconds
    if secs_to_next < 0:
        secs_to_next += 3600
    countdown = f"{secs_to_next // 60} min {secs_to_next % 60:02d} sec until next"
    if secs_to_next <= 60:
        countdown = f"{secs_to_next} sec until next"

    # Load background
    bg_path = 'bg.jpg'
    if not os.path.exists(bg_path):
        return "bg.jpg missing", 500

    img = Image.open(bg_path).convert('RGBA')
    draw = ImageDraw.Draw(img)

    # Try to load custom font, fallback to default
    try:
        font = ImageFont.truetype('font.ttf', 14)
        timer_font = ImageFont.truetype('font.ttf', 16)
    except IOError:
        font = ImageFont.load_default()
        timer_font = font

    # Draw text with outline/shadow for readability
    def draw_outlined_text(x, y, text, fill, font_obj):
        # Outline (black)
        for dx, dy in [(-2, -2), (-2, 2), (2, -2), (2, 2), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
            draw.text((x + dx, y + dy), text, font=font_obj, fill="black")
        # Main text
        draw.text((x, y), text, fill=fill, font=font_obj)

    y = 30
    draw_outlined_text(10, y, "Current Zone:", "white", font)
    y += 28
    for part in [current[i:i+38] for i in range(0, len(current), 38)]:
        draw_outlined_text(15, y, part, "white", font)
        y += 22

    y += 15
    draw_outlined_text(10, y, countdown, (255, 215, 0), timer_font)
    y += 35

    draw_outlined_text(10, y, "Next Zone:", "white", font)
    y += 28
    for part in [next_zone[i:i+38] for i in range(0, len(next_zone), 38)]:
        draw_outlined_text(15, y, part, "white", font)
        y += 22

    # Serve as PNG
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return Response(buf, mimetype='image/png', headers={'Cache-Control': 'no-cache, no-store'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
