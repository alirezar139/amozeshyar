// Turns a single picked hex color into a full 50-950 tint/shade ramp, so
// a user can pick any color at all (not just from a curated list) and
// still get a usable set of Tailwind-style shades for it. The picked hex
// becomes the "500" (accent-style) or "600" (primary/header/nav-style)
// step exactly — matching which weight each role is actually used at
// across the app (buttons use bg-primary-600 / bg-accent-500, header and
// nav follow primary's convention) — and the rest of the ramp is derived
// by shifting lightness around that anchor, keeping hue/saturation fixed.
export type ColorRamp = Record<string, string>
export type ColorRole = 'primary' | 'accent' | 'header' | 'nav'

function hexToRgb(hex: string): [number, number, number] {
  const clean = hex.replace('#', '').trim()
  const full = clean.length === 3 ? clean.split('').map((c) => c + c).join('') : clean
  const num = parseInt(full, 16) || 0
  return [(num >> 16) & 255, (num >> 8) & 255, num & 255]
}

function rgbToHsl(r: number, g: number, b: number): [number, number, number] {
  r /= 255
  g /= 255
  b /= 255
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  const l = (max + min) / 2
  const d = max - min
  let h = 0
  let s = 0
  if (d !== 0) {
    s = d / (1 - Math.abs(2 * l - 1))
    if (max === r) h = ((g - b) / d) % 6
    else if (max === g) h = (b - r) / d + 2
    else h = (r - g) / d + 4
    h *= 60
    if (h < 0) h += 360
  }
  return [h, s * 100, l * 100]
}

function hslToRgb(h: number, s: number, l: number): [number, number, number] {
  s /= 100
  l /= 100
  const c = (1 - Math.abs(2 * l - 1)) * s
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1))
  const m = l - c / 2
  let [r, g, b] = [0, 0, 0]
  if (h < 60) [r, g, b] = [c, x, 0]
  else if (h < 120) [r, g, b] = [x, c, 0]
  else if (h < 180) [r, g, b] = [0, c, x]
  else if (h < 240) [r, g, b] = [0, x, c]
  else if (h < 300) [r, g, b] = [x, 0, c]
  else [r, g, b] = [c, 0, x]
  return [Math.round((r + m) * 255), Math.round((g + m) * 255), Math.round((b + m) * 255)]
}

const clampLightness = (l: number) => Math.min(97, Math.max(3, l))

const PRIMARY_OFFSETS: Record<string, number> = {
  '50': 53, '100': 45, '200': 33, '300': 22, '400': 11, '500': 5,
  '600': 0, '700': -8, '800': -16, '900': -23, '950': -30,
}
const ACCENT_OFFSETS: Record<string, number> = {
  '50': 48, '100': 41, '200': 30, '300': 20, '400': 9,
  '500': 0, '600': -8, '700': -15, '800': -21, '900': -27,
}

export function generateRamp(hex: string, role: ColorRole): ColorRamp {
  const [r, g, b] = hexToRgb(hex)
  const [h, s, l] = rgbToHsl(r, g, b)
  const offsets = role === 'accent' ? ACCENT_OFFSETS : PRIMARY_OFFSETS
  const ramp: ColorRamp = {}
  for (const [step, delta] of Object.entries(offsets)) {
    const [rr, gg, bb] = hslToRgb(h, s, clampLightness(l + delta))
    ramp[step] = `${rr} ${gg} ${bb}`
  }
  return ramp
}
