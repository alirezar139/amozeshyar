// Turns the SVG sources here into the PNGs @capacitor/assets expects
// (it doesn't read SVG) plus the website's PWA icons, then `capacitor-assets generate` makes every
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

// The same mark for the website's PWA (iPhone "Add to Home Screen", Android
// "Install app"): frontend/public/icons/. iOS ignores transparency, so its
// apple-touch-icon is the flattened icon.
const web = new URL('../../frontend/public/icons/', import.meta.url).pathname
const flat = await sharp(background).composite([{ input: foreground }]).png().toBuffer()
for (const size of [192, 512]) {
  await sharp(flat).resize(size).toFile(`${web}icon-${size}.png`)
}
// "maskable": launchers crop it to their own shape, so the mark sits in the middle 80%.
const inner = await sharp(foreground).resize(Math.round(512 * 0.8)).toBuffer()
await sharp(background).resize(512, 512).composite([{ input: inner, gravity: 'center' }]).toFile(`${web}maskable-512.png`)
await sharp(flat).resize(180).toFile(`${web}apple-touch-icon.png`)
