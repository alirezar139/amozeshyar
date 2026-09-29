/**
 * Full-screen WebGL fragment-shader backgrounds. Each effect is a GLSL
 * `vec3 effect(vec2 uv, vec2 p, float t)` body appended to a shared header
 * (simplex noise, fbm, the palette uniforms). Plain WebGL 1, no libraries.
 */

export type ShaderEffect = 'mesh' | 'liquid' | 'northern' | 'silk' | 'nebula' | 'caustics' | 'lava' | 'lines'
export const SHADER_EFFECTS: ShaderEffect[] = ['mesh', 'liquid', 'northern', 'silk', 'nebula', 'caustics', 'lava', 'lines']

const VERTEX = `
attribute vec2 aPos;
varying vec2 vUv;
void main() { vUv = aPos * 0.5 + 0.5; gl_Position = vec4(aPos, 0.0, 1.0); }
`

const HEADER = `
precision highp float;
uniform float uTime;
uniform vec2 uRes;
uniform vec2 uMouse;
uniform vec3 uC1;
uniform vec3 uC2;
uniform vec3 uC3;
uniform float uDark;
varying vec2 vUv;

// Ashima 3D simplex noise
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 permute(vec4 x) { return mod289(((x * 34.0) + 1.0) * x); }
vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }
float snoise(vec3 v) {
  const vec2 C = vec2(1.0 / 6.0, 1.0 / 3.0);
  const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
  vec3 i = floor(v + dot(v, C.yyy));
  vec3 x0 = v - i + dot(i, C.xxx);
  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min(g.xyz, l.zxy);
  vec3 i2 = max(g.xyz, l.zxy);
  vec3 x1 = x0 - i1 + C.xxx;
  vec3 x2 = x0 - i2 + C.yyy;
  vec3 x3 = x0 - D.yyy;
  i = mod289(i);
  vec4 p = permute(permute(permute(i.z + vec4(0.0, i1.z, i2.z, 1.0)) + i.y + vec4(0.0, i1.y, i2.y, 1.0)) + i.x + vec4(0.0, i1.x, i2.x, 1.0));
  float n_ = 0.142857142857;
  vec3 ns = n_ * D.wyz - D.xzx;
  vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
  vec4 x_ = floor(j * ns.z);
  vec4 y_ = floor(j - 7.0 * x_);
  vec4 x = x_ * ns.x + ns.yyyy;
  vec4 y = y_ * ns.x + ns.yyyy;
  vec4 h = 1.0 - abs(x) - abs(y);
  vec4 b0 = vec4(x.xy, y.xy);
  vec4 b1 = vec4(x.zw, y.zw);
  vec4 s0 = floor(b0) * 2.0 + 1.0;
  vec4 s1 = floor(b1) * 2.0 + 1.0;
  vec4 sh = -step(h, vec4(0.0));
  vec4 a0 = b0.xzyw + s0.xzyw * sh.xxyy;
  vec4 a1 = b1.xzyw + s1.xzyw * sh.zzww;
  vec3 p0 = vec3(a0.xy, h.x);
  vec3 p1 = vec3(a0.zw, h.y);
  vec3 p2 = vec3(a1.xy, h.z);
  vec3 p3 = vec3(a1.zw, h.w);
  vec4 norm = taylorInvSqrt(vec4(dot(p0, p0), dot(p1, p1), dot(p2, p2), dot(p3, p3)));
  p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
  vec4 m = max(0.6 - vec4(dot(x0, x0), dot(x1, x1), dot(x2, x2), dot(x3, x3)), 0.0);
  m = m * m;
  return 42.0 * dot(m * m, vec4(dot(p0, x0), dot(p1, x1), dot(p2, x2), dot(p3, x3)));
}
float fbm(vec3 p) {
  float v = 0.0;
  float a = 0.5;
  for (int i = 0; i < 5; i++) { v += a * snoise(p); p *= 2.02; a *= 0.5; }
  return v;
}
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
vec3 pal(float x) { x = fract(x); return x < 0.5 ? mix(uC1, uC2, x * 2.0) : mix(uC2, uC3, x * 2.0 - 1.0); }
`

const FOOTER = `
void main() {
  vec2 uv = vUv;
  vec2 p = vec2(uv.x * uRes.x / uRes.y, uv.y);
  vec3 col = effect(uv, p, uTime);
  // Light mode: airy pastel so text stays readable; dark mode: deep and rich.
  vec3 light = mix(col, vec3(1.0), 0.28);
  vec3 dark = col * 0.62;
  gl_FragColor = vec4(mix(light, dark, uDark), 1.0);
}
`

const EFFECTS: Record<ShaderEffect, string> = {
  // Stripe-style mesh gradient: colors pinned to slowly orbiting points,
  // blended by inverse distance over a noise-warped plane.
  mesh: `
vec3 effect(vec2 uv, vec2 p, float t) {
  vec2 q = p + 0.22 * vec2(snoise(vec3(p * 1.3, t * 0.07)), snoise(vec3(p * 1.3 + 9.1, t * 0.07)));
  float ar = uRes.x / uRes.y;
  vec2 a = vec2(ar * (0.25 + 0.15 * sin(t * 0.13)), 0.75 + 0.15 * cos(t * 0.11)) + (uMouse - 0.5) * 0.1;
  vec2 b = vec2(ar * (0.8 + 0.12 * cos(t * 0.09)), 0.7 + 0.2 * sin(t * 0.12));
  vec2 c = vec2(ar * (0.55 + 0.2 * sin(t * 0.07 + 2.0)), 0.2 + 0.18 * cos(t * 0.1 + 1.0));
  vec2 d = vec2(ar * (0.1 + 0.1 * cos(t * 0.08 + 4.0)), 0.15 + 0.1 * sin(t * 0.09));
  float wa = 1.0 / (pow(distance(q, a), 2.2) + 0.02);
  float wb = 1.0 / (pow(distance(q, b), 2.2) + 0.02);
  float wc = 1.0 / (pow(distance(q, c), 2.2) + 0.02);
  float wd = 1.0 / (pow(distance(q, d), 2.2) + 0.02);
  vec3 col = (uC1 * wa + uC2 * wb + uC3 * wc + mix(uC1, vec3(1.0), 0.6) * wd) / (wa + wb + wc + wd);
  col += 0.04 * snoise(vec3(p * 3.0, t * 0.2));
  return col;
}`,

  // Domain-warped fbm (Inigo Quilez) — liquid marble veins.
  liquid: `
vec3 effect(vec2 uv, vec2 p, float t) {
  p *= 1.6;
  vec2 q = vec2(fbm(vec3(p, t * 0.05)), fbm(vec3(p + vec2(5.2, 1.3), t * 0.05)));
  vec2 r = vec2(fbm(vec3(p + 4.0 * q + vec2(1.7, 9.2), t * 0.07)), fbm(vec3(p + 4.0 * q + vec2(8.3, 2.8), t * 0.07)));
  float f = fbm(vec3(p + 4.0 * r, t * 0.03));
  vec3 col = mix(uC1, uC2, clamp(f * f * 4.0, 0.0, 1.0));
  col = mix(col, uC3, clamp(length(q), 0.0, 1.0));
  col = mix(col, vec3(1.0), clamp(r.x * r.x, 0.0, 1.0) * 0.5);
  return col * (0.55 + 1.1 * (f * f * f + 0.6 * f * f + 0.5 * f));
}`,

  // Aurora borealis: noisy curtains with vertical rays over a sky.
  northern: `
vec3 effect(vec2 uv, vec2 p, float t) {
  vec3 sky = mix(mix(vec3(0.72, 0.84, 0.98), vec3(0.93, 0.96, 1.0), uv.y), mix(vec3(0.01, 0.03, 0.09), vec3(0.05, 0.08, 0.2), uv.y), uDark);
  vec3 col = sky;
  for (int i = 0; i < 4; i++) {
    float fi = float(i);
    float curtain = 0.52 + fi * 0.07 + 0.1 * sin(p.x * 1.6 + t * 0.25 + fi * 1.7) + 0.08 * snoise(vec3(p.x * 1.4, fi * 3.0, t * 0.12));
    float d = uv.y - curtain;
    float rays = 0.55 + 0.45 * snoise(vec3(p.x * 18.0, fi, t * 0.35));
    float band = exp(-d * d * 120.0) + step(0.0, d) * exp(-d * 5.0) * 0.55 * rays;
    col += pal(fi * 0.3 + 0.1 * sin(t * 0.1)) * band * (0.55 - fi * 0.08);
  }
  // a few stars for the night sky
  vec2 g = floor(uv * uRes / 3.0);
  float s = step(0.9975, hash(g)) * (0.5 + 0.5 * sin(t * 2.0 + hash(g + 1.0) * 6.28)) * uDark;
  return col + s;
}`,

  // Silk: long diagonal folds with specular highlights.
  silk: `
vec3 effect(vec2 uv, vec2 p, float t) {
  vec2 s = p * 1.4;
  float warp = fbm(vec3(s * 0.9, t * 0.08)) * 2.6;
  float w = sin(s.x * 3.0 + s.y * 2.2 + warp + t * 0.35);
  float fold = w * 0.5 + 0.5;
  vec3 base = mix(uC1, uC2, clamp(uv.y + 0.25 * w, 0.0, 1.0));
  base = mix(base, uC3, smoothstep(0.3, 1.0, snoise(vec3(s * 0.5, t * 0.05)) * 0.5 + 0.5) * 0.45);
  float shade = 0.55 + 0.55 * pow(fold, 1.4);
  float highlight = pow(fold, 22.0) * 0.55;
  return base * shade + highlight;
}`,

  // Nebula clouds with twinkling stars.
  nebula: `
vec3 effect(vec2 uv, vec2 p, float t) {
  float f = fbm(vec3(p * 1.4, t * 0.03));
  float g = fbm(vec3(p * 2.8 + f, t * 0.05));
  vec3 space = mix(vec3(0.86, 0.9, 0.97), vec3(0.01, 0.01, 0.04), uDark);
  vec3 col = space;
  col = mix(col, uC1, smoothstep(-0.2, 0.8, f) * 0.85);
  col = mix(col, uC2, smoothstep(0.0, 0.9, g) * 0.7);
  col += uC3 * pow(max(g, 0.0), 3.0) * 1.2;
  vec2 cell = floor(uv * uRes / 2.5);
  float star = step(0.996, hash(cell)) * (0.55 + 0.45 * sin(t * 3.0 + hash(cell + 3.0) * 6.28));
  return col + star * mix(0.5, 1.0, uDark);
}`,

  // Swimming-pool caustics (classic iterative pattern).
  caustics: `
vec3 effect(vec2 uv, vec2 p, float t) {
  float tt = t * 0.5 + 23.0;
  vec2 pp = mod(p * 6.28318 * 1.2, 6.28318) - 250.0;
  vec2 i = pp;
  float c = 1.0;
  float inten = 0.005;
  for (int n = 0; n < 5; n++) {
    float s = tt * (1.0 - (3.5 / float(n + 1)));
    i = pp + vec2(cos(s - i.x) + sin(s + i.y), sin(s - i.y) + cos(s + i.x));
    c += 1.0 / length(vec2(pp.x / (sin(i.x + s) / inten), pp.y / (cos(i.y + s) / inten)));
  }
  c /= 5.0;
  c = 1.17 - pow(c, 1.4);
  float v = clamp(pow(abs(c), 8.0), 0.0, 1.0);
  vec3 water = mix(uC1, uC3, uv.y);
  return mix(water * 0.75, mix(uC2, vec3(1.0), 0.5), v);
}`,

  // Lava lamp: metaballs merging and parting.
  lava: `
vec3 effect(vec2 uv, vec2 p, float t) {
  float ar = uRes.x / uRes.y;
  float s = 0.0;
  for (int i = 0; i < 7; i++) {
    float fi = float(i);
    vec2 c = vec2(ar * (0.5 + 0.38 * sin(t * 0.18 * (1.0 + fi * 0.13) + fi * 1.3)), 0.5 + 0.42 * cos(t * 0.15 * (1.0 + fi * 0.1) + fi * 2.1));
    float r = 0.1 + 0.05 * sin(fi * 1.7);
    s += r * r / dot(p - c, p - c);
  }
  float m = smoothstep(0.92, 1.08, s);
  float glow = smoothstep(0.25, 1.0, s);
  vec3 bg = mix(uC3 * 0.35 + 0.2, uC1 * 0.45 + 0.15, uv.y);
  vec3 blob = mix(uC2, uC1, uv.y + 0.2 * sin(t * 0.2));
  return mix(bg, blob, m) + glow * 0.12 + m * (1.0 - smoothstep(1.0, 1.6, s)) * 0.25;
}`,

  // Flowing glowing lines.
  lines: `
vec3 effect(vec2 uv, vec2 p, float t) {
  vec3 col = mix(vec3(0.95, 0.96, 0.99), vec3(0.02, 0.03, 0.07), uDark);
  float w = 1.6 / uRes.y;
  for (int i = 0; i < 28; i++) {
    float fi = float(i) / 28.0;
    float y = 0.08 + fi * 0.86 + 0.07 * snoise(vec3(p.x * 1.1, fi * 4.0, t * 0.09)) + 0.025 * sin(p.x * 5.0 + t * 0.6 + fi * 9.0);
    float d = abs(uv.y - y);
    col += pal(fi + t * 0.02) * (smoothstep(w, 0.0, d) * 0.9 + exp(-d * 260.0) * 0.35);
  }
  return col;
}`,
}

export function fragmentSource(effect: ShaderEffect) {
  return HEADER + EFFECTS[effect] + FOOTER
}

/** "#aabbcc" or "r g b" (a --c-* custom property) -> [0..1]x3 */
export function parseColor(value: string): [number, number, number] {
  const v = value.trim()
  if (v.startsWith('#')) {
    const n = parseInt(v.slice(1), 16)
    return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255]
  }
  const parts = v.replace(/rgb\(|\)/g, '').split(/[\s,]+/).map(Number)
  return parts.length >= 3 && parts.every((x) => !Number.isNaN(x)) ? [parts[0] / 255, parts[1] / 255, parts[2] / 255] : [0.5, 0.5, 0.5]
}

export interface ShaderRenderer {
  setEffect: (effect: ShaderEffect) => boolean
  render: (time: number, opts: { colors: [number, number, number][]; dark: boolean; mouse?: [number, number] }) => void
  resize: (width: number, height: number) => void
  destroy: () => void
}

/** A renderer on one canvas; returns null when WebGL isn't available. */
export function createShaderRenderer(canvas: HTMLCanvasElement): ShaderRenderer | null {
  const gl = canvas.getContext('webgl', { antialias: false, alpha: false, preserveDrawingBuffer: true, powerPreference: 'low-power' })
  if (!gl) return null

  const buffer = gl.createBuffer()
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer)
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW)

  const programs = new Map<ShaderEffect, { program: WebGLProgram; loc: Record<string, WebGLUniformLocation | null>; aPos: number }>()
  let current: ReturnType<typeof programs.get> | undefined

  function compile(type: number, source: string) {
    const shader = gl!.createShader(type)!
    gl!.shaderSource(shader, source)
    gl!.compileShader(shader)
    if (!gl!.getShaderParameter(shader, gl!.COMPILE_STATUS)) {
      console.warn('[bg shader]', gl!.getShaderInfoLog(shader))
      gl!.deleteShader(shader)
      return null
    }
    return shader
  }

  function build(effect: ShaderEffect) {
    const vs = compile(gl!.VERTEX_SHADER, VERTEX)
    const fs = compile(gl!.FRAGMENT_SHADER, fragmentSource(effect))
    if (!vs || !fs) return undefined
    const program = gl!.createProgram()!
    gl!.attachShader(program, vs)
    gl!.attachShader(program, fs)
    gl!.linkProgram(program)
    if (!gl!.getProgramParameter(program, gl!.LINK_STATUS)) return undefined
    const loc: Record<string, WebGLUniformLocation | null> = {}
    for (const name of ['uTime', 'uRes', 'uMouse', 'uC1', 'uC2', 'uC3', 'uDark']) loc[name] = gl!.getUniformLocation(program, name)
    return { program, loc, aPos: gl!.getAttribLocation(program, 'aPos') }
  }

  return {
    setEffect(effect) {
      if (!programs.has(effect)) {
        const built = build(effect)
        if (!built) return false
        programs.set(effect, built)
      }
      current = programs.get(effect)
      return true
    },
    resize(width, height) {
      canvas.width = Math.max(1, Math.round(width))
      canvas.height = Math.max(1, Math.round(height))
      gl.viewport(0, 0, canvas.width, canvas.height)
    },
    render(time, { colors, dark, mouse = [0.5, 0.5] }) {
      if (!current) return
      gl.useProgram(current.program)
      gl.bindBuffer(gl.ARRAY_BUFFER, buffer)
      gl.enableVertexAttribArray(current.aPos)
      gl.vertexAttribPointer(current.aPos, 2, gl.FLOAT, false, 0, 0)
      const { loc } = current
      gl.uniform1f(loc.uTime, time)
      gl.uniform2f(loc.uRes, canvas.width, canvas.height)
      gl.uniform2f(loc.uMouse, mouse[0], mouse[1])
      gl.uniform3fv(loc.uC1, colors[0])
      gl.uniform3fv(loc.uC2, colors[1])
      gl.uniform3fv(loc.uC3, colors[2])
      gl.uniform1f(loc.uDark, dark ? 1 : 0)
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4)
    },
    destroy() {
      for (const { program } of programs.values()) gl.deleteProgram(program)
      gl.deleteBuffer(buffer)
      gl.getExtension('WEBGL_lose_context')?.loseContext()
    },
  }
}

// One shared hidden renderer for still thumbnails (site-settings tiles), so
// previews don't each open their own WebGL context.
let snapshotCanvas: HTMLCanvasElement | null = null
let snapshotRenderer: ShaderRenderer | null = null
const snapshotCache = new Map<string, string>()

export function shaderSnapshot(effect: ShaderEffect, colors: [number, number, number][], dark: boolean): string | null {
  if (typeof document === 'undefined') return null
  const key = `${effect}|${colors.flat().join(',')}|${dark}`
  const cached = snapshotCache.get(key)
  if (cached) return cached
  if (!snapshotCanvas) {
    snapshotCanvas = document.createElement('canvas')
    snapshotRenderer = createShaderRenderer(snapshotCanvas)
    snapshotRenderer?.resize(320, 200)
  }
  if (!snapshotRenderer || !snapshotRenderer.setEffect(effect)) return null
  snapshotRenderer.render(12, { colors, dark })
  const url = snapshotCanvas.toDataURL('image/jpeg', 0.85)
  snapshotCache.set(key, url)
  return url
}
