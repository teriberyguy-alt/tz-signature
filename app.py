from flask import Flask, Response
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
from datetime import datetime, timezone
import os
import easyocr
import re

app = Flask(__name__)

reader = easyocr.Reader(['en'], gpu=False)  # English only, no GPU needed on Render

@app.route('/signature.png')
def signature():
    current = 'PENDING'
    next_zone = 'PENDING'
    countdown = 'PENDING'

    try:
        # Fetch clean TZ image from d2tz (no tier, decent size)
        tz_url = "https://api.d2tz.info/public/tz_image?t=none&width=500"
        r = requests.get(tz_url, timeout=10)
        if r.status_code == 200:
            tz_img = Image.open(BytesIO(r.content))
            tz_img.save('temp_tz.png')  # Temp save for OCR

            # OCR read text
            result = reader.readtext('temp_tz.png', detail=0, paragraph=True)
            full_text = ' '.join(result).upper()

            # Extract sections
            current_match = re.search(r'CURRENT ZONE:([^NEXT]+)', full_text, re.IGNORECASE | re.DOTALL)
            next_match = re.search(r'NEXT ZONE:(.+)', full_text, re.IGNORECASE | re.DOTALL)
            countdown_match = re.search(r'(\d+ MIN \d+ SEC UNTIL NEXT|\d+ SEC UNTIL NEXT)', full_text, re.IGNORECASE)

            if current_match:
                current = current_match.group(1).strip().replace('\n', ' ').replace('  ', ' ')
            if next_match:
                next_zone = next_match.group(1).strip().replace('\n', ' ').replace('  ', ' ')
            if countdown_match:
                countdown = countdown_match.group(1).strip()

            os.remove('temp_tz.png')  # Clean up

    except Exception as e:
        print(f"OCR/fetch error: {e}")

    # Your original countdown fallback (if OCR misses timer)
    if countdown == 'PENDING':
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

    # Load your bg and draw
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

    y += 10
    draw_outlined_text(10, y, countdown, (255, 215, 0), timer_font)
    y += 25

    draw_outlined_text(10, y, "NEXT ZONE:", (255, 255, 255), font)
    y += 22
    for part in [next_zone[i:i+30] for i in range(0, len(next_zone), 30)]:
        draw_outlined_text(15, y, part, (255, 255, 255), font)
        y += 18

    # Add your watermark if you had one
    draw_outlined_text(img.width - 100, img.height - 30, "Guy_T", (200, 200, 200), font)

    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return Response(buf, mimetype='image/png', headers={'Cache-Control': 'no-cache, no-store'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
