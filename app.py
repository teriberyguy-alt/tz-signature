from flask import Flask, Response
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
from datetime import datetime, timezone
import os
import re

app = Flask(__name__)

@app.route('/signature.png')
def signature():
    current = 'PENDING'
    next_zone = 'PENDING'
    try:
        r = requests.get('https://d2emu.com/tz', timeout=10)
        if r.status_code == 200:
            text = r.text.upper()
            lines = [line.strip() for line in text.splitlines() if line.strip()]

            print("DEBUG FETCH START ---")  # For Render logs
            print(text[:800])  # Log first chunk to see what's coming
            print("DEBUG FETCH END ---")

            current_block = []
            next_block = []
            collecting_current = True  # Assume first valid block is current
            collecting_next = False

            junk_keywords = ['GTAG', 'DATALAYER', 'FUNCTION', 'DIV', 'BUTTON', 'NAV', 'PROFILE', 'ICON', 'SCRIPT', 'NEW DATE', 'PUSH', 'GOOGLE']

            for line in lines:
                # Skip junk/script lines entirely
                if any(kw in line for kw in junk_keywords) or re.search(r'[<{}(]', line) or len(line) < 8:
                    continue

                # Look for zone-like lines: multiple capitalized words, no junk
                words = line.split()
                if len(words) >= 2 and all(w[0].isupper() or w.isdigit() or '-' in w for w in words):
                    # Check if it's a header (skip it)
                    if 'TERROR' in line or 'ZONE' in line or 'IMMUN' in line or 'DATE' in line:
                        if 'NEXT' in line:
                            collecting_current = False
                            collecting_next = True
                        continue

                    # Add to current or next block
                    zone_str = ' '.join(words)
                    if collecting_current:
                        current_block.append(zone_str)
                    elif collecting_next:
                        next_block.append(zone_str)

            if current_block:
                current = ' + '.join(current_block)
            if next_block:
                next_zone = ' + '.join(next_block)

            # Cleanup if junk slipped in
            if len(current) < 10 or 'ERROR' in current:
                current = 'PENDING'
            if len(next_zone) < 10 or 'ERROR' in next_zone:
                next_zone = 'PENDING'

    except Exception as e:
        print(f"Fetch failed: {e}")
        current = next_zone = 'FETCH ERROR'

    # Countdown
    now = datetime.now(timezone.utc)
    minutes = now.minute
    seconds = now.second
    mins_to_next = 30 - (minutes % 30)
    secs_to_next = mins_to_next * 60 - seconds
    if secs_to_next < 0:
        secs_to_next += 3600
    countdown = f"{secs_to_next // 60} min {secs_to_next % 60:02d} sec until next"
    if secs_to_next < 60:
        countdown = f"{secs_to_next} sec until next"

    # Load bg
    bg_path = 'bg.jpg'
    if not os.path.exists(bg_path):
        return "bg.jpg missing", 500

    img = Image.open(bg_path).convert('RGBA')
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype('font.ttf', 14)
        timer_font = ImageFont.truetype('font.ttf', 16)
    except:
        font = ImageFont.load_default()
        timer_font = font

    # Draw with outline
    def draw_outlined_text(x, y, text, fill, font_obj):
        for dx, dy in [(-2,-2),(-2,2),(2,-2),(2,2),(-1,-1),(-1,1),(1,-1),(1,1)]:
            draw.text((x + dx, y + dy), text, font=font_obj, fill="black")
        draw.text((x, y), text, fill=fill, font=font_obj)

    y = 30
    draw_outlined_text(10, y, "Current Zone:", "white", font)
    y += 28
    for part in [current[i:i+35] for i in range(0, len(current), 35)]:
        draw_outlined_text(15, y, part, "white", font)
        y += 22

    y += 15
    draw_outlined_text(10, y, countdown, (255, 215, 0), timer_font)
    y += 35

    draw_outlined_text(10, y, "Next Zone:", "white", font)
    y += 28
    for part in [next_zone[i:i+35] for i in range(0, len(next_zone), 35)]:
        draw_outlined_text(15, y, part, "white", font)
        y += 22

    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return Response(buf, mimetype='image/png', headers={'Cache-Control': 'no-cache, no-store'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
