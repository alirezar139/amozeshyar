// Turns the SVG sources here into the PNGs @capacitor/assets expects
// (it doesn't read SVG), then `capacitor-assets generate` makes every
// launcher-icon and splash size from them. For an instructor's own
// branding, edit the SVGs (or drop in a 1024px icon-only.png) and run
// `npm run assets`.
import sharp from 'sharp'

const dir = new URL('./', import.meta.url).pathname
const svg = (name) => sharp(`${dir}${name}.svg`, { density: 300 })

const foreground = await svg('icon-foreground').resize(1024, 1024).png().toBuffer()
const background = await svg('icon-background').resize(1024, 1024).png().toBuffer()

await sharp(foreground).toFile(`${dir}icon-foreground.png`)
await sharp(background).toFile(`${dir}icon-background.png`)
// Legacy (pre-adaptive) icon: the two layers flattened.
await sharp(background).composite([{ input: foreground }]).toFile(`${dir}icon-only.png`)

// Splash: the mark at a third of the shorter side, on the same background.
const splash = async (file) => {
  const size = 2732
  const mark = await sharp(foreground).resize(Math.round(size / 2.2)).toBuffer()
  await sharp(background).resize(size, size).composite([{ input: mark, gravity: 'center' }]).toFile(`${dir}${file}`)
}
await splash('splash.png')
await splash('splash-dark.png')
