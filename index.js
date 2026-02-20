const express = require('express');
const sharp = require('sharp');
const axios = require('axios');
const fs = require('fs');
const path = require('path');

const app = express();
const port = process.env.PORT || 3000;

// Path to bg.jpg in repo root
const bgPath = path.join(__dirname, 'bg.jpg');

app.get('/signature.png', async (req, res) => {
  try {
    let current = 'REPORT PENDING';
    let next = 'PENDING';

    try {
      const response = await axios.get('https://d2emu.com/tz', {
        timeout: 10000,
        headers: { 'User-Agent': 'Mozilla/5.0' }
      });
      const text = response.data.toUpperCase();

      const currentMatch = text.match(/CURRENT TERROR ZONE:\s*([^\n<]+)/i);
      if (currentMatch) {
        current = currentMatch[1].trim().split('IMMUN')[0].trim();
      }

      const nextMatch = text.match(/NEXT TERROR ZONE:\s*([^\n<]+)/i);
      if (nextMatch) {
        next = nextMatch[1].trim().split('IMMUN')[0].trim();
      }
    } catch (err) {
      console.error('Fetch error:', err.message);
    }

    // 30-minute countdown
    const now = new Date();
    const minutes = now.getUTCMinutes();
    const seconds = now.getUTCSeconds();
    const minutesToNext = 30 - (minutes % 30);
    const secondsToNext = minutesToNext * 60 - seconds;
    const minsLeft = Math.floor(secondsToNext / 60);
    const secsLeft = secondsToNext % 60;
    const countdown = minsLeft === 0 ? `${secsLeft} seconds until` : `${minsLeft} min, ${secsLeft.toString().padStart(2, '0')} sec until`;

    // Load background image (resize to 300x140 if needed)
    let image = sharp(bgPath);
    const metadata = await image.metadata();
    if (metadata.width !== 300 || metadata.height !== 140) {
      image = image.resize(300, 140, { fit: 'cover' });
    }

    // Text overlay SVG
    const svg = `
      <svg width="300" height="140">
        <text x="10" y="30" fill="#c00" font-size="20" font-family="Arial, sans-serif" font-weight="bold">TERROR ZONES</text>
        <text x="10" y="60" fill="#fff" font-size="16" font-family="Arial, sans-serif">Now: ${current}</text>
        <text x="10" y="85" fill="#fff" font-size="16" font-family="Arial, sans-serif">Next: ${next}</text>
        <text x="10" y="110" fill="#ff0" font-size="14" font-family="Arial, sans-serif">${countdown}</text>
        <text x="220" y="130" fill="#888" font-size="12" font-family="Arial, sans-serif">Guy_T</text>
      </svg>`;

    const svgBuffer = Buffer.from(svg);

    // Composite text on top of bg
    const finalImage = await image.composite([{ input: svgBuffer, top: 0, left: 0 }]).png().toBuffer();

    res.set('Content-Type', 'image/png');
    res.set('Cache-Control', 'no-cache, no-store, must-revalidate');
    res.send(finalImage);
  } catch (err) {
    console.error(err.message);
    res.status(500).send('Error generating sig');
  }
});

app.listen(port, () => console.log(`Listening on port ${port}`));
