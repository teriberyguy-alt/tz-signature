import io
import os
import requests
import textwrap
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, Response
from bs4 import BeautifulSoup

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_terror_zones():
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
        }
        tz_url = 'https://d2emu.com/tz'
        for attempt in range(2):
            try:
                response = requests.get(tz_url, headers=headers, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                full_text = soup.get_text(separator=' ', strip=True).upper()

                current_zone = 'PENDING'
                next_zone = 'PENDING'

                # Parse markdown table for zones
                lines = response.text.splitlines()
                zone_candidates = []
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith('|') and '|' in stripped[1:] and '---' not in stripped:
                        parts = [p.strip().upper() for p in stripped.split('|') if p.strip()]
                        if len(parts) >= 2:
                            zone_text = ' '.join(parts[1:])
                            if zone_text:
                                zone_candidates.append(zone_text)

                if zone_candidates:
                    current_zone = zone_candidates[0]
                    if len(zone_candidates) > 1:
                        next_zone = ' '.join(zone_candidates[1:])

                return current_zone, next_zone
            except requests.exceptions.RequestException:
                if attempt == 1:
                    return 'FETCH FAIL', 'FETCH FAIL'
                time.sleep(1)
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

    wrapper = textwrap.TextWrapper(width=12) # adjust if needed
    curr_lines = wrapper.wrap(current_zone)
    next_lines = wrapper.wrap(next_zone)

    frames = []
    bg_colors = [(0, 0, 0), (10, 0, 0), (20, 0, 0)]

    for i in range(3):
        img = Image.new('RGB', (64, 64), bg_colors[i])
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 0, 63, 63), outline=(200, 40, 0), width=1)
        y = 6 # start position
        if i == 0:
            # Frame 1: NOW + current zone (wrapped)
            draw.text((4, y), "NOW:", fill=(255, 165, 0), font=font)
            y += 10
            for line in curr_lines:
                draw.text((4, y), line, fill=(255, 255, 255), font=font)
                y += 9
        elif i == 1:
            # Frame 2: Timer
            mins = 60 - datetime.now().minute
            timer_text = f"{mins}M LEFT"
            draw.text((4, 12), timer_text, fill=(255, 215, 0), font=font)
            draw.text((4, 30), "TIME", fill=(220, 220, 150), font=font)
        else:
            # Frame 3: NEXT + next zone (wrapped)
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
        duration=1000, # 1 second per frame = easier to read
        loop=0,
        optimize=True
    )
    buf.seek(0)
    res = Response(buf, mimetype='image/gif')
    res.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return res

if __name__ == '__main__':
    app.run()
