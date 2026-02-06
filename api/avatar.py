import io
import os
import requests
import textwrap
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
        for attempt in range(3):
            try:
                response = requests.get(tz_url, headers=headers, timeout=15)
                if response.status_code != 200:
                    raise requests.exceptions.HTTPError(f"Status {response.status_code}")
                data = response.json()

                current_zone = data.get('currentTerrorZone', {}).get('zone', 'PENDING')
                next_zone = data.get('nextTerrorZone', {}).get('zone', 'PENDING')

                if current_zone == 'Unknown' or not current_zone.strip():
                    current_zone = 'PENDING'
                if next_zone == 'Unknown' or not next_zone.strip():
                    next_zone = 'PENDING'

                return current_zone.upper(), next_zone.upper()
            except Exception as e:
                if attempt == 2:
                    return f'ERR {response.status_code if "response" in locals() else "unknown"}', 'ERR'
                time.sleep(2)
    except Exception:
        return 'FETCH ERROR', 'FETCH ERROR'

@app.route('/avatar.gif')
def avatar():
    current_zone, next_zone = get_terror_zones()

    font_path = os.path.join(BASE_DIR, 'font.ttf')
    try:
        font = ImageFont.truetype(font_path, 8)
    except:
        font = ImageFont.load_default()

    wrapper = textwrap.TextWrapper(width=12)
    curr_lines = wrapper.wrap(current_zone)
    next_lines = wrapper.wrap(next_zone)

    frames = []
    bg_colors = [(0, 0, 0), (10, 0, 0), (20, 0, 0)]

    for i in range(3):
        img = Image.new('RGB', (64, 64), bg_colors[i])
        draw = ImageDraw.Draw(img)

        draw.rectangle((0, 0, 63, 63), outline=(200, 40, 0), width=1)

        y = 6

        if i == 0:
            draw.text((4, y), "NOW:", fill=(255, 165, 0), font=font)
            y += 10
            for line in curr_lines:
                draw.text((4, y), line, fill=(255, 255, 255), font=font)
                y += 9
        elif i == 1:
            mins = 60 - datetime.now().minute
            timer_text = f"{mins}M LEFT"
            draw.text((4, 12), timer_text, fill=(255, 215, 0), font=font)
            draw.text((4, 30), "TIME", fill=(220, 220, 150), font=font)
        else:
            draw.text((4, y), "NEXT:", fill=(200, 40, 0), font=font)
            y += 10
            for line in next_lines:
                draw.text((4, y), line, fill=(220, 220, 150), font=font)
                y += 9

        frames.append(img)

    buf = io.BytesIO()
    frames[0].save(
        buf,
        format='GIF',
        save_all=True,
        append_images=frames[1:],
        duration=1000,
        loop=0,
        optimize=True
    )
    buf.seek(0)

    res = Response(buf, mimetype='image/gif')
    res.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return res

if __name__ == '__main__':
    app.run()
