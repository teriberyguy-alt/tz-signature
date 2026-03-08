from flask import Flask, Response
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
from datetime import datetime, timezone
import os
import pytesseract
import re

app = Flask(__name__)

@app.route('/signature.png')
def signature():
    current = 'PENDING'
    next_zone = 'PENDING'
    countdown = 'PENDING'

    try:
        # Fetch the clean TZ image from d2tz.info
        tz_url = "https://api.d2tz.info/public/tz_image?t=none&width=500"
        r = requests.get(tz_url, timeout=15)
        if r.status_code == 200:
            tz_img = Image.open(BytesIO(r.content)).convert('L')  # Grayscale → better OCR accuracy

            # Perform OCR
            full_text = pytesseract.image_to_string(tz_img, config='--psm 6').upper()

            # Debug: log what OCR saw (visible in Render logs)
            print("DEBUG: OCR extracted text:")
            print(full_text[:500])  # first 500 chars

            # Extract zones and countdown using regex
            current_match = re.search(r'CURRENT ZONE:([^NEXT]+)', full_text, re.IGNORECASE | re.DOTALL)
            next_match = re.search(r'NEXT ZONE:(.+?)(?:$|UNTIL)', full_text, re.IGNORECASE | re.DOTALL)
            countdown_match = re.search(r'(\d+ MIN \d+ SEC UNTIL NEXT|\d+ SEC UNTIL NEXT)', full_text, re.IGNORECASE)

            if current_match:
                current = current_match.group(1).strip().replace('\n', ' ').replace('  ', ' ')
            if next_match:
                next_zone = next_match.group(1).strip().replace('\n', ' ').replace('  ', ' ')
            if countdown_match:
                countdown = countdown_match.group(1).strip()

    except Exception as e:
        print(f"Fetch/OCR error: {str(e)}")

    # Fallback countdown if OCR didn't find it
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

    # Load your background image
    bg_path = 'bg.jpg'
    if not os.path.exists(bg_path):
        return "bg.jpg missing", 500

    img = Image.open(bg_path).convert('RGBA')
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype('font.ttf', 12)
        timer_font = ImageFont.truetype('font.ttf', 13)
    except IOError:
        font = ImageFont.load_default()
        timer_font = font

    def draw_outlined_text(x, y, text, fill, font_obj):
        # Black outline
        for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
            draw.text((x + dx, y + dy), text, font=font_obj, fill="black")
        # Main text
        draw.text((x, y), text, fill=fill, font=font_obj)

    # Draw title (your old style)
    draw_outlined_text(10, 10, "TERROR ZONES", (200, 0, 0), timer_font)  # red title

    y = 45
    draw_outlined_text(10, y, "CURRENT ZONE:", (255, 255, 255), font)
    y += 22
    for part in [current[i:i+30] for i in range(0, len(current), 30)]:
        draw_outlined_text(15, y, part, (255, 255, 255), font)
        y += 18

    y += 10
    draw_outlined_text(10, y, countdown.upper(), (255, 215, 0), timer_font)
    y += 25

    draw_outlined_text(10, y, "NEXT ZONE:", (255, 255, 255), font)
    y += 22
    for part in [next_zone[i:i+30] for i in range(0, len(next_zone), 30)]:
        draw_outlined_text(15, y, part, (255, 255, 255), font)
        y += 18

    # Your watermark
    draw_outlined_text(img.width - 90, img.height - 30, "Guy_T", (180, 180, 180), font)

    # Serve the image
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return Response(buf, mimetype='image/png', headers={'Cache-Control': 'no-cache, no-store'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
