import { describe, expect, it, vi } from 'vitest';
import { applyServerEvent, isAssistantStatus, type SocketActions } from './socketEvents';

function makeActions(): SocketActions {
  return { setStatus: vi.fn(), setTranscript: vi.fn(), setActiveTool: vi.fn() };
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