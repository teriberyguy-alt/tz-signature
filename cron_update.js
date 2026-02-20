const sharp = require('sharp');
const axios = require('axios');
const fs = require('fs');
const path = require('path');

async function updateSig() {
  let current = 'PENDING';
  let next = 'PENDING';

  try {
    const res = await axios.get('https://d2emu.com/tz', { timeout: 10000 });
    const text = res.data.toUpperCase();

    const cMatch = text.match(/CURRENT TERROR ZONE:\s*([^\n<]+)/i);
    if (cMatch) current = cMatch[1].trim().split('IMMUN')[0].trim();

    const nMatch = text.match(/NEXT TERROR ZONE:\s*([^\n<]+)/i);
    if (nMatch) next = nMatch[1].trim().split('IMMUN')[0].trim();
  } catch (err) {
    console.error('Fetch failed:', err.message);
  }

  // Countdown
  const now = new Date();
  const minsToNext = 30 - (now.getUTCMinutes() % 30);
  const countdown = `${minsToNext} min until`;

  // Load bg
  const bg = await sharp('bg.jpg').resize(300, 140).toBuffer();

  // Text SVG
  const svg = `<svg width="300" height="140"><text x="10" y="50" fill="#fff" font-size="16">Now: ${current}</text><text x="10" y="75" fill="#fff" font-size="16">Next: ${next}</text><text x="10" y="100" fill="#ff0" font-size="14">${countdown}</text></svg>`;
  const svgBuffer = Buffer.from(svg);

  // Composite
  const final = await sharp(bg).composite([{ input: svgBuffer, top: 0, left: 0 }]).png().toFile('public/sig.png');

  console.log('Sig updated at', new Date());
}

updateSig();
