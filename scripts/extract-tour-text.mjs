// One-off helper: parses the TOUR_STEPS object out of useGuide.ts and
// writes a flat list of { route, index, title, text } to stdout as JSON.
// Not part of the app itself — used only when (re)generating the
// pre-rendered narration audio in public/audio/tour/.
import { readFileSync } from 'node:fs'

const src = readFileSync(new URL('../frontend/composables/useGuide.ts', import.meta.url), 'utf8')

const start = src.indexOf('export const TOUR_STEPS')
const braceStart = src.indexOf('{', start)
let depth = 0
let end = braceStart
for (let i = braceStart; i < src.length; i++) {
  if (src[i] === '{') depth++
  else if (src[i] === '}') {
    depth--
    if (depth === 0) {
      end = i
      break
    }
  }
}
const body = src.slice(braceStart + 1, end)

const routeKeyRe = /^\s{2}(?:'([\w-]+)'|(\w[\w-]*)):\s*\[/
const stepRe = /\{\s*selector:\s*'([^']*)',\s*title:\s*'((?:[^'\\]|\\.)*)',\s*text:\s*'((?:[^'\\]|\\.)*)'\s*\}/g

const results = []
let currentRoute = null
for (const line of body.split('\n')) {
  const routeMatch = line.match(routeKeyRe)
  if (routeMatch) {
    currentRoute = routeMatch[1] ?? routeMatch[2]
    continue
  }
  if (!currentRoute) continue
  for (const m of line.matchAll(stepRe)) {
    results.push({
      route: currentRoute,
      index: results.filter((r) => r.route === currentRoute).length,
      title: m[2].replace(/\\'/g, "'"),
      text: m[3].replace(/\\'/g, "'"),
    })
  }
}

console.log(JSON.stringify(results, null, 2))
