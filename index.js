const express = require('express');
const sharp = require('sharp');
const axios = require('axios');
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
      const text = response.data;

      console.log('Page fetched - length:', text.length);

      // Flexible extraction (ignore case, extra spaces, HTML tags)
      const currentMatch = text.match(/Current\s*Terror\s*Zone:\s*([^<>\n]+)/i);
      if (currentMatch) {
        current = currentMatch[1].trim().split(/immun/i)[0].trim();
        console.log('Current zone extracted:', current);
      }

      const nextMatch = text.match(/Next\s*Terror\s*Zone:\s*([^<>\n]+)/i);
      if (nextMatch) {
        next = nextMatch[1].trim().split(/immun/i)[0].trim();
        console.log('Next zone extracted:', next);
      }

      // Log raw snippet around label for debug
      if (text.match(/Current\s*Terror\s*Zone:/i)) {
        const start = text.toUpperCase().indexOf('CURRENT TERROR ZONE:');
        console.log('Raw snippet around current label:', text.substring(start, start + 200));
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

    // Load bg.jpg
    let image = sharp(bgPath);
    const metadata = await image.metadata();
    if (metadata.width !== 300 || metadata.height !== 140) {
      image = image.resize(300, 140, { fit: 'cover' });
    }

    // Text overlay SVG (no title or footer text)
    const svg = `
      <svg width="300" height="140">
        <text x="10" y="50" fill="#fff" font-size="16" font-family="Arial, sans-serif">Now: ${current}</text>
        <text x="10" y="75" fill="#fff" font-size="16" font-family="Arial, sans-serif">Next: ${next}</text>
        <text x="10" y="100" fill="#ff0" font-size="14" font-family="Arial, sans-serif">${countdown}</text>
      </svg>`;

    const svgBuffer = Buffer.from(svg);

    // Composite text on bg
    const finalImage = await image.composite([{ input: svgBuffer, top: 0, left: 0 }]).png().toBuffer();

    res.set('Content-Type', 'image/png');
    res.set('Cache-Control', 'no-cache, no-store, must-revalidate');
    res.send(finalImage);
  } catch (err) {
    console.error('Error:', err.message);
    res.status(500).send('Error generating sig');
  }
});

app.listen(port, () => console.log(`Listening on port ${port}`));
