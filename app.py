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

cache = {'text': None, 'timestamp': 0}

@app.route('/signature.png')
def signature():
    print("DEBUG: Route hit at", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))

    current = 'PENDING'
    next_zone = 'PENDING'
    countdown = 'PENDING'

    start_time = time.time()

    try:
        if cache['text'] and (time.time() - cache['timestamp'] < 60):
            full_text = cache['text']
            print("DEBUG: Using cache")
        else:
            tz_url = "https://api.d2tz.info/public/tz_image?t=none&width=500"
            r = requests.get(tz_url, timeout=10)
            if r.status_code != 200:
                raise Exception(f"Fetch failed: {r.status_code}")

            tz_img = Image.open(BytesIO(r.content)).convert('RGB')

            # Upscale slightly for better OCR accuracy
            tz_img = tz_img.resize((tz_img.width * 2, tz_img.height * 2), Image.LANCZOS)

            # Crop to top 75% to include next zone
            width, height = tz_img.size
            tz_img = tz_img.crop((0, 0, width, int(height * 0.75)))

            # Contrast + invert
            enhancer = ImageEnhance.Contrast(tz_img)
            tz_img = enhancer.enhance(4.0)
            tz_img = ImageOps.invert(tz_img)

            # Threshold
            tz_cv = cv2.cvtColor(np.array(tz_img), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(tz_cv, cv2.COLOR_BGR2GRAY)
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

            # OCR with single column + whitelist
            config = r'--oem 3 --psm 4 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789,:; '
            full_text = pytesseract.image_to_string(thresh, config=config).upper().strip()

            # Post-process: fix common OCR errors
            full_text = full_text.replace('Ø', 'O').replace('UTER', 'OUTER').replace('PDS', ' OF DES').replace('MAUSØLEUM', 'MAUSOLEUM')
            full_text = re.sub(r'([A-Z])([A-Z]{3,})', r'\1 \2', full_text)  # Force space after single letter
            full_text = re.sub(r'([A-Z]),([A-Z])', r'\1, \2', full_text)  # Space after comma

            cache['text'] = full_text
            cache['timestamp'] = time.time()

            print("DEBUG: Fresh OCR (processed):")
            print(full_text)

        # Parse current zone
        current_match = re.search(r'CURRENT\s*ZONE[:\s]*([A-Z0-9\s,]+?)(?=NEXT\s*ZONE|$)', full_text, re.IGNORECASE | re.DOTALL | re.MULTILINE)
        if current_match:
            current = current_match.group(1).strip().replace('\n', ' ').replace('  ', ' ')

        # Parse next zone
        next_match = re.search(r'NEXT\s*ZONE[:\s]*([A-Z0-9\s,]+?)(?=\s*\d+|$)', full_text, re.IGNORECASE | re.DOTALL | re.MULTILINE)
        if next_match:
            next_zone = next_match.group(1).strip().replace('\n', ' ').replace('  ', ' ')
        else:
            # Fallback if regex misses - look for anything after "NEXT ZONE"
            next_part = re.search(r'NEXT\s*ZONE[:\s]*(.+)', full_text, re.IGNORECASE | re.DOTALL)
            if next_part:
                next_zone = next_part.group(1).strip().replace('\n', ' ').replace('  ', ' ')[:60] + '...'

        # Countdown
        countdown_match = re.search(r'(\d+\s*MIN\s*\d+\s*SEC\s*UNTIL\s*NEXT|\d+\s*SEC\s*UNTIL\s*NEXT)', full_text, re.IGNORECASE)
        if countdown_match:
            countdown = countdown_match.group(1).strip()

    except Exception as e:
        print(f"Error: {str(e)}")

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

    print(f"DEBUG: Final parsed - current: '{current}' | next: '{next_zone}' | countdown: '{countdown}'")
    print(f"DEBUG: Generation time: {time.time() - start_time:.2f} sec")

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

    # Positions - tweak y if needed
    y = 45
    draw_outlined_text(10, y, "CURRENT ZONE:", (255, 255, 255), font)
    y += 22
    for part in [current[i:i+45] for i in range(0, len(current), 45)]:
        draw_outlined_text(15, y, part.strip(), (255, 255, 255), font)
        y += 18

    y += 10
    draw_outlined_text(10, y, countdown, (255, 215, 0), timer_font)
    y += 25

    draw_outlined_text(10, y, "NEXT ZONE:", (255, 255, 255), font)
    y += 22
    for part in [next_zone[i:i+45] for i in range(0, len(next_zone), 45)]:
        draw_outlined_text(15, y, part.strip(), (255, 255, 255), font)
        y += 18

    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    print("DEBUG: Image sent")
    return Response(buf, mimetype='image/png', headers={'Cache-Control': 'no-cache, no-store'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
