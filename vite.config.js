import { defineConfig } from 'vite';

// GitHub Pages 배포 시: base를 '/레포지토리명/'으로 변경하세요
// 예: base: '/ai-champion-generator/'
export default defineConfig({
  base: './',
  build: {
    outDir: 'dist',
  },
});
