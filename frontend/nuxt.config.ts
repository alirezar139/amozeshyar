// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: false },

  css: ['~/assets/css/main.css'],

  modules: [
    '@pinia/nuxt',
    '@nuxtjs/tailwindcss',
    '@nuxtjs/sitemap',
    '@nuxtjs/robots',
    '@nuxt/image',
  ],

  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000/api/v1',
    },
  },

  // Rendering strategy per route group (the core of the SEO plan):
  // public marketing/catalog pages are pre-rendered or SSR'd for crawlers
  // and social-share previews; authenticated dashboards are pure SPA since
  // SEO doesn't apply there and skipping SSR keeps them cheap to serve.
  routeRules: {
    // Not statically prerendered: the homepage fetches live featured
    // courses/instructors (short-lived presigned image URLs, and course
    // data that now carries the viewing user's own `is_enrolled`) — a
    // build-time-frozen page would go stale exactly like the two cases
    // below, just less obviously since it still looks "done".
    '/': {},
    // Course pages embed the viewing student's own enrollment/progress
    // (see courses/serializers.py `is_enrolled`, `progress_seconds`) —
    // `swr` is a *shared* cache keyed by URL only, so caching these would
    // leak one user's purchase/progress state into what another visitor's
    // browser renders for the same course. Plain per-request SSR instead.
    '/courses': {},
    '/courses/**': {},
    // Not personalized, but also not cacheable for long: instructor
    // photos are served via short-lived (10 min) presigned MinIO URLs
    // (see backend AWS_QUERYSTRING_EXPIRE), and an SWR-cached page would
    // keep serving an already-expired image URL baked into its HTML long
    // after the underlying signed link stopped working.
    '/instructors/**': {},
    '/dashboard/**': { ssr: false },
    '/instructor-panel/**': { ssr: false },
    '/admin/**': { ssr: false },
  },

  site: {
    url: process.env.NUXT_PUBLIC_SITE_URL || 'http://localhost:3300',
  },

  app: {
    head: {
      htmlAttrs: { lang: 'fa', dir: 'rtl' },
      link: [
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;600;700;800&display=swap',
        },
      ],
      // Applies the saved theme and colors (or the OS preference / default
      // colors) before Vue even hydrates, so there's no flash of the wrong
      // theme/colors on load. Kept as a raw inline script (not a
      // composable) specifically because it must run before anything
      // else. The ramp math here is a plain-JS duplicate of
      // utils/colorRamp.ts's generateRamp() — it has to be inlined since
      // this runs before any module has loaded, but the two must stay in
      // sync (same offsets) or colors would visibly jump once Vue hydrates
      // and re-applies via useTheme().syncFromDom().
      script: [
        {
          innerHTML: `(function(){try{var t=localStorage.getItem('theme');if(!t){t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'}if(t==='dark')document.documentElement.classList.add('dark');var raw=localStorage.getItem('theme-colors');var c=raw?JSON.parse(raw):null;if(c&&c.primary&&c.accent){function h2r(h){h=h.replace('#','');if(h.length===3)h=h[0]+h[0]+h[1]+h[1]+h[2]+h[2];var n=parseInt(h,16)||0;return [(n>>16)&255,(n>>8)&255,n&255]}function r2h(r,g,b){r/=255;g/=255;b/=255;var max=Math.max(r,g,b),min=Math.min(r,g,b),l=(max+min)/2,d=max-min,h=0,s=0;if(d!==0){s=d/(1-Math.abs(2*l-1));if(max===r)h=((g-b)/d)%6;else if(max===g)h=(b-r)/d+2;else h=(r-g)/d+4;h*=60;if(h<0)h+=360}return [h,s*100,l*100]}function h2rgb(h,s,l){s/=100;l/=100;var cc=(1-Math.abs(2*l-1))*s,x=cc*(1-Math.abs((h/60)%2-1)),m=l-cc/2,r=0,g=0,b=0;if(h<60){r=cc;g=x}else if(h<120){r=x;g=cc}else if(h<180){g=cc;b=x}else if(h<240){g=x;b=cc}else if(h<300){r=x;b=cc}else{r=cc;b=x}return [Math.round((r+m)*255),Math.round((g+m)*255),Math.round((b+m)*255)]}function ramp(hex,offs){var rgb=h2r(hex),hsl=r2h(rgb[0],rgb[1],rgb[2]);var out={};for(var k in offs){var l=Math.min(97,Math.max(3,hsl[2]+offs[k]));var rr=h2rgb(hsl[0],hsl[1],l);out[k]=rr[0]+' '+rr[1]+' '+rr[2]}return out}var po={'50':53,'100':45,'200':33,'300':22,'400':11,'500':5,'600':0,'700':-8,'800':-16,'900':-23,'950':-30};var ao={'50':48,'100':41,'200':30,'300':20,'400':9,'500':0,'600':-8,'700':-15,'800':-21,'900':-27};var roles={primary:po,accent:ao,header:po,nav:po};var root=document.documentElement.style;for(var role in roles){var hex=c[role]||c.primary;var rr2=ramp(hex,roles[role]);for(var k in rr2)root.setProperty('--c-'+role+'-'+k,rr2[k])}}}catch(e){}})()`,
        },
      ],
    },
  },
})
