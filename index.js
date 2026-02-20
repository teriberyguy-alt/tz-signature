const express = require('express');
const sharp = require('sharp');
const axios = require('axios');
const cheerio = require('cheerio');

const app = express();
const port = process.env.PORT || 3000;

// Route for signature
app.get('/signature.png', async (req, res) => {
  try {
    const response = await axios.get('https://d2emu.com/tz', {
      timeout: 10000,
      headers: { 'User-Agent': 'Mozilla/5.0' }
    });
    const $ = cheerio.load(response.data);

    let current = 'REPORT PENDING';
    let next = 'PENDING';

    // Extract zones from page text
    const text = $('body').text().toUpperCase();
    const currentMatch = text.match(/CURRENT TERROR ZONE:\s*([^\n]+)/i);
    if (currentMatch) {
      current = currentMatch[1].trim().split('IMMUN')[0].trim();
    }

    const nextMatch = text.match(/NEXT TERROR ZONE:\s*([^\n]+)/i);
    if (nextMatch) {
      next = nextMatch[1].trim().split('IMMUN')[0].trim();
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

    // Generate image with sharp (fast & simple)
    const svg = `
      <svg width="300" height="140">
        <rect width="300" height="140" fill="#111"/>
        <text x="10" y="30" fill="#c00" font-size="20" font-family="Arial">TERROR ZONES</text>
        <text x="10" y="60" fill="#fff" font-size="16" font-family="Arial">Now: ${current}</text>
        <text x="10" y="85" fill="#fff" font-size="16" font-family="Arial">Next: ${next}</text>
        <text x="10" y="110" fill="#ff0" font-size="14" font-family="Arial">${countdown}</text>
        <text x="220" y="130" fill="#888" font-size="12" font-family="Arial">Guy_T</text>
      </svg>`;

    const buffer = await sharp(Buffer.from(svg)).png().toBuffer();

    res.set('Content-Type', 'image/png');
    res.set('Cache-Control', 'no-cache, no-store, must-revalidate');
    res.send(buffer);
  } catch (err) {
    console.error(err);
    res.status(500).send('Error generating sig');
  }
});

app.listen(port, () => console.log(`Listening on port ${port}`));
