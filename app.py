from flask import Flask, Response
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
from datetime import datetime, timezone
import os

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

            print("DEBUG: Fetch OK - scanning for | table")

            current_zones = []
            next_zones = []
            separator_seen = False

            for line in lines:
                line = line.strip()
                if not line or '|' not in line:
                    continue

                parts = [p.strip() for p in line.split('|') if p.strip()]

                if len(parts) < 2:
                    continue

                zone_text = parts[-1]  # Last cell is the zones

                if '---' in zone_text or len(zone_text) < 5:
                    separator_seen = True
                    continue

                # Clean zone text (remove extra spaces)
                zone_text = ' '.join(zone_text.split())

                if zone_text:
                    if not separator_seen:
                        current_zones.append(zone_text)
                    else:
                        next_zones.append(zone_text)

            if current_zones:
                current = ' + '.join(current_zones)
            if next_zones:
                next_zone = ' + '.join(next_zones)

            print(f"DEBUG parsed current: '{current}'")
            print(f"DEBUG parsed next: '{next_zone}'")

    except Exception as e:
        print(f"ERROR: {str(e)}")
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
        font = ImageFont.truetype('font.ttf', 12)
        timer_font = ImageFont.truetype('font.ttf', 13)
    except:
        font = ImageFont.load_default()
        timer_font = font

    def draw_outlined_text(x, y, text, fill, font_obj):
        for dx, dy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
            draw.text((x + dx, y + dy), text, font=font_obj, fill="black")
        draw.text((x, y), text, fill=fill, font=font_obj)

    y = 45
    draw_outlined_text(10, y, "CURRENT ZONE:", (255, 255, 255), font)
    y += 22
    for part in [current[i:i+30] for i in range(0, len(current), 30)]:
        draw_outlined_text(15, y, part, (255, 255, 255), font)
        y += 18

    y += 12
    draw_outlined_text(10, y, countdown, (255, 215, 0), timer_font)
    y += 28

    draw_outlined_text(10, y, "NEXT ZONE:", (255, 255, 255), font)
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
