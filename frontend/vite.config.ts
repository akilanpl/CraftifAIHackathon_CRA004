import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', 'SENTINEL_');
  const target = env.SENTINEL_API_TARGET || 'http://127.0.0.1:8000';
  return { plugins: [react()], server: { proxy: { '/api': target, '/ws': { target: target.replace(/^http/, 'ws'), ws: true } } } };
});
