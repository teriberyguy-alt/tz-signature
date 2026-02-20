import io
import os
import requests
import textwrap
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, Response
from bs4 import BeautifulSoup
import re

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@app.route('/signature.png')
def generate_signature():
    now_lines = ["TZ data unavailable"]
    next_lines = []
    countdown_str = ""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
    }

    try:
        tz_url = 'https://d2emu.com/tz'

        for attempt in range(3):
            try:
                response = requests.get(tz_url, headers=headers, timeout=15)
                print(f"Attempt {attempt+1} - Status: {response.status_code}")
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')

                current_zone = 'REPORT PENDING'
                next_zone = 'PENDING'

                # Method 1: Table parse - look for |  | zone rows
                lines = response.text.splitlines()
                zone_candidates = []
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith('|') and '|' in stripped[1:]:
                        parts = [p.strip().upper() for p in stripped.split('|') if p.strip()]
                        if len(parts) >= 2 and '---' not in ' '.join(parts):
                            zone_text = parts[-1]  # last part is usually zone
                            if 'IMMUN' in zone_text or 'MONSTERS' in zone_text or 'COLD' in zone_text or 'FIRE' in zone_text or 'LIGHTNING' in zone_text or 'POISON' in zone_text or 'MAGIC' in zone_text:
                                continue
                            if len(zone_text) > 5 and zone_text != '---':
                                zone_candidates.append(zone_text)

                print(f"Table candidates: {zone_candidates}")

                if zone_candidates:
                    current_zone = zone_candidates[0]
                    if len(zone_candidates) > 1:
                        next_zone = ' '.join(zone_candidates[1:])

                # Method 2: Regex fallback on full text
                full_text = soup.get_text(separator=' ', strip=True)
                current_match = re.search(r'Current\s*Terror\s*Zone:\s*([^\n.]+)', full_text, re.IGNORECASE)
                if current_match:
                    current_zone = current_match.group(1).strip().upper()
                    print(f"Regex current: {current_zone}")

                next_match = re.search(r'Next\s*Terror\s*Zone:\s*([^\n.]+)', full_text, re.IGNORECASE)
                if next_match:
                    next_zone = next_match.group(1).strip().upper()
                    print(f"Regex next: {next_zone}")

                # Clean any immunities junk
                if 'IMMUN' in current_zone:
                    current_zone = current_zone.split('IMMUN')[0].strip().upper()
                if 'IMMUN' in next_zone:
                    next_zone = next_zone.split('IMMUN')[0].strip().upper()

                now_text = f"Now: {current_zone}"
                next_text = f"Next: {next_zone}"

                now_lines = textwrap.wrap(now_text, width=35)
                next_lines = textwrap.wrap(next_text, width=35)

                # 30-minute cycle countdown
                now_dt = datetime.utcnow()
                minutes_to_next = 30 - (now_dt.minute % 30)
                seconds_to_next = minutes_to_next * 60 - now_dt.second
                if seconds_to_next < 0:
                    seconds_to_next = 0
                minutes = seconds_to_next // 60
                seconds = seconds_to_next % 60

                if minutes == 0:
                    countdown_str = f"{seconds} seconds until"
                else:
                    countdown_str = f"{minutes} min, {seconds:02d} sec until"

                break
            except Exception as e:
                print(f"Attempt {attempt+1} failed: {str(e)}")
                if attempt == 2:
                    now_lines = [f"Fetch err: {str(e)[:30]}"]
                    break
                time.sleep(2)
    except Exception as e:
        print(f"Overall fetch error: {str(e)}")
        now_lines = ["TZ Fetch Slow"]
        next_lines = ["Refresh in a few sec"]

    try:
        bg_path = os.path.join(BASE_DIR, 'bg.jpg')
        font_path = os.path.join(BASE_DIR, 'font.ttf')

        bg_image = Image.open(bg_path).convert('RGBA')
        draw = ImageDraw.Draw(bg_image)
        font = ImageFont.truetype(font_path, 12)
        timer_font = ImageFont.truetype(font_path, 13)

        x = 10
        y = 55
        line_spacing = 15

        def draw_with_shadow(text, px, py, fnt, color):
            draw.text((px+1, py+1), text, font=fnt, fill=(0, 0, 0))
            draw.text((px, py), text, font=fnt, fill=color)

        for line in now_lines:
            draw_with_shadow(line, x, y, font, (255, 255, 255))
            y += line_spacing

        if countdown_str:
            y += 6
            draw_with_shadow(countdown_str, x + 5, y, timer_font, (255, 215, 0))
            y += line_spacing + 4

        for line in next_lines:
            draw_with_shadow(line, x, y, font, (255, 255, 255))
            y += line_spacing

        img_bytes = io.BytesIO()
        bg_image.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        return Response(img_bytes, mimetype='image/png')
    except Exception as e:
        print(f"Image generation error: {str(e)}")
        return Response(f"Image error: {str(e)}".encode(), mimetype='text/plain', status=500)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
