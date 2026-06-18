#!/usr/bin/env node
/**
 * Generate PNG icons for PWA apps.
 * Creates 192x192, 512x512, and maskable icon variants with app-specific colors.
 * Usage: node scripts/generate-pwa-icons.js
 */

import sharp from 'sharp'
import { promises as fs } from 'fs'
import { dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const projectRoot = dirname(__dirname)

const apps = [
  {
    name: 'design_time',
    label: 'DT',
    color: '#8B5CF6', // Purple
  },
  {
    name: 'run_time',
    label: 'RT',
    color: '#06B6D4', // Cyan
  },
  {
    name: 'erp_simulator',
    label: 'ERP',
    color: '#EC4899', // Pink
  },
  {
    name: 'equipment_simulator',
    label: 'EQ',
    color: '#F59E0B', // Amber
  },
]

async function generateIcon(size, label, color, maskable = false) {
  const padding = Math.round(size * 0.15)
  const innerSize = size - padding * 2
  const fontSize = Math.round(innerSize * 0.5)

  // SVG with centered text
  const svg = `
    <svg width="${size}" height="${size}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:${color};stop-opacity:1" />
          <stop offset="100%" style="stop-color:${adjustColor(color, -20)};stop-opacity:1" />
        </linearGradient>
        ${maskable ? `<mask id="mask"><rect width="${size}" height="${size}" fill="white" rx="${Math.round(size * 0.2)}"/></mask>` : ''}
      </defs>
      <rect width="${size}" height="${size}" fill="url(#grad)" ${maskable ? 'mask="url(#mask)"' : ''}/>
      <text x="${size / 2}" y="${size / 2 + fontSize / 3}" font-size="${fontSize}" font-weight="bold" fill="white" text-anchor="middle" dominant-baseline="middle" font-family="system-ui, sans-serif">${label}</text>
    </svg>
  `

  return sharp(Buffer.from(svg)).png().toBuffer()
}

function adjustColor(hex, percent) {
  const num = parseInt(hex.slice(1), 16)
  const amt = Math.round(2.55 * percent)
  const R = (num >> 16) + amt
  const G = (num >> 8) + amt & 0x00FF
  const B = (num + amt) & 0x0000FF
  return `#${(0x1000000 + (R < 255 ? R < 1 ? 0 : R : 255) * 0x10000 + (G < 255 ? G < 1 ? 0 : G : 255) * 0x100 + (B < 255 ? B < 1 ? 0 : B : 255)).toString(16).slice(1)}`
}

async function main() {
  for (const app of apps) {
    const publicDir = `${projectRoot}/clients/${app.name}/public`

    // Create public dir if it doesn't exist
    await fs.mkdir(publicDir, { recursive: true })

    console.log(`Generating icons for ${app.name}...`)

    // Generate 192x192
    const icon192 = await generateIcon(192, app.label, app.color)
    await fs.writeFile(`${publicDir}/icon-192x192.png`, icon192)
    console.log(`  ✓ icon-192x192.png`)

    // Generate 512x512
    const icon512 = await generateIcon(512, app.label, app.color)
    await fs.writeFile(`${publicDir}/icon-512x512.png`, icon512)
    console.log(`  ✓ icon-512x512.png`)

    // Generate maskable variant (for adaptive icons on Android)
    const iconMaskable = await generateIcon(512, app.label, app.color, true)
    await fs.writeFile(`${publicDir}/icon-512x512-maskable.png`, iconMaskable)
    console.log(`  ✓ icon-512x512-maskable.png`)
  }

  console.log('\n✓ All PWA icons generated successfully')
}

main().catch(console.error)
