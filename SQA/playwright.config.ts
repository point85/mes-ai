import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  use: {
    screenshot: 'on',
    trace: 'on-first-retry',
    viewport: { width: 1280, height: 720 },
  },
  reporter: [['html', { outputFolder: 'qa-report' }]],
});