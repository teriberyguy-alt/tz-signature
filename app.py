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
            lines = text.splitlines()

            # Debug: Log relevant parts
            print("DEBUG: Fetch status 200 - looking for table lines")

            current_zones = []
            next_zones = []
            in_table = False
            separator_seen = False

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if '|' in line:
                    in_table = True
                    parts = [p.strip() for p in line.split('|') if p.strip()]

                    if len(parts) >= 2:
                        zone_text = parts[-1].strip()  # Last part is zones

                        if '---' in zone_text or 'DASH' in zone_text:
                            separator_seen = True
                            continue

                        if zone_text and all(word[0].isupper() or word.isdigit() or "'" in word for word in zone_text.split()):
                            if not separator_seen:
                                current_zones.append(zone_text)
                            else:
                                next_zones.append(zone_text)

            if current_zones:
                current = ' + '.join(current_zones)
            if next_zones:
                next_zone = ' + '.join(next_zones)

            print(f"DEBUG: Parsed current: {current}")
            print(f"DEBUG: Parsed next: {next_zone}")

    except Exception as e:
        print(f"ERROR: Fetch/parse failed - {str(e)}")
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

    # Image
    bg_path = 'bg.jpg'
    if not os.path.exists(bg_path):
        return "bg.jpg missing", 500

    img = Image.open(bg_path).convert('RGBA')
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype('font.ttf', 12)  # Smaller to prevent overflow
        timer_font = ImageFont.truetype('font.ttf', 13)
    except:
        font = ImageFont.load_default()
        timer_font = font

    def draw_outlined_text(x, y, text, fill, font_obj):
        for dx, dy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
            draw.text((x + dx, y + dy), text, font=font_obj, fill="black")
        draw.text((x, y), text, fill=fill, font=font_obj)

    y = 40  # Adjusted start
    draw_outlined_text(10, y, "Current Zone:", (255, 255, 255), font)
    y += 22
    for part in [current[i:i+30] for i in range(0, len(current), 30)]:  # Tighter wrap
        draw_outlined_text(15, y, part, (255, 255, 255), font)
        y += 18

    y += 10
    draw_outlined_text(10, y, countdown, (255, 215, 0), timer_font)
    y += 25

    draw_outlined_text(10, y, "Next Zone:", (255, 255, 255), font)
    y += 22
    for part in [next_zone[i:i+30] for i in range(0, len(next_zone), 30)]:
        draw_outlined_text(15, y, part, (255, 255, 255), font)
        y += 18

    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return Response(buf, mimetype='image/png', headers={'Cache-Control': 'no-cache, no-store'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
