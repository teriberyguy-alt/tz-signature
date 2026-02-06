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
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://d2runewizard.com/terror-zone-tracker',
        'Origin': 'https://d2runewizard.com'
    }

    url = f'https://d2runewizard.com/api/v1/terror-zone?t={int(time.time())}'

    for attempt in range(2):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            zone = data.get('currentTerrorZone', {}).get('zone', 'Unknown')
            if zone.lower() == 'unknown' or not zone.strip():
                zone = 'PENDING'
            return zone.upper()
        except requests.exceptions.RequestException:
            if attempt == 1:
                return 'PENDING'
            time.sleep(1.5)
    return 'PENDING'

@app.route('/avatar.gif')
def avatar():
    zone = get_current_zone()

    font_path = os.path.join(BASE_DIR, 'font.ttf')
    try:
        font = ImageFont.truetype(font_path, 9)
    except:
        font = ImageFont.load_default()

    frames = []
    bg_colors = [(0, 0, 0), (12, 0, 0), (24, 0, 0), (12, 0, 0)]  # subtle pulse

    zone_short = zone[:11] + '..' if len(zone) > 11 else zone

    for i in range(3):
        img = Image.new('RGB', (64, 64), bg_colors[i])
        draw = ImageDraw.Draw(img)

        draw.rectangle((0, 0, 63, 63), outline=(200, 40, 0), width=1)

        if i == 0:
            draw.text((4, 6), "TZ:", fill=(255, 165, 0), font=font)
            draw.text((4, 22), zone_short, fill=(255, 255, 255), font=font)
        elif i == 1:
            mins = 60 - datetime.now().minute
            draw.text((4, 6), f"{mins}M", fill=(255, 215, 0), font=font)
            draw.text((4, 22), "LEFT", fill=(220, 220, 150), font=font)
        else:
            draw.text((4, 18), "LIVE", fill=(200, 40, 0), font=font)

        # Flame effect dots
        draw.point([(8 + i*3, 50), (12 + i*2, 52), (16 + i*3, 51)], fill=(255, 100, 0))

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
    res.headers["Pragma"] = "no-cache"
    res.headers["Expires"] = "0"
    return res

if __name__ == '__main__':
    app.run()
