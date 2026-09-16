import path from 'node:path';
import { defineConfig } from '@playwright/test';

const root = __dirname;
const dataDir = path.join(root, 'test-results', 'e2e-data');
const pythonExe = path.join(root, '.venv', 'Scripts', 'python.exe');

export default defineConfig({
  testDir: 'e2e',
  timeout: 90_000,
  retries: 0,
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:3000',
    channel: 'msedge',
    headless: true,
    viewport: { width: 420, height: 700 },
  },
  webServer: [
    {
      command: `"${pythonExe}" -m uvicorn server:create_app --factory --host 127.0.0.1 --port 8000`,
      url: 'http://127.0.0.1:8000/health',
      timeout: 120_000,
      reuseExistingServer: false,
      env: {
        ...process.env,
        JARVIS_LLM_BACKEND: 'fake',
        JARVIS_VOICE_ENABLED: 'false',
        JARVIS_DATA_DIR: dataDir,
        JARVIS_MCP_CONFIG_PATH: path.join(dataDir, 'no-mcp.json'),
        JARVIS_FILE_ROOTS: JSON.stringify([path.join(root, 'e2e', 'fixtures')]),
      } as Record<string, string>,
    },
    {
      command: 'npm run dev -- --hostname 127.0.0.1 --port 3000',
      url: 'http://127.0.0.1:3000',
      timeout: 180_000,
      reuseExistingServer: false,
    },
  ],
});