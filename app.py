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
        print("DEBUG START: Image generation request")
        r = requests.get('https://d2emu.com/tz', timeout=10)
        print(f"DEBUG: d2emu response code = {r.status_code}")

        if r.status_code == 200:
            text = r.text.upper()
            print("DEBUG: Text fetched - length", len(text))

            # Minimal clean
            text = re.sub(r'<SCRIPT.*?</SCRIPT>', '', text, flags=re.DOTALL | re.IGNORECASE)

            lines = text.splitlines()

            current_zones = []
            next_zones = []
            past_dash = False

            for line in lines:
                line = line.strip()
                if '|' not in line:
                    continue

                print(f"DEBUG ROW: {line}")

                parts = line.split('|')
                if len(parts) < 3:
                    continue

                zone_part = parts[2].strip()  # zones here

                if zone_part:
                    print(f"DEBUG CELL: '{zone_part}'")

                    if '---' in zone_part:
                        past_dash = True
                        print("DEBUG: Dash separator - next zones incoming")
                        continue

                    # Accept if has spaces or looks like zone
                    if ' ' in zone_part or len(zone_part.split()) > 0:
                        if not past_dash:
                            current_zones.append(zone_part)
                            print(f"DEBUG: Current += '{zone_part}'")
                        else:
                            next_zones.append(zone_part)
                            print(f"DEBUG: Next += '{zone_part}'")

            if current_zones:
                current = ' + '.join(current_zones)
                print(f"DEBUG FINAL CURRENT: {current}")
            if next_zones:
                next_zone = ' + '.join(next_zones)
                print(f"DEBUG FINAL NEXT: {next_zone}")

    except Exception as e:
        print(f"DEBUG ERROR: {str(e)}")
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
