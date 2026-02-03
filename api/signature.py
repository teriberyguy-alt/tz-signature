import io
import os
import requests
import textwrap
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, Response

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@app.route('/signature.png')
def generate_signature():
    now_lines = ["TZ data unavailable"]
    next_lines = []
    countdown_str = ""
    try:
        tz_url = 'https://d2runewizard.com/api/terror-zone'
        response = requests.get(tz_url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        current_zone = data.get('currentTerrorZone', {}).get('zone', 'Unknown')
        next_zone = data.get('nextTerrorZone', {}).get('zone', 'Unknown')
        
        now_text = f"Now: {current_zone}"
        next_text = f"Next: {next_zone}"
        
        now_lines = textwrap.wrap(now_text, width=35)
        next_lines = textwrap.wrap(next_text, width=35)
        
        # Countdown: seconds until next full hour (UTC)
        now_dt = datetime.utcnow()
        seconds_to_next = (60 - now_dt.minute) * 60 - now_dt.second
        if seconds_to_next < 0:  # Rare edge case
            seconds_to_next = 0
        minutes = seconds_to_next // 60
        seconds = seconds_to_next % 60
        countdown_str = f"{minutes:02d}:{seconds:02d} until"
    except Exception as e:
        now_lines = [f"TZ fetch error: {str(e)[:60]}"]

    try:
        bg_path = os.path.join(BASE_DIR, 'bg.jpg')
        font_path = os.path.join(BASE_DIR, 'font.ttf')
        
        bg_image = Image.open(bg_path).convert('RGBA')
        draw = ImageDraw.Draw(bg_image)
        font = ImageFont.truetype(font_path, 12)
        
        x = 10
        y = 60          # Starting y for "Now" (adjust if overlaps your name/logo)
        line_spacing = 14
        
        # Draw "Now" lines
        for line in now_lines:
            draw.text((x, y), line, font=font, fill=(255, 255, 255))
            y += line_spacing
        
        # Draw countdown (gold, with a bit extra space above/below)
        if countdown_str:
            y += 4  # Small gap after "Now"
            draw.text((x, y), countdown_str, font=font, fill=(255, 215, 0))
            y += line_spacing + 2  # Gap before "Next"
        
        # Draw "Next" lines
        for line in next_lines:
            draw.text((x, y), line, font=font, fill=(255, 255, 255))
            y += line_spacing
        
        img_bytes = io.BytesIO()
        bg_image.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return Response(img_bytes, mimetype='image/png')
    except Exception as e:
        return Response(f"Image error: {str(e)}".encode(), mimetype='text/plain', status=500)

if __name__ == '__main__':
    app.run()
