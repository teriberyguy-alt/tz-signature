import io
import os
import requests
import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageOps
from flask import Flask, Response

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Small icon URLs (public, tiny ~16-24px PNGs; adjust if needed)
ICONS = {
    'fire': 'https://static.wikia.nocookie.net/diablo/images/7/7a/Fire_small.png/revision/latest?cb=20110414000000',  # Example; find better if broken
    'cold': 'https://static.wikia.nocookie.net/diablo/images/1/1e/Cold_small.png/revision/latest?cb=20110414000000',
    'lightning': 'https://static.wikia.nocookie.net/diablo/images/3/3d/Lightning_small.png/revision/latest?cb=20110414000000',
    'poison': 'https://static.wikia.nocookie.net/diablo/images/5/5e/Poison_small.png/revision/latest?cb=20110414000000',
    # Add more if you find good URLs (e.g., from maxroll.gg or d2planner)
}

@app.route('/signature.png')
def generate_signature():
    overlay_lines = ["TZ data unavailable"]
    try:
        tz_url = 'https://d2runewizard.com/api/terror-zone'
        response = requests.get(tz_url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        current_zone = data.get('currentTerrorZone', {}).get('zone', 'Unknown')
        next_zone = data.get('nextTerrorZone', {}).get('zone', 'Unknown')
        
        # Clean names, no act
        now_text = f"Now: {current_zone}"
        next_text = f"Next: {next_zone}"
        
        wrapped_now = textwrap.wrap(now_text, width=35)
        wrapped_next = textwrap.wrap(next_text, width=35)
        
        overlay_lines = wrapped_now + wrapped_next
    except Exception as e:
        overlay_lines = [f"TZ fetch error: {str(e)[:60]}"]

    try:
        bg_path = os.path.join(BASE_DIR, 'bg.jpg')
        font_path = os.path.join(BASE_DIR, 'font.ttf')
        
        bg_image = Image.open(bg_path).convert('RGBA')
        draw = ImageDraw.Draw(bg_image, 'RGBA')
        font = ImageFont.truetype(font_path, 12)
        
        # Text positioning
        x = 10
        y = 70
        line_spacing = 14
        
        for line in overlay_lines:
            draw.text((x, y), line, font=font, fill=(255, 255, 255))
            y += line_spacing
        
        # Optional: Small immunity icons row at bottom (e.g., y near 120-130 to fit 140 height)
        icon_y = 110  # Adjust up/down
        icon_size = (20, 20)  # Tiny
        icon_x_start = 10
        icon_spacing = 25
        
        # For now, show all 4 as example/reminder (customize later)
        for i, (elem, url) in enumerate(ICONS.items()):
            try:
                icon_response = requests.get(url, timeout=5)
                icon_img = Image.open(io.BytesIO(icon_response.content)).convert('RGBA')
                icon_img = icon_img.resize(icon_size, Image.LANCZOS)
                
                # Paste with alpha
                bg_image.paste(icon_img, (icon_x_start + i * icon_spacing, icon_y), icon_img)
            except:
                pass  # Skip if icon fails to load
        
        # Save
        img_bytes = io.BytesIO()
        bg_image.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return Response(img_bytes, mimetype='image/png')
    except Exception as e:
        return Response(f"Image error: {str(e)}".encode(), mimetype='text/plain', status=500)

if __name__ == '__main__':
    app.run()
