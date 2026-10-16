import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Read the repository's root .env. Only VITE_-prefixed variables reach the browser.
  envDir: '..',
})
