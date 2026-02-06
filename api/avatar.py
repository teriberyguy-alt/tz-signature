import io
import os
import requests
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, Response

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_terror_zones():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://d2runewizard.com/terror-zone-tracker',
        'Origin': 'https://d2runewizard.com'
    }

    tz_url = f'https://d2runewizard.com/api/v1/terror-zone?t={int(time.time())}'

    try:
        response = requests.get(tz_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        current_zone = data.get('currentTerrorZone', {}).get('zone', 'Unknown')
        next_zone = data.get('nextTerrorZone', {}).get('zone', 'Unknown')

        if current_zone.lower() == 'unknown' or not current_zone.strip():
            current_zone = 'PENDING'
        if next_zone.lower() == 'unknown' or not next_zone.strip():
            next_zone = 'PENDING'

        return current_zone.upper(), next_zone.upper()

    except Exception:
        return 'PENDING', 'PENDING'

@app.route('/avatar.gif')
def avatar_gif():
    current_zone, next_zone = get_terror_zones()

    # Tiny font for 64x64
    font_path = os.path.join(BASE_DIR, 'font.ttf')
    try:
        font = ImageFont.truetype(font_path, 8)
    except:
        font = ImageFont.load_default()

    frames = []
    bg_colors = [(0, 0, 0), (10, 0, 0), (20, 0, 0), (10, 0, 0)]  # subtle pulse

    curr_short = current_zone[:10] + '..' if len(current_zone) > 10 else current_zone
    next_short = next_zone[:10] + '..' if len(next_zone) > 10 else next_zone

    for i in range(4):
        img = Image.new('RGB', (64, 64), color=bg_colors[i % len(bg_colors)])
        draw = ImageDraw.Draw(img)

        # Thin border
        draw.rectangle((0, 0, 63, 63), outline=(200, 40, 0), width=1)

        if i % 2 == 0:
            # Frame: Current TZ
            draw.text((4, 6), "TZ:", fill=(255, 165, 0), font=font)
            draw.text((4, 20), curr_short, fill=(255, 255, 255), font=font)
        else:
            # Frame: Timer + next hint
            minutes_left = 60 - datetime.now().minute
            timer_text = f"{minutes_left}M"
            draw.text((4, 6), timer_text, fill=(200, 40, 0), font=font)
            draw.text((4, 20), "Next:" + next_short, fill=(220, 220, 150), font=font)

        # Simple flame dots for effect
        draw.point([(10 + i*3, 50), (14 + i*2, 52), (18 + i*3, 51)], fill=(255, 100, 0))

        frames.append(img)

    img_io = io.BytesIO()
    frames[0].save(
        img_io,
        format='GIF',
        save_all=True,
        append_images=frames[1:],
        duration=600,  # 0.6 seconds per frame
        loop=0,        # infinite loop
        optimize=True  # smaller file
    )
    img_io.seek(0)

    res = Response(img_io, mimetype='image/gif')
    res.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    res.headers["Pragma"] = "no-cache"
    res.headers["Expires"] = "0"
    return res

if __name__ == '__main__':
    app.run()
