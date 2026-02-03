import io
import os
import requests
import textwrap
import time  # Added for retry delay
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
        
        # Retry logic: try twice if first fails
        for attempt in range(2):
            try:
                response = requests.get(tz_url, timeout=15)  # Increased timeout
                response.raise_for_status()
                data = response.json()
                
                current_zone = data.get('currentTerrorZone', {}).get('zone', 'Unknown')
                next_zone = data.get('nextTerrorZone', {}).get('zone', 'Unknown')
                
                now_text = f"Now: {current_zone}"
                next_text = f"Next: {next_zone}"
                
                now_lines = textwrap.wrap(now_text, width=35)
                next_lines = textwrap.wrap(next_text, width=35)
                
                # Countdown calculation (UTC, on the hour flip)
                now_dt = datetime.utcnow()
                seconds_to_next = (60 - now_dt.minute) * 60 - now_dt.second
                if seconds_to_next < 0:
                    seconds_to_next = 0
                minutes = seconds_to_next // 60
                seconds = seconds_to_next % 60
                countdown_str = f"{minutes} min, {seconds:02d} sec until"
                
                break  # Success, no need for retry
            except requests.exceptions.RequestException:
                if attempt == 1:
                    raise  # Both attempts failed
                time.sleep(1)  # Wait 1s before retry
    except Exception:
        # Clean fallback message instead of raw error
        now_lines = ["TZ Fetch Slow"]
        next_lines = ["Refresh in a few sec"]

    try:
        bg_path = os.path.join(BASE_DIR, 'bg.jpg')
        font_path = os.path.join(BASE_DIR, 'font.ttf')
        
        bg_image = Image.open(bg_path).convert('RGBA')
        draw = ImageDraw.Draw(bg_image)
        font = ImageFont.truetype(font_path, 12)
        timer_font = ImageFont.truetype(font_path, 13)  # Slightly larger for emphasis
        
        x = 10
        y = 55          # Start a bit higher to give more room
        line_spacing = 15  # Increased for breathing room
        
        # Draw "Now" lines
        for line in now_lines:
            draw.text((x, y), line, font=font, fill=(255, 255, 255))
            y += line_spacing
        
        # Draw countdown (gold, extra spacing)
        if countdown_str:
            y += 6   # Gap after "Now"
            draw.text((x + 5, y), countdown_str, font=timer_font, fill=(255, 215, 0))  # Slight indent
            y += line_spacing + 4  # Bigger gap before "Next"
        
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
