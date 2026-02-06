import io
import os
import requests
import textwrap
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, Response

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@app.route('/signature.png')
def generate_signature():
    now_lines = ["REPORT PENDING"]
    next_lines = ["NEXT UNKNOWN"]
    countdown_str = "?"

    # Headers to avoid 403 from d2runewizard
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://d2runewizard.com/terror-zone-tracker',
        'Origin': 'https://d2runewizard.com'
    }

    try:
        # Add timestamp to bust cache and get fresh data
        tz_url = f'https://d2runewizard.com/api/v1/terror-zone?t={int(time.time())}'

        for attempt in range(2):
            try:
                response = requests.get(tz_url, headers=headers, timeout=12)
                response.raise_for_status()
                data = response.json()

                # Current structure (as of late 2025 / 2026)
                current_zone = data.get('currentTerrorZone', {}).get('zone', 'Unknown')
                next_zone = data.get('nextTerrorZone', {}).get('zone', 'Unknown')

                if current_zone.lower() == 'unknown' or not current_zone:
                    current_zone = 'REPORT PENDING'

                if next_zone.lower() == 'unknown' or not next_zone:
                    next_zone = 'PENDING'

                now_text = f"Now: {current_zone.upper()}"
                next_text = f"Next: {next_zone.upper()}"

                now_lines = textwrap.wrap(now_text, width=32)
                next_lines = textwrap.wrap(next_text, width=32)

                # Accurate countdown to next hour
                now_dt = datetime.utcnow()
                seconds_to_next = (60 - now_dt.minute) * 60 - now_dt.second
                if seconds_to_next < 0:
                    seconds_to_next = 0
                minutes = seconds_to_next // 60
                seconds = seconds_to_next % 60

                if minutes == 0 and seconds < 60:
                    countdown_str = f"{seconds}s until change"
                elif minutes == 1:
                    countdown_str = f"1 min {seconds:02d}s until"
                else:
                    countdown_str = f"{minutes} min until"

                break

            except requests.exceptions.RequestException as e:
                if attempt == 1:
                    raise
                time.sleep(1.5)

    except Exception as e:
        now_lines = ["TZ FETCH FAILED"]
        next_lines = ["Try again soon"]
        countdown_str = "?"

    try:
        bg_path = os.path.join(BASE_DIR, 'bg.jpg')
        font_path = os.path.join(BASE_DIR, 'font.ttf')

        bg_image = Image.open(bg_path).convert('RGBA')
        draw = ImageDraw.Draw(bg_image)

        # Use your font or fallback
        try:
            title_font = ImageFont.truetype(font_path, 16)
            main_font = ImageFont.truetype(font_path, 12)
            timer_font = ImageFont.truetype(font_path, 13)
        except:
            title_font = ImageFont.load_default()
            main_font = ImageFont.load_default()
            timer_font = ImageFont.load_default()

        # Shadow helper
        def draw_with_shadow(text, x, y, font, color):
            draw.text((x+1, y+1), text, font=font, fill=(0, 0, 0))  # shadow
            draw.text((x, y), text, font=font, fill=color)

        # Title
        draw_with_shadow("TERROR ZONE", 70, 8, title_font, (200, 40, 0))

        # Timer (top right)
        draw_with_shadow(countdown_str, 185, 12, timer_font, (255, 215, 0))

        y = 45  # Starting Y for content
        line_spacing = 16

        # Now lines
        draw_with_shadow("NOW:", 15, y, main_font, (200, 40, 0))
        y += 14
        for line in now_lines:
            draw_with_shadow(line, 15, y, main_font, (255, 255, 255))
            y += line_spacing

        y += 8  # gap

        # Next lines
        draw_with_shadow("NEXT:", 15, y, main_font, (200, 40, 0))
        y += 14
        for line in next_lines:
            draw_with_shadow(line, 15, y, main_font, (220, 220, 150))
            y += line_spacing

        img_bytes = io.BytesIO()
        bg_image.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        return Response(img_bytes, mimetype='image/png')

    except Exception as e:
        return Response(f"Image generation error: {str(e)}".encode(), mimetype='text/plain', status=500)

if __name__ == '__main__':
    app.run()
