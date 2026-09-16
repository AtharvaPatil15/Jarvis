import { beforeEach, expect, it } from 'vitest';
import { useAssistantStore } from './assistantStore';

beforeEach(() => {
  useAssistantStore.setState({ transcript: '', streaming: false, pendingPermission: null, connected: false });
});

it('starts a fresh transcript for the first delta and appends the rest', () => {
  const store = useAssistantStore.getState();
  store.setTranscript('"what time is it"');
  store.appendResponseDelta('It is ');
  store.appendResponseDelta('5 PM.');
  expect(useAssistantStore.getState().transcript).toBe('It is 5 PM.');
  store.endStream();
  store.appendResponseDelta('New answer');
  expect(useAssistantStore.getState().transcript).toBe('New answer');
});

it('tracks connection and pending permission', () => {
  const store = useAssistantStore.getState();
  store.setConnected(true);
  store.setPendingPermission({ id: 'p1', tool: 'read_file', summary: 'read the file notes.txt' });
  expect(useAssistantStore.getState().connected).toBe(true);
  expect(useAssistantStore.getState().pendingPermission?.id).toBe('p1');
});