from flask import Flask, Response
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import requests
from io import BytesIO
from datetime import datetime, timezone
import os
import pytesseract
import re
import cv2
import numpy as np

app = Flask(__name__)

@app.route('/signature.png')
def signature():
    current = 'PENDING'
    next_zone = 'PENDING'
    countdown = 'PENDING'

    try:
        # Fetch d2tz image (larger for better OCR)
        tz_url = "https://api.d2tz.info/public/tz_image?t=none&width=600"
        r = requests.get(tz_url, timeout=15)
        if r.status_code != 200:
            print(f"DEBUG: d2tz fetch failed, status {r.status_code}")
        else:
            tz_img_bytes = r.content

            # Open and pre-process
            tz_img = Image.open(BytesIO(tz_img_bytes)).convert('RGB')

            # Crop to text area (top ~70% of image)
            width, height = tz_img.size
            tz_img = tz_img.crop((0, 0, width, int(height * 0.7)))

            # Enhance contrast
            enhancer = ImageEnhance.Contrast(tz_img)
            tz_img = enhancer.enhance(2.0)

            # Convert to OpenCV format for further processing
            tz_cv = cv2.cvtColor(np.array(tz_img), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(tz_cv, cv2.COLOR_BGR2GRAY)
            # Threshold to make text pop
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # OCR on processed image
            custom_config = r'--oem 3 --psm 6'  # Assume single uniform block of text
            full_text = pytesseract.image_to_string(thresh, config=custom_config).upper()

            print("DEBUG: OCR full text:")
            print(full_text[:1000])  # Log first chunk

            # Extract
            current_match = re.search(r'CURRENT ZONE:\s*([^N]+?)(?=NEXT ZONE|$)', full_text, re.IGNORECASE | re.DOTALL)
            next_match = re.search(r'NEXT ZONE:\s*(.+?)(?=\s*\d+ MIN|\s*\d+ SEC|$)', full_text, re.IGNORECASE | re.DOTALL)
            countdown_match = re.search(r'(\d+ MIN \d+ SEC UNTIL NEXT|\d+ SEC UNTIL NEXT)', full_text, re.IGNORECASE)

            if current_match:
                current = current_match.group(1).strip().replace('\n', ' ').replace('  ', ' ')
            if next_match:
                next_zone = next_match.group(1).strip().replace('\n', ' ').replace('  ', ' ')
            if countdown_match:
                countdown = countdown_match.group(1).strip()

    except Exception as e:
        print(f"Fetch/OCR error: {str(e)}")

    # Fallback countdown
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

    # Load your bg.jpg (title and Guy_T are baked in)
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

    y = 45  # Adjust starting y to fit your bg (move down if title is high)
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

    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return Response(buf, mimetype='image/png', headers={'Cache-Control': 'no-cache, no-store'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
