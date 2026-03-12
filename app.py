from flask import Flask, Response
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
from datetime import datetime, timezone
import os
import json

app = Flask(__name__)

@app.route('/signature.png')
def signature():
    current = 'PENDING'
    next_zone = 'PENDING'
    countdown = 'PENDING'

    try:
        # Fetch JSON from d2tz.info API
        api_url = "https://www.d2tz.info/api/current"  # or /api/tz if different
        r = requests.get(api_url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            print("DEBUG: API response:", json.dumps(data, indent=2))  # Log for Render

            # Adjust keys based on actual response (check logs)
            current = data.get('current', 'PENDING').upper()
            next_zone = data.get('next', 'PENDING').upper()
            countdown = data.get('time_remaining', 'PENDING')  # or 'countdown'

            # Clean up if needed
            current = current.replace(',', ', ').strip()
            next_zone = next_zone.replace(',', ', ').strip()

    except Exception as e:
        print(f"API error: {str(e)}")

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

    # Load bg.jpg (title + Guy_T baked in)
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

    y = 45  # Adjust if needed to fit bg
    draw_outlined_text(10, y, "CURRENT ZONE:", (255, 255, 255), font)
    y += 22
    for part in [current[i:i+30] for i in range(0, len(current), 30)]:
        draw_outlined_text(15, y, part, (255, 255, 255), font)
        y += 18

    y += 10
    draw_outlined_text(10, y, countdown, (255, 215, 0), timer_font)
    y += 25

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
