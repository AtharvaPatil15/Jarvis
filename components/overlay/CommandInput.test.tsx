// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { useAssistantStore } from '@/store/assistantStore';
import { CommandInput } from './CommandInput';

beforeEach(() => useAssistantStore.setState({ connected: true }));
afterEach(cleanup);

it('sends the text on submit and clears the box when accepted', () => {
  const onSend = vi.fn(() => true);
  render(<CommandInput onSend={onSend} />);
  const box = screen.getByLabelText('Command') as HTMLInputElement;
  fireEvent.change(box, { target: { value: 'what time is it' } });
  fireEvent.submit(box.form as HTMLFormElement);
  expect(onSend).toHaveBeenCalledWith('what time is it');
  expect(box.value).toBe('');
});

it('keeps the text when the send is rejected', () => {
  render(<CommandInput onSend={() => false} />);
  const box = screen.getByLabelText('Command') as HTMLInputElement;
  fireEvent.change(box, { target: { value: '   ' } });
  fireEvent.submit(box.form as HTMLFormElement);
  expect(box.value).toBe('   ');
});

it('is disabled with an explanatory placeholder while disconnected', () => {
  useAssistantStore.setState({ connected: false });
  const onSend = vi.fn(() => true);
  render(<CommandInput onSend={onSend} />);
  const box = screen.getByLabelText('Command') as HTMLInputElement;
  expect(box.disabled).toBe(true);
  expect(box.placeholder).toBe('Connecting to JARVIS...');
});