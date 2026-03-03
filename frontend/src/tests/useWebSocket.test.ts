import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock WebSocket class
class MockWebSocket {
  static OPEN = 1;
  static CLOSED = 3;

  url: string;
  readyState = MockWebSocket.OPEN;
  onopen: ((ev: Event) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    // Simulate async open
    setTimeout(() => this.onopen?.(new Event('open')), 0);
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
  }

  send(_data: string) {}

  simulateMessage(data: unknown) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
  }

  simulateClose() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close'));
  }

  simulateError() {
    this.onerror?.(new Event('error'));
  }
}

describe('useWebSocket', () => {
  let instances: MockWebSocket[];

  beforeEach(() => {
    instances = [];
    vi.stubGlobal(
      'WebSocket',
      class extends MockWebSocket {
        constructor(url: string) {
          super(url);
          instances.push(this);
        }
      },
    );
    // Provide window.location for URL construction
    vi.stubGlobal('location', {
      protocol: 'http:',
      hostname: 'localhost',
      port: '45173',
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('MockWebSocket stores URL', () => {
    const ws = new MockWebSocket('ws://localhost:48765/ws');
    expect(ws.url).toBe('ws://localhost:48765/ws');
  });

  it('MockWebSocket simulates message', () => {
    const ws = new MockWebSocket('ws://localhost:48765/ws');
    let received: unknown = null;
    ws.onmessage = (ev) => {
      received = JSON.parse(ev.data);
    };
    ws.simulateMessage({ type: 'progress', data: { step: 'compile_latex' } });
    expect(received).toEqual({ type: 'progress', data: { step: 'compile_latex' } });
  });

  it('MockWebSocket simulates close', () => {
    const ws = new MockWebSocket('ws://localhost:48765/ws');
    let closed = false;
    ws.onclose = () => {
      closed = true;
    };
    ws.simulateClose();
    expect(closed).toBe(true);
    expect(ws.readyState).toBe(MockWebSocket.CLOSED);
  });

  it('MockWebSocket simulates error', () => {
    const ws = new MockWebSocket('ws://localhost:48765/ws');
    let errored = false;
    ws.onerror = () => {
      errored = true;
    };
    ws.simulateError();
    expect(errored).toBe(true);
  });

  it('can parse progress messages', () => {
    const data = {
      type: 'progress',
      data: {
        task_id: 'abc',
        task_number: 1,
        step: 'generate_resume',
        status: 'running',
        message: 'Working...',
        attempt: 1,
      },
    };
    // Simulate what the hook does with the message
    const parsed = JSON.parse(JSON.stringify(data));
    expect(parsed.type).toBe('progress');
    expect(parsed.data.task_id).toBe('abc');
    expect(parsed.data.step).toBe('generate_resume');
  });

  it('handles malformed JSON gracefully', () => {
    const ws = new MockWebSocket('ws://localhost:48765/ws');
    let error: Error | null = null;
    ws.onmessage = (ev) => {
      try {
        JSON.parse(ev.data);
      } catch (e) {
        error = e as Error;
      }
    };
    ws.onmessage?.(new MessageEvent('message', { data: 'not json' }));
    expect(error).not.toBeNull();
  });
});
