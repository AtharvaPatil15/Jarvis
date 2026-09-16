import { describe, expect, it, vi } from 'vitest';
import { applyServerEvent, isAssistantStatus, type SocketActions } from './socketEvents';

function makeActions(): SocketActions {
  return {
    setStatus: vi.fn(), setTranscript: vi.fn(), setActiveTool: vi.fn(),
    appendResponseDelta: vi.fn(), endStream: vi.fn(), setPendingPermission: vi.fn(),
  };
}

describe('applyServerEvent', () => {
  it('sets a valid status from state_change', () => {
    const actions = makeActions();
    expect(applyServerEvent({ type: 'state_change', payload: 'thinking' }, actions)).toBe(true);
    expect(actions.setStatus).toHaveBeenCalledWith('thinking');
  });

  it('rejects an unknown status', () => {
    const actions = makeActions();
    expect(applyServerEvent({ type: 'state_change', payload: 'dancing' }, actions)).toBe(false);
    expect(actions.setStatus).not.toHaveBeenCalled();
  });

  it('switches to listening on wake word', () => {
    const actions = makeActions();
    applyServerEvent({ type: 'wake_word_detected', payload: null }, actions);
    expect(actions.setStatus).toHaveBeenCalledWith('listening');
  });

  it('quotes the user transcript and shows the ai response', () => {
    const actions = makeActions();
    applyServerEvent({ type: 'user_transcript', payload: 'hello' }, actions);
    applyServerEvent({ type: 'ai_response', payload: 'Hi there.' }, actions);
    expect(actions.setTranscript).toHaveBeenNthCalledWith(1, '"hello"');
    expect(actions.setTranscript).toHaveBeenNthCalledWith(2, 'Hi there.');
  });

  it('tracks the active tool from tool_start and clears it on tool_end', () => {
    const actions = makeActions();
    applyServerEvent({ type: 'tool_start', payload: { id: '1', name: 'get_time', arguments: {} } }, actions);
    applyServerEvent({ type: 'tool_end', payload: { id: '1', name: 'get_time', ok: true, summary: '' } }, actions);
    expect(actions.setActiveTool).toHaveBeenNthCalledWith(1, 'get_time');
    expect(actions.setActiveTool).toHaveBeenNthCalledWith(2, null);
  });

  it('shows server errors in the transcript', () => {
    const actions = makeActions();
    applyServerEvent({ type: 'error', payload: { message: 'model offline' } }, actions);
    expect(actions.setTranscript).toHaveBeenCalledWith('Error: model offline');
  });

  it('ignores unknown event types', () => {
    expect(applyServerEvent({ type: 'mystery', payload: 1 }, makeActions())).toBe(false);
  });

  it('streams deltas and finalises on ai_response', () => {
    const actions = makeActions();
    applyServerEvent({ type: 'ai_response_delta', payload: 'Hel' }, actions);
    applyServerEvent({ type: 'ai_response', payload: 'Hello.' }, actions);
    expect(actions.appendResponseDelta).toHaveBeenCalledWith('Hel');
    expect(actions.setTranscript).toHaveBeenCalledWith('Hello.');
    expect(actions.endStream).toHaveBeenCalled();
  });

  it('ends the stream when a new turn starts thinking', () => {
    const actions = makeActions();
    applyServerEvent({ type: 'state_change', payload: 'thinking' }, actions);
    expect(actions.endStream).toHaveBeenCalled();
  });

  it('stores permission requests and clears them when the tool ends or the turn goes idle', () => {
    const actions = makeActions();
    const request = { id: 'p1', tool: 'read_file', summary: 'read the file notes.txt' };
    expect(applyServerEvent({ type: 'permission_request', payload: request }, actions)).toBe(true);
    expect(applyServerEvent({ type: 'permission_request', payload: { id: 1 } }, actions)).toBe(false);
    applyServerEvent({ type: 'tool_end', payload: { id: 't', name: 'read_file', ok: false, summary: '' } }, actions);
    applyServerEvent({ type: 'state_change', payload: 'idle' }, actions);
    expect(actions.setPendingPermission).toHaveBeenNthCalledWith(1, request);
    expect(actions.setPendingPermission).toHaveBeenNthCalledWith(2, null);
    expect(actions.setPendingPermission).toHaveBeenNthCalledWith(3, null);
  });

  it('shows reminders', () => {
    const actions = makeActions();
    applyServerEvent({ type: 'reminder', payload: { id: 3, text: 'drink water' } }, actions);
    expect(actions.setTranscript).toHaveBeenCalledWith('Reminder: drink water');
  });
});

describe('isAssistantStatus', () => {
  it('accepts exactly the five backend states', () => {
    for (const s of ['idle', 'listening', 'thinking', 'responding', 'executing_tool']) {
      expect(isAssistantStatus(s)).toBe(true);
    }
    expect(isAssistantStatus('speaking')).toBe(false);
    expect(isAssistantStatus(3)).toBe(false);
  });
});