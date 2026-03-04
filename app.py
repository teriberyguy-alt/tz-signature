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

            # Log raw fetch for debug (check Render logs)
            print("DEBUG RAW FETCH START ---")
            print(text[500:2000])  # Mid-page chunk to catch zones
            print("DEBUG RAW FETCH END ---")

            # Remove script/style tags and junk to clean
            text = re.sub(r'<SCRIPT.*?</SCRIPT>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<STYLE.*?</STYLE>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'\{[^}]*\}', '', text)  # Strip CSS blocks
            text = re.sub(r'POSITION:|DISPLAY:|CURSOR:|VISIBILITY:|COLOR:|BACKGROUND:|TEXT-ALIGN:', '', text)

            lines = [line.strip() for line in text.splitlines() if line.strip() and len(line) > 5]

            collecting_current = False
            collecting_next = False
            current_lines = []
            next_lines = []

            for line in lines:
                if 'CURRENT TERROR ZONE' in line or 'CURRENT ZONE' in line:
                    collecting_current = True
                    collecting_next = False
                    continue
                if 'NEXT TERROR ZONE' in line or 'NEXT ZONE' in line:
                    collecting_current = False
                    collecting_next = True
                    continue

                # Zone pattern: capitalized words, possibly with + or | separators, no CSS junk
                if re.match(r'^[A-Z0-9][A-Z\s\'\-]+(?:\s+[A-Z0-9][A-Z\s\'\-]+)*$', line):
                    if collecting_current:
                        current_lines.append(line)
                    elif collecting_next:
                        next_lines.append(line)
                    elif not collecting_current and not collecting_next and '|' not in line:  # Fallback for table rows
                        if len(current_lines) < 3:
                            current_lines.append(line)
                        elif len(next_lines) < 3:
                            next_lines.append(line)

            if current_lines:
                current = ' + '.join(current_lines)
            if next_lines:
                next_zone = ' + '.join(next_lines)

            # Final cleanup
            current = re.sub(r'\s+', ' ', current).strip()
            next_zone = re.sub(r'\s+', ' ', next_zone).strip()
            if 'SPIDER FOREST' in current or 'STONY FIELD' in current:  # Known good
                pass
            elif len(current) < 10:
                current = 'PENDING'

    except Exception as e:
        print(f"Fetch error: {str(e)}")
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

    # Load bg and draw
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
