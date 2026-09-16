// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { useAssistantStore } from '@/store/assistantStore';
import { PermissionPrompt } from './PermissionPrompt';

const request = { id: 'p1', tool: 'read_file', summary: 'read the file notes.txt' };

beforeEach(() => useAssistantStore.setState({ pendingPermission: null }));
afterEach(cleanup);

it('renders nothing without a pending request', () => {
  const { container } = render(<PermissionPrompt onRespond={vi.fn()} />);
  expect(container.innerHTML).toBe('');
});

it('shows the request and sends Allow', () => {
  useAssistantStore.setState({ pendingPermission: request });
  const onRespond = vi.fn();
  render(<PermissionPrompt onRespond={onRespond} />);
  expect(screen.getByRole('alertdialog').textContent).toContain('read_file');
  expect(screen.getByRole('alertdialog').textContent).toContain('Allow JARVIS to read the file notes.txt?');
  fireEvent.click(screen.getByRole('button', { name: 'Allow' }));
  expect(onRespond).toHaveBeenCalledWith('p1', true);
  expect(useAssistantStore.getState().pendingPermission).toBeNull();
});

it('sends Deny', () => {
  useAssistantStore.setState({ pendingPermission: request });
  const onRespond = vi.fn();
  render(<PermissionPrompt onRespond={onRespond} />);
  fireEvent.click(screen.getByRole('button', { name: 'Deny' }));
  expect(onRespond).toHaveBeenCalledWith('p1', false);
});