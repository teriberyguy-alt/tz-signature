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
        print("DEBUG: Image request received")
        r = requests.get('https://d2emu.com/tz', timeout=10)
        print(f"DEBUG: d2emu fetch status: {r.status_code}")

        if r.status_code == 200:
            text = r.text.upper()

            # Clean minimal junk
            text = re.sub(r'<SCRIPT.*?</SCRIPT>', '', text, flags=re.DOTALL | re.IGNORECASE)

            lines = text.splitlines()
            print("DEBUG: Searching for | table rows")

            current_zones = []
            next_zones = []
            past_separator = False

            for line in lines:
                line = line.strip()
                if '|' not in line:
                    continue

                print(f"DEBUG: Raw row: {line}")

                parts = line.split('|')
                if len(parts) < 3:
                    continue

                zone_cell = parts[2].strip()  # zones are in third part

                if not zone_cell:
                    continue

                print(f"DEBUG: Zone cell: '{zone_cell}'")

                if '---' in zone_cell:
                    past_separator = True
                    print("DEBUG: --- separator - now next")
                    continue

                # Accept zone cells (spaces, capital words)
                if len(zone_cell) > 5 and ' ' in zone_cell:
                    print(f"DEBUG: Accepted zone: '{zone_cell}'")
                    if not past_separator:
                        current_zones.append(zone_cell)
                    else:
                        next_zones.append(zone_cell)

            if current_zones:
                current = ' + '.join(current_zones)
                print(f"DEBUG: Current zones: {current}")
            if next_zones:
                next_zone = ' + '.join(next_zones)
                print(f"DEBUG: Next zones: {next_zone}")

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
        font = ImageFont.truetype('font.ttf', 10)
        timer_font = ImageFont.truetype('font.ttf', 11)
    except:
        font = ImageFont.load_default()
        timer_font = font

    def draw_outlined_text(x, y, text, fill, font_obj):
        for dx, dy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
            draw.text((x + dx, y + dy), text, font=font_obj, fill="black")
        draw.text((x, y), text, fill=fill, font=font_obj)

    y = 55
    draw_outlined_text(10, y, "CURRENT ZONE:", (255, 255, 255), font)
    y += 18
    for part in [current[i:i+25] for i in range(0, len(current), 25)]:
        draw_outlined_text(15, y, part, (255, 255, 255), font)
        y += 15

    y += 5
    draw_outlined_text(10, y, countdown, (255, 215, 0), timer_font)
    y += 20

    draw_outlined_text(10, y, "NEXT ZONE:", (255, 255, 255), font)
    y += 18
    for part in [next_zone[i:i+25] for i in range(0, len(next_zone), 25)]:
        draw_outlined_text(15, y, part, (255, 255, 255), font)
        y += 15

    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return Response(buf, mimetype='image/png', headers={'Cache-Control': 'no-cache, no-store'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
