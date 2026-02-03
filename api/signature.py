import io
import requests
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, Response

app = Flask(__name__)

@app.route('/signature.png')
def generate_signature():
    # Fetch the Terror Zones data from the simple API
    tz_url = 'https://d2runewizard.com/api/terror-zone'
    response = requests.get(tz_url)
    tz_text = response.text.strip().split('\n')
    
    # Parse the current and next zones (assuming the format stays as "Current terror zone: Name, actX.")
    current_tz = tz_text[0].split(': ')[1].strip() if len(tz_text) > 0 else 'Unknown'
    next_tz = tz_text[1].split(': ')[1].strip() if len(tz_text) > 1 else 'Unknown'
    
    # Combine them into the text to overlay (you can customize this line if needed)
    overlay_text = f"Current: {current_tz}\nNext: {next_tz}"
    
    # Load the background image
    bg_image = Image.open('bg.jpg')
    
    # Create a drawing context
    draw = ImageDraw.Draw(bg_image)
    
    # Load your custom font (adjust size 12 if text is too small/big)
    font = ImageFont.truetype('font.ttf', 12)
    
    # Position the text (x=10, y=100) - bottom-leftish. Adjust numbers if text doesn't fit well (e.g., try y=50 for higher up)
    draw.multiline_text((10, 100), overlay_text, font=font, fill=(255, 255, 255))  # White text; change (R,G,B) for other colors
    
    # Save the image to bytes (in-memory)
    img_bytes = io.BytesIO()
    bg_image.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    # Return as PNG
    return Response(img_bytes, mimetype='image/png')

if __name__ == '__main__':
    app.run()