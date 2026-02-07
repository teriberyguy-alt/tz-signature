import io
import os
import requests
import textwrap
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, Response
from bs4 import BeautifulSoup

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@app.route('/signature.png')
def generate_signature():
    now_lines = ["TZ data unavailable"]
    next_lines = []
    countdown_str = ""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
        }
        tz_url = 'https://d2emu.com/tz'

        for attempt in range(2):
            try:
                response = requests.get(tz_url, headers=headers, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')

                current_zone = 'REPORT PENDING'
                next_zone = 'PENDING'

                # 1. Strict table parse - only |  | lines, skip immunities
                lines = response.text.splitlines()
                zone_candidates = []
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith('|  |') and '---' not in stripped and 'immunities' not in stripped.lower():
                        parts = stripped.split('|')
                        if len(parts) >= 3:
                            zone_text = parts[2].strip().upper()
                            if zone_text and zone_text != '---' and len(zone_text) > 3:
                                zone_candidates.append(zone_text)

                if zone_candidates:
                    current_zone = zone_candidates[0]
                    if len(zone_candidates) > 1:
                        next_zone = ' '.join(zone_candidates[1:])

                # 2. Text fallback if no table zones
                full_text = soup.get_text(separator=' ', strip=True).upper()
                if current_zone == 'REPORT PENDING' and "CURRENT TERROR ZONE:" in full_text:
                    start = full_text.find("CURRENT TERROR ZONE:")
                    snippet = full_text[start + len("CURRENT TERROR ZONE:"): start + 150]
                    current_zone = snippet.split("NEXT")[0].strip().upper()

                if next_zone == 'PENDING' and "NEXT TERROR ZONE:" in full_text:
                    start = full_text.find("NEXT TERROR ZONE:")
                    snippet = full_text[start + len("NEXT TERROR ZONE:"): start + 150]
                    next_zone = snippet.strip().upper()

                now_text = f"Now: {current_zone}"
                next_text = f"Next: {next_zone}"

                now_lines = textwrap.wrap(now_text, width=35)
                next_lines = textwrap.wrap(next_text, width=35)

                now_dt = datetime.utcnow()
                seconds_to_next = (60 - now_dt.minute) * 60 - now_dt.second
                if seconds_to_next < 0:
                    seconds_to_next = 0
                minutes = seconds_to_next // 60
                seconds = seconds_to_next % 60

                if minutes == 0:
                    countdown_str = f"{seconds} seconds until"
                else:
                    countdown_str = f"{minutes} min, {seconds:02d} sec until"

                break
            except requests.exceptions.RequestException:
                if attempt == 1:
                    raise
                time.sleep(1)
    except Exception:
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
        return Response(f"Image error: {str(e)}".encode(), mimetype='text/plain', status=500)

if __name__ == '__main__':
    app.run()
