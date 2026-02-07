const express = require('express');
const fetch = require('node-fetch');
const sharp = require('sharp');
const cheerio = require('cheerio');
const path = require('path');

const app = express();

const BASE_DIR = path.join(__dirname, '..');

async function getTerrorZones() {
  const headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
  };
  const tzUrl = 'https://d2emu.com/tz';

  try:
    const response = await fetch(tzUrl, { headers, timeout: 15000 });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    
    const text = await response.text();
    const $ = cheerio.load(text);
    let currentZone = 'REPORT PENDING';
    let nextZone = 'PENDING';

    const lines = text.split('\n');
    const zoneCandidates = [];
    for (let line of lines) {
      const stripped = line.trim();
      if (stripped.startsWith('|  |') && !stripped.includes('---') && !stripped.toLowerCase().includes('immunities')) {
        const parts = stripped.split('|').map(p => p.trim().toUpperCase()).filter(p => p);
        if (parts.length >= 2) {
          const zoneText = parts.slice(1).join(' ').trim();
          if (zoneText && zoneText.length > 3) {
            zoneCandidates.push(zoneText);
          }
        }
      }
    }

    if (zoneCandidates.length > 0) {
      currentZone = zoneCandidates[0];
      if (zoneCandidates.length > 1) {
        nextZone = zoneCandidates.slice(1).join(' ');
      }
    }

    return { currentZone, nextZone };
  } catch (e) {
    return { currentZone: 'FETCH FAIL', nextZone: 'FETCH FAIL' };
  }
}

app.get('/avatar.gif', async (req, res) => {
  const { currentZone, nextZone } = await getTerrorZones();

  const fontPath = path.join(BASE_DIR, 'font.ttf');

  // Sharp doesn't support text, so use canvas or svg for text - placeholder for now
  // To make it work, add 'canvas' to package.json and use it

  const buf = Buffer.from('GIF placeholder - add canvas for text');  // Placeholder

  res.set('Content-Type', 'image/gif');
  res.set('Cache-Control', 'no-cache, no-store, must-revalidate');
  res.send(buf);
});

module.exports = app;
