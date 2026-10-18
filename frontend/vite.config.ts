import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', 'SENTINEL_');
  const target = env.SENTINEL_API_TARGET || 'http://127.0.0.1:8000';
  const aiTarget = env.SENTINEL_AI_TARGET || 'http://127.0.0.1:8004';
  return { plugins: [react()], server: { proxy: { '/api/ai': aiTarget, '/ws/ai': { target: aiTarget.replace(/^http/, 'ws'), ws: true }, '/api': target, '/ws': { target: target.replace(/^http/, 'ws'), ws: true } } } };
});
