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
    print("DEBUG: Route hit at", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))

    current = 'PENDING'
    next_zone = 'PENDING'
    countdown = 'PENDING'

    try:
        r = requests.get('https://d2emu.com/tz', timeout=10)
        print(f"DEBUG: d2emu fetch status: {r.status_code}")

        if r.status_code == 200:
            text = r.text.upper()

            # Remove script junk
            text = re.sub(r'<SCRIPT.*?</SCRIPT>', '', text, flags=re.DOTALL | re.IGNORECASE)

            lines = text.splitlines()
            current_zones = []
            next_zones = []
            past_separator = False

            for line in lines:
                line = line.strip()
                if '|' not in line:
                    continue

                parts = line.split('|')
                if len(parts) < 3:
                    continue

                zone_part = parts[2].strip()  # zone is in third part

                if not zone_part:
                    continue

                if '---' in zone_part:
                    past_separator = True
                    continue

                # Accept zone-like strings (caps, spaces/commas)
                if zone_part[0].isupper() and len(zone_part.split()) > 0:
                    if not past_separator:
                        current_zones.append(zone_part)
                    else:
                        next_zones.append(zone_part)

            if current_zones:
                current = ' + '.join(current_zones)
            if next_zones:
                next_zone = ' + '.join(next_zones)

            print(f"DEBUG: Parsed zones - current: '{current}' | next: '{next_zone}'")

    except Exception as e:
        print(f"Fetch/parse error: {str(e)}")

    # Fallback countdown
    if countdown == 'PENDING':
        now = datetime.now(timezone.utc)
        minutes = now.minute
        seconds = now.second
        mins_to_next = 30 - (minutes % 30)
        secs_to_next = mins_to_next * 60 - seconds
        if secs_to_next < 0:
            secs_to_next += 3600
        countdown = f"{secs_to_next // 60} MIN {secs_to_next % 60:02d} SEC UNTIL NEXT"
        if secs_to_next < 60:
            countdown = f"{secs_to_next} SEC UNTIL NEXT"

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
        for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
            draw.text((x + dx, y + dy), text, font=font_obj, fill="black")
        draw.text((x, y), text, fill=fill, font=font_obj)

    y = 45
    draw_outlined_text(10, y, "CURRENT ZONE:", (255, 255, 255), font)
    y += 22
    for part in [current[i:i+45] for i in range(0, len(current), 45)]:
        draw_outlined_text(15, y, part, (255, 255, 255), font)
        y += 18

    y += 10
    draw_outlined_text(10, y, countdown, (255, 215, 0), timer_font)
    y += 25

    draw_outlined_text(10, y, "NEXT ZONE:", (255, 255, 255), font)
    y += 22
    for part in [next_zone[i:i+45] for i in range(0, len(next_zone), 45)]:
        draw_outlined_text(15, y, part, (255, 255, 255), font)
        y += 18

    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return Response(buf, mimetype='image/png', headers={'Cache-Control': 'no-cache, no-store'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
