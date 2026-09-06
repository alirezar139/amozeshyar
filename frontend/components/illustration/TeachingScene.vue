<template>
  <div class="glass relative overflow-hidden rounded-2xl p-6 shadow-xl">
    <svg viewBox="0 0 400 300" class="h-full w-full" fill="none" xmlns="http://www.w3.org/2000/svg">
      <!-- whiteboard -->
      <rect x="40" y="30" width="230" height="150" rx="10" class="fill-white/70 dark:fill-white/10" />
      <rect x="40" y="30" width="230" height="150" rx="10" class="stroke-gray-300 dark:stroke-white/20" stroke-width="2" />
      <line x1="90" y1="180" x2="80" y2="215" class="stroke-gray-300 dark:stroke-white/20" stroke-width="4" stroke-linecap="round" />
      <line x1="220" y1="180" x2="230" y2="215" class="stroke-gray-300 dark:stroke-white/20" stroke-width="4" stroke-linecap="round" />

      <!-- animated growth chart on the board -->
      <polyline
        points="60,150 100,120 130,135 165,90 200,105 245,55"
        class="animate-write-line text-primary-600 dark:text-primary-400"
        stroke="currentColor"
        stroke-width="4"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
      <circle cx="245" cy="55" r="5" class="fill-accent-500" />

      <!-- a couple of "notes" lines on the board -->
      <line x1="60" y1="160" x2="110" y2="160" class="stroke-gray-300 dark:stroke-white/20" stroke-width="3" stroke-linecap="round" />
      <line x1="60" y1="168" x2="95" y2="168" class="stroke-gray-300 dark:stroke-white/20" stroke-width="3" stroke-linecap="round" />

      <!-- teacher: simple flat figure with a pointer -->
      <g>
        <circle cx="300" cy="90" r="18" class="fill-primary-600" />
        <path d="M275 175 Q300 120 325 175 Z" class="fill-primary-600" />
        <line x1="282" y1="130" x2="255" y2="105" class="stroke-primary-600" stroke-width="6" stroke-linecap="round" />
      </g>

      <!-- student desk with laptop -->
      <g>
        <rect x="60" y="230" width="90" height="10" rx="3" class="fill-gray-300 dark:fill-white/15" />
        <path d="M75 228 L75 205 Q75 200 80 200 L130 200 Q135 200 135 205 L135 228 Z" class="fill-accent-500/90" />
        <rect x="82" y="207" width="46" height="16" rx="2" class="fill-white/80 dark:fill-white/70" />
      </g>

      <!-- floating decorative icons -->
      <g class="animate-float-a text-accent-500">
        <circle cx="330" cy="200" r="14" fill="currentColor" opacity="0.15" />
        <path d="M330 192v16M322 200h16" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" />
      </g>
      <g class="animate-float-b text-primary-600 dark:text-primary-400">
        <rect x="330" y="230" width="20" height="16" rx="2" fill="currentColor" opacity="0.15" />
        <rect x="330" y="230" width="20" height="16" rx="2" stroke="currentColor" stroke-width="2" />
        <line x1="334" y1="235" x2="346" y2="235" stroke="currentColor" stroke-width="1.5" />
        <line x1="334" y1="239" x2="342" y2="239" stroke="currentColor" stroke-width="1.5" />
      </g>
    </svg>
  </div>
</template>
