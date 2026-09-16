import path from 'node:path';
import { expect, test } from '@playwright/test';

const shots = path.join(__dirname, '..', 'docs', 'proof', 'img');
const note = path.join(__dirname, 'fixtures', 'e2e-note.txt');

async function ready(page: import('@playwright/test').Page) {
  await page.goto('/');
  const box = page.getByLabel('Command');
  await expect(box).toBeEnabled({ timeout: 60_000 });
  return box;
}

test('a typed command is answered by the agent', async ({ page }) => {
  const box = await ready(page);
  await box.fill('hello jarvis');
  await box.press('Enter');
  await expect(page.getByText('You said: hello jarvis')).toBeVisible();
  await page.screenshot({ path: path.join(shots, 'P6-T3-text-command.png') });
});

test('a sensitive tool asks for permission and runs when allowed', async ({ page }) => {
  const box = await ready(page);
  await box.fill(`/tool read_file ${JSON.stringify({ path: note })}`);
  await box.press('Enter');
  const dialog = page.getByRole('alertdialog');
  await expect(dialog).toContainText('read the file');
  await page.screenshot({ path: path.join(shots, 'P6-T3-permission-prompt.png') });
  await dialog.getByRole('button', { name: 'Allow' }).click();
  await expect(dialog).toBeHidden();
  await expect(page.getByText(/You said: \/tool read_file/)).toBeVisible();
  await page.screenshot({ path: path.join(shots, 'P6-T3-permission-allowed.png') });
});

test('denying permission closes the prompt and the assistant still replies', async ({ page }) => {
  const box = await ready(page);
  await box.fill(`/tool read_file ${JSON.stringify({ path: note })}`);
  await box.press('Enter');
  const dialog = page.getByRole('alertdialog');
  await dialog.getByRole('button', { name: 'Deny' }).click();
  await expect(dialog).toBeHidden();
  await expect(page.getByText(/You said: \/tool read_file/)).toBeVisible();
});