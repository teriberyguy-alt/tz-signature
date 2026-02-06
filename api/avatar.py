import io
import os
import requests
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, Response

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_current_zone():
    zone = 'PENDING'
    try:
        tz_url = 'https://d2runewizard.com/api/terror-zone'  # your original URL
        
        for attempt in range(2):
            try:
                response = requests.get(tz_url, timeout=15)
                response.raise_for_status()
                data = response.json()
               
                current_zone = data.get('currentTerrorZone', {}).get('zone', 'Unknown')
                if current_zone != 'Unknown':
                    zone = current_zone.upper()
                break
            except requests.exceptions.RequestException:
                if attempt == 1:
                    zone = 'FETCH FAILED'
                time.sleep(1)
    except Exception:
        zone = 'FETCH ERROR'
    
    return zone

@app.route('/avatar.gif')
def avatar():
    zone = get_current_zone()

    font_path = os.path.join(BASE_DIR, 'font.ttf')
    try:
        font = ImageFont.truetype(font_path, 9)
    except:
        font = ImageFont.load_default()

    frames = []
    bg_colors = [(0, 0, 0), (10, 0, 0), (20, 0, 0)]

    zone_short = zone[:10] + '..' if len(zone) > 10 else zone

    for i in range(3):
        img = Image.new('RGB', (64, 64), bg_colors[i])
        draw = ImageDraw.Draw(img)

        draw.rectangle((0, 0, 63, 63), outline=(200, 40, 0), width=1)

        if i == 0:
            draw.text((4, 8), "TZ:", fill=(255, 165, 0), font=font)
            draw.text((4, 22), zone_short, fill=(255, 255, 255), font=font)
        elif i == 1:
            mins = 60 - datetime.now().minute
            draw.text((4, 8), f"{mins}M", fill=(255, 215, 0), font=font)
            draw.text((4, 22), "NEXT", fill=(220, 220, 150), font=font)
        else:
            draw.text((4, 18), zone[:8], fill=(200, 40, 0), font=font)

        frames.append(img)

    buf = io.BytesIO()
    frames[0].save(
        buf,
        format='GIF',
        save_all=True,
        append_images=frames[1:],
        duration=700,
        loop=0,
        optimize=True
    )
    buf.seek(0)

    res = Response(buf, mimetype='image/gif')
    res.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return res

if __name__ == '__main__':
    app.run()
