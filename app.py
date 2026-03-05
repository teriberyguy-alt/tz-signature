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
        print("DEBUG: --- New request for signature.png ---")
        r = requests.get('https://d2emu.com/tz', timeout=10)
        print(f"DEBUG: Fetch status: {r.status_code}")

        if r.status_code == 200:
            text = r.text.upper()

            # Clean junk
            text = re.sub(r'<SCRIPT.*?</SCRIPT>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<STYLE.*?</STYLE>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'\{[^}]*\}', '', text)

            lines = text.splitlines()
            print("DEBUG: Looking for table lines with |")

            current_zones = []
            next_zones = []
            past_separator = False

            for line in lines:
                line = line.strip()
                if '|' not in line:
                    continue

                print(f"DEBUG: Table line found: '{line}'")  # Log every table row

                cells = [cell.strip() for cell in line.split('|') if cell.strip()]

                if len(cells) == 0:
                    continue

                zone_str = ' '.join(cells)

                if '---' in zone_str:
                    past_separator = True
                    print("DEBUG: Separator row detected")
                    continue

                # Accept almost any reasonable zone string (multiple words, capitalized)
                if len(zone_str.split()) >= 1 and not any(kw in zone_str for kw in ['IMMUN', 'DATE', 'TERROR', 'ZONE', 'WINDOW', 'DATALAYER', 'GTAG']):
                    print(f"DEBUG: Captured potential zone: '{zone_str}'")
                    if not past_separator:
                        current_zones.append(zone_str)
                    else:
                        next_zones.append(zone_str)

            if current_zones:
                current = ' + '.join(current_zones)
                print(f"DEBUG: Final current zones: {current}")
            if next_zones:
                next_zone = ' + '.join(next_zones)
                print(f"DEBUG: Final next zones: {next_zone}")

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

    # Image setup
    bg_path = 'bg.jpg'
    if not os.path.exists(bg_path):
        return "bg.jpg missing", 500

    img = Image.open(bg_path).convert('RGBA')
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype('font.ttf', 11)
        timer_font = ImageFont.truetype('font.ttf', 12)
    except:
        font = ImageFont.load_default()
        timer_font = font

    def draw_outlined_text(x, y, text, fill, font_obj):
        for dx, dy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
            draw.text((x + dx, y + dy), text, font=font_obj, fill="black")
        draw.text((x, y), text, fill=fill, font=font_obj)

    y = 50
    draw_outlined_text(10, y, "CURRENT ZONE:", (255, 255, 255), font)
    y += 20
    for part in [current[i:i+26] for i in range(0, len(current), 26)]:
        draw_outlined_text(15, y, part, (255, 255, 255), font)
        y += 16

    y += 8
    draw_outlined_text(10, y, countdown, (255, 215, 0), timer_font)
    y += 22

    draw_outlined_text(10, y, "NEXT ZONE:", (255, 255, 255), font)
    y += 20
    for part in [next_zone[i:i+26] for i in range(0, len(next_zone), 26)]:
        draw_outlined_text(15, y, part, (255, 255, 255), font)
        y += 16

    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return Response(buf, mimetype='image/png', headers={'Cache-Control': 'no-cache, no-store'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
