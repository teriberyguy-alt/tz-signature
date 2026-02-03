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
    overlay_lines = ["TZ data unavailable"]
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
        
        wrapped_now = textwrap.wrap(now_text, width=35)
        wrapped_next = textwrap.wrap(next_text, width=35)
        
        overlay_lines = wrapped_now + wrapped_next
        
        # Calculate MM:SS until next hour (zones change on the hour)
        now = datetime.utcnow()
        seconds_to_next_hour = (60 - now.minute) * 60 - now.second
        minutes = seconds_to_next_hour // 60
        seconds = seconds_to_next_hour % 60
        countdown_str = f"{minutes:02d}:{seconds:02d} until"
    except Exception as e:
        overlay_lines = [f"TZ fetch error: {str(e)[:60]}"]

    try:
        bg_path = os.path.join(BASE_DIR, 'bg.jpg')
        font_path = os.path.join(BASE_DIR, 'font.ttf')
        
        bg_image = Image.open(bg_path).convert('RGBA')
        draw = ImageDraw.Draw(bg_image)
        font = ImageFont.truetype(font_path, 12)
        
        x = 10
        y = 60  # Start higher to fit countdown
        line_spacing = 14
        
        for line in overlay_lines:
            draw.text((x, y), line, font=font, fill=(255, 255, 255))
            y += line_spacing
        
        # Add countdown line below the zones (or integrate if you prefer)
        if countdown_str:
            countdown_text = f"{countdown_str}"
            draw.text((x, y + 5), countdown_text, font=font, fill=(255, 215, 0))  # Gold color for emphasis
        
        img_bytes = io.BytesIO()
        bg_image.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return Response(img_bytes, mimetype='image/png')
    except Exception as e:
        return Response(f"Image error: {str(e)}".encode(), mimetype='text/plain', status=500)

if __name__ == '__main__':
    app.run()
