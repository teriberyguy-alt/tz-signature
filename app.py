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
import time

app = Flask(__name__)

# Simple in-memory cache (last OCR result + timestamp)
cache = {'text': None, 'timestamp': 0}

@app.route('/signature.png')
def signature():
    print("DEBUG: Signature route hit at", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))

    current = 'PENDING'
    next_zone = 'PENDING'
    countdown = 'PENDING'

    start_time = time.time()

    try:
        # Check cache first (refresh every 60 seconds)
        if cache['text'] and (time.time() - cache['timestamp'] < 60):
            full_text = cache['text']
            print("DEBUG: Using cached OCR text")
        else:
            tz_url = "https://api.d2tz.info/public/tz_image?t=none&width=400"  # Smaller = faster OCR
            r = requests.get(tz_url, timeout=10)
            if r.status_code != 200:
                print(f"DEBUG: d2tz fetch failed - status {r.status_code}")
                raise Exception("Fetch failed")

            tz_img = Image.open(BytesIO(r.content)).convert('RGB')

            # Crop tighter (top 45%)
            width, height = tz_img.size
            tz_img = tz_img.crop((0, 0, width, int(height * 0.45)))

            # Fast contrast + invert
            enhancer = ImageEnhance.Contrast(tz_img)
            tz_img = enhancer.enhance(3.5)
            tz_img = ImageOps.invert(tz_img)

            # Quick threshold
            tz_cv = cv2.cvtColor(np.array(tz_img), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(tz_cv, cv2.COLOR_BGR2GRAY)
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

            # OCR - single good config to save time
            config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789,:; '
            full_text = pytesseract.image_to_string(thresh, config=config).upper().strip()

            # Cache it
            cache['text'] = full_text
            cache['timestamp'] = time.time()

            print("DEBUG: Fresh OCR performed - full text:")
            print(full_text)

        # Parse
        current_match = re.search(r'CURRENT\s*ZONE[:\s]*([A-Z0-9\s,]+?)(?=NEXT\s*ZONE|$)', full_text, re.IGNORECASE | re.DOTALL)
        next_match = re.search(r'NEXT\s*ZONE[:\s]*([A-Z0-9\s,]+?)(?=\s*\d+|$)', full_text, re.IGNORECASE | re.DOTALL)
        countdown_match = re.search(r'(\d+\s*MIN\s*\d+\s*SEC\s*UNTIL\s*NEXT|\d+\s*SEC\s*UNTIL\s*NEXT)', full_text, re.IGNORECASE)

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
        countdown = f"{secs_to_next // 60} MIN {secs_to_next % 60:02d} SEC UNTIL NEXT"
        if secs_to_next < 60:
            countdown = f"{secs_to_next} SEC UNTIL NEXT"

    print(f"DEBUG: Parsed - current: {current} | next: {next_zone} | countdown: {countdown}")
    print(f"DEBUG: Generation time: {time.time() - start_time:.2f} seconds")

    # Load bg.jpg
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

    # Adjusted y-start and wider wrap (40 chars/line) to prevent cutoff
    y = 45  # Change this if text is too high/low on your bg
    draw_outlined_text(10, y, "CURRENT ZONE:", (255, 255, 255), font)
    y += 22
    for part in [current[i:i+40] for i in range(0, len(current), 40)]:  # wider lines
        draw_outlined_text(15, y, part, (255, 255, 255), font)
        y += 18

    y += 10
    draw_outlined_text(10, y, countdown, (255, 215, 0), timer_font)
    y += 25

    draw_outlined_text(10, y, "NEXT ZONE:", (255, 255, 255), font)
    y += 22
    for part in [next_zone[i:i+40] for i in range(0, len(next_zone), 40)]:
        draw_outlined_text(15, y, part, (255, 255, 255), font)
        y += 18

    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    print("DEBUG: Image generated and ready to send")
    return Response(buf, mimetype='image/png', headers={'Cache-Control': 'no-cache, no-store'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
