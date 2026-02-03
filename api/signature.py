import io
import os
import requests
import textwrap
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, Response

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@app.route('/signature.png')
def generate_signature():
    overlay_lines = ["TZ data unavailable"]
    try:
        tz_url = 'https://d2runewizard.com/api/terror-zone'
        response = requests.get(tz_url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        current_zone = data.get('currentTerrorZone', {}).get('zone', 'Unknown')
        current_act = data.get('currentTerrorZone', {}).get('act', '')
        next_zone = data.get('nextTerrorZone', {}).get('zone', 'Unknown')
        next_act = data.get('nextTerrorZone', {}).get('act', '')
        
        # Format with act if present
        now_text = f"Now: {current_zone}"
        if current_act:
            now_text += f" ({current_act})"
        
        next_text = f"Next: {next_zone}"
        if next_act:
            next_text += f" ({next_act})"
        
        # Wrap long lines (adjust width=30 if text still overflows; smaller = more lines)
        wrapped_now = textwrap.wrap(now_text, width=35)
        wrapped_next = textwrap.wrap(next_text, width=35)
        
        overlay_lines = wrapped_now + wrapped_next
    except Exception as e:
        overlay_lines = [f"TZ fetch error: {str(e)[:60]}"]

    try:
        bg_path = os.path.join(BASE_DIR, 'bg.jpg')
        font_path = os.path.join(BASE_DIR, 'font.ttf')
        
        bg_image = Image.open(bg_path).convert('RGBA')  # Ensure alpha for better blending if needed
        draw = ImageDraw.Draw(bg_image)
        font = ImageFont.truetype(font_path, 12)  # Try 11 or 13 if too big/small
        
        # Starting position: left margin 10px, top ~70-90px to leave room for your name/logo
        x = 10
        y = 70
        line_spacing = 14  # Adjust (font size + 2-4) for gap between lines
        
        for line in overlay_lines:
            draw.text((x, y), line, font=font, fill=(255, 255, 255))  # White; try (220,220,255) for softer
            y += line_spacing
        
        # Save to bytes
        img_bytes = io.BytesIO()
        bg_image.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return Response(img_bytes, mimetype='image/png')
    except Exception as e:
        return Response(f"Image error: {str(e)}".encode(), mimetype='text/plain', status=500)

if __name__ == '__main__':
    app.run()
