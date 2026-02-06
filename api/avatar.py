import io
import os
import requests
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, Response

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_zone():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://d2runewizard.com/'
    }
    url = f'https://d2runewizard.com/api/v1/terror-zone?t={int(time.time())}'
    try:
        r = requests.get(url, headers=headers, timeout=8)
        data = r.json()
        return data.get('currentTerrorZone', {}).get('zone', 'PENDING').upper()
    except:
        return 'PENDING'

@app.route('/avatar.gif')
def avatar():
    zone = get_zone()
    font_path = os.path.join(BASE_DIR, 'font.ttf')
    font = ImageFont.truetype(font_path, 9) if os.path.exists(font_path) else ImageFont.load_default()

    frames = []
    for i in range(3):
        img = Image.new('RGB', (64, 64), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 0, 63, 63), outline=(180, 30, 0), width=1)

        if i == 0:
            draw.text((4, 10), zone[:12], fill=(255, 255, 255), font=font)
        elif i == 1:
            mins = 60 - datetime.now().minute
            draw.text((4, 10), f"{mins}M", fill=(255, 215, 0), font=font)
        else:
            draw.text((4, 10), "TZ", fill=(200, 40, 0), font=font)

        frames.append(img)

    buf = io.BytesIO()
    frames[0].save(buf, format='GIF', save_all=True, append_images=frames[1:], duration=700, loop=0, optimize=True)
    buf.seek(0)

    res = Response(buf, mimetype='image/gif')
    res.headers['Cache-Control'] = 'no-cache'
    return res

if __name__ == '__main__':
    app.run()
