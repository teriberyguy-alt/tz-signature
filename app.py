from flask import Flask, Response
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps
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
        # Fetch d2tz image at good size
        tz_url = "https://api.d2tz.info/public/tz_image?t=none&width=600"
        r = requests.get(tz_url, timeout=15)
        if r.status_code != 200:
            print(f"DEBUG: d2tz fetch failed - status {r.status_code}")
        else:
            tz_img_bytes = r.content

            # Open image
            tz_img = Image.open(BytesIO(tz_img_bytes)).convert('RGB')

            # Crop to top 50-60% (zones are usually near the top)
            width, height = tz_img.size
            tz_img = tz_img.crop((0, 0, width, int(height * 0.55)))

            # Enhance contrast heavily
            enhancer = ImageEnhance.Contrast(tz_img)
            tz_img = enhancer.enhance(4.0)  # very strong

            # Invert colors (white text on black becomes black text on white → often better for Tesseract)
            tz_img = ImageOps.invert(tz_img)

            # Convert to OpenCV for advanced thresholding
            tz_cv = cv2.cvtColor(np.array(tz_img), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(tz_cv, cv2.COLOR_BGR2GRAY)

            # Adaptive threshold + Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

            # Multiple OCR attempts with different configs
            configs = [
                r'--oem 3 --psm 6',                       # Assume single uniform block
                r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789,:; ',  # Treat as single line
                r'--oem 1 --psm 6',                       # Legacy engine fallback
            ]

            full_text = ''
            for config in configs:
                text = pytesseract.image_to_string(thresh, config=config).upper().strip()
                if len(text) > 30:  # reasonable minimum length
                    full_text = text
                    print(f"DEBUG: OCR success with config: {config}")
                    break

            # Log what we got
            print("DEBUG: OCR extracted full text:")
            print(full_text)

            # Try to parse zones
            current_match = re.search(r'CURRENT\s*ZONE:[\s:]*([A-Z0-9\s,]+?)(?=NEXT\s*ZONE|$)', full_text, re.IGNORECASE | re.DOTALL | re.MULTILINE)
            next_match = re.search(r'NEXT\s*ZONE:[\s:]*([A-Z0-9\s,]+?)(?=\s*\d+|$)', full_text, re.IGNORECASE | re.DOTALL | re.MULTILINE)
            countdown_match = re.search(r'(\d+\s*MIN\s*\d+\s*SEC\s*UNTIL\s*NEXT|\d+\s*SEC\s*UNTIL\s*NEXT)', full_text, re.IGNORECASE)

            if current_match:
                current = current_match.group(1).strip().replace('\n', ' ').replace('  ', ' ')
            if next_match:
                next_zone = next_match.group(1).strip().replace('\n', ' ').replace('  ', ' ')
            if countdown_match:
                countdown = countdown_match.group(1).strip()

    except Exception as e:
        print(f"Fetch/OCR error: {str(e)}")

    # Fallback countdown if OCR failed to find timer
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

    # Load background (title and Guy_T are in bg.jpg)
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

    # Adjust y-start if text overlaps your background title
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

    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return Response(buf, mimetype='image/png', headers={'Cache-Control': 'no-cache, no-store'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
