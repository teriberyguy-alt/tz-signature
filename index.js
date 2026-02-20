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
      const text = response.data.toUpperCase();

      console.log('Page fetched successfully - length:', text.length);

      // Extract current zone - look for label and grab until next label or junk
      const currentLabel = 'CURRENT TERROR ZONE:';
      const nextLabel = 'NEXT TERROR ZONE:';
      const immunLabel = 'TERROR ZONE HAS MONSTERS WITH IMMUNITIES';

      if (currentLabel in text) {
        const start = text.indexOf(currentLabel) + currentLabel.length;
        let end = text.indexOf(nextLabel, start);
        if (end === -1) end = text.indexOf(immunLabel, start);
        if (end === -1) end = text.length;
        let snippet = text.substring(start, end).trim();
        // Clean extra junk
        snippet = snippet.split(/[\n<]/)[0].trim();
        if (snippet.length > 3 && snippet !== '---') {
          current = snippet;
          console.log('Current zone extracted:', current);
        }
      }

      if (nextLabel in text) {
        const start = text.indexOf(nextLabel) + nextLabel.length;
        let end = text.indexOf(immunLabel, start);
        if (end === -1) end = text.length;
        let snippet = text.substring(start, end).trim();
        snippet = snippet.split(/[\n<]/)[0].trim();
        if (snippet.length > 3 && snippet !== '---') {
          next = snippet;
          console.log('Next zone extracted:', next);
        }
      }

      if (current === 'REPORT PENDING') {
        console.log('No current zone found in page text');
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

    // Load background
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
