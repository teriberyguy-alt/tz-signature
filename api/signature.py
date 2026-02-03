import io
import os
import requests
import json
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, Response

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@app.route('/signature.png')
def generate_signature():
    overlay_text = "TZ data unavailable"
    try:
        tz_url = 'https://d2runewizard.com/api/terror-zone'
        response = requests.get(tz_url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        current = data.get('currentTerrorZone', {})
        next_tz = data.get('nextTerrorZone', {})
        
        current_zone = current.get('zone', 'Unknown')
        current_act = current.get('act', '')
        next_zone = next_tz.get('zone', 'Unknown')
        next_act = next_tz.get('act', '')
        
        current_str = f"{current_zone}, {current_act}" if current_act else current_zone
        next_str = f"{next_zone}, {next_act}" if next_act else next_zone
        
        overlay_text = f"Current: {current_str}\nNext: {next_str}"
    except requests.exceptions.RequestException as e:
        overlay_text = f"TZ fetch error: {str(e)[:50]}"
    except json.JSONDecodeError:
        overlay_text = "Invalid TZ data format"
    except Exception as e:
        overlay_text = f"Error: {str(e)[:50]}"

    try:
        bg_path = os.path.join(BASE_DIR, 'bg.jpg')
        font_path = os.path.join(BASE_DIR, 'font.ttf')
        
        bg_image = Image.open(bg_path)
        draw = ImageDraw.Draw(bg_image)
        font = ImageFont.truetype(font_path, 14)  # Adjust size as needed
        
        draw.multiline_text((10, 90), overlay_text, font=font, fill=(255, 255, 255))  # White text; adjust pos/size/color
        
        img_bytes = io.BytesIO()
        bg_image.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return Response(img_bytes, mimetype='image/png')
    except Exception as e:
        return Response(f"Image gen error: {str(e)}".encode(), mimetype='text/plain', status=500)

if __name__ == '__main__':
    app.run()
