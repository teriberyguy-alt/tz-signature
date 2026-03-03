from flask import Flask, Response, request
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import datetime
import os

app = Flask(__name__)

@app.route('/signature.png')
def signature():
    # Fetch TZ data
    try:
        r = requests.get('https://d2emu.com/tz', timeout=5)
        text = r.text.upper()
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        current_zones = []
        next_zones = []
        collecting_current = False
        collecting_next = False

        for line in lines:
            if 'CURRENT TERROR ZONE' in line or 'CURRENT' in line:
                collecting_current = True
                collecting_next = False
                continue
            if 'NEXT TERROR ZONE' in line or 'NEXT' in line:
                collecting_current = False
                collecting_next = True
                continue
            if collecting_current and not any(k in line for k in ['IMMUN', 'DATE']):
                current_zones.extend(line.split())
            if collecting_next and not any(k in line for k in ['IMMUN', 'DATE']):
                next_zones.extend(line.split())

        current = ' + '.join(current_zones) if current_zones else 'PENDING'
        next_zone = ' + '.join(next_zones) if next_zones else 'PENDING'

    except Exception as e:
        current = next_zone = 'ERROR'

    # Countdown
    now = datetime.datetime.utcnow()
    mins = now.minute
    secs = now.second
    mins_to_next = 30 - (mins % 30)
    secs_to_next = mins_to_next * 60 - secs
    if secs_to_next < 0:
        secs_to_next += 3600
    countdown = f"{secs_to_next // 60} min {secs_to_next % 60:02d} sec until next"

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

    # Draw (adjust coords/sizes to fit your bg)
    y = 30
    draw.text((10, y), "Current Zone:", fill="white", font=font, stroke_width=2, stroke_fill="black")
    y += 25
    for line in [current[i:i+35] for i in range(0, len(current), 35)]:
        draw.text((15, y), line, fill="white", font=font, stroke_width=2, stroke_fill="black")
        y += 20

    y += 15
    draw.text((10, y), countdown, fill=(255, 215, 0), font=timer_font, stroke_width=2, stroke_fill="black")
    y += 30

    draw.text((10, y), "Next Zone:", fill="white", font=font, stroke_width=2, stroke_fill="black")
    y += 25
    for line in [next_zone[i:i+35] for i in range(0, len(next_zone), 35)]:
        draw.text((15, y), line, fill="white", font=font, stroke_width=2, stroke_fill="black")
        y += 20

    # Serve PNG
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return Response(buf, mimetype='image/png', headers={'Cache-Control': 'no-cache'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
