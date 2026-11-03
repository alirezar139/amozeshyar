// Flat config from @nuxt/eslint-config: Vue + TypeScript rules tuned for Nuxt.
// Standalone (no .nuxt/ needed), so `npm run lint` works right after `npm ci`.
import { createConfigForNuxt } from '@nuxt/eslint-config'

export default createConfigForNuxt({
  features: { typescript: true },
}).append(
  {
    ignores: ['.nuxt/', '.output/', 'node_modules/', 'public/'],
  },
  {
    rules: {
      // API payloads are typed loosely (`request<any>`) throughout, by choice.
      '@typescript-eslint/no-explicit-any': 'off',
      // Formatting, not correctness; the codebase mixes `<x />` and `<x>` for void tags.
      'vue/html-self-closing': 'off',
      'vue/first-attribute-linebreak': 'off',
    },
  },
)
