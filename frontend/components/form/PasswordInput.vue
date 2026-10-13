<script setup lang="ts">
// Password field with a show/hide toggle (same look as the admin "set password" dialog).
// Extra attributes (required, minlength, autocomplete, …) go to the <input>.
defineOptions({ inheritAttrs: false })
const model = defineModel<string>({ default: '' })
const visible = ref(false)
</script>

<template>
  <div class="relative mt-1">
    <input
      v-bind="$attrs"
      v-model="model"
      :type="visible ? 'text' : 'password'"
      dir="ltr"
      class="glass block w-full rounded-md py-2 pe-3 ps-10 text-sm text-gray-900 dark:text-white"
    >
    <button
      type="button"
      class="absolute start-2 top-1/2 -translate-y-1/2 rounded p-1 text-gray-500 hover:text-gray-800 dark:hover:text-gray-200"
      :aria-label="visible ? 'پنهان کردن رمز' : 'نمایش رمز'"
      :title="visible ? 'پنهان کردن رمز' : 'نمایش رمز'"
      @click="visible = !visible"
    >
      {{ visible ? '🙈' : '👁' }}
    </button>
  </div>
</template>
