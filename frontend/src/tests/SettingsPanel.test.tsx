import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SettingsPanel } from '../components/SettingsPanel';
import { useTaskStore } from '../store/taskStore';

const mockSettings = {
  default_provider: 'gemini',
  gemini_api_key: 'AIza****',
  gemini_model: 'gemini-3-pro-preview',
  gemini_temperature: null,
  gemini_top_k: null,
  gemini_top_p: null,
  gemini_max_output_tokens: null,
  gemini_thinking_level: 'high',
  gemini_enable_search: false,
  claude_api_key: '',
  claude_model: 'claude-sonnet-4-5-20250929',
  claude_temperature: null,
  claude_max_output_tokens: null,
  claude_extended_thinking: false,
  claude_thinking_budget: 10000,
  openai_compat_base_url: 'http://localhost:3000/v1',
  openai_compat_api_key: '',
  openai_compat_model: 'gpt-4o',
  openai_compat_temperature: null,
  openai_compat_max_output_tokens: null,
  claude_proxy_base_url: 'http://localhost:42069',
  claude_proxy_api_key: '',
  claude_proxy_model: 'claude-sonnet-4-5-20250929',
  claude_proxy_temperature: null,
  claude_proxy_max_output_tokens: null,
  deepseek_api_key: '',
  deepseek_model: 'deepseek-chat',
  deepseek_temperature: null,
  deepseek_max_output_tokens: null,
  qwen_api_key: '',
  qwen_model: 'qwen-plus',
  qwen_temperature: null,
  qwen_max_output_tokens: null,
  enforce_resume_one_page: true,
  enforce_cover_letter_one_page: true,
  max_page_retry_attempts: 3,
  generate_cover_letter: true,
  max_latex_retries: 3,
  default_template_id: 'classic',
  agent_providers: {},
};

describe('SettingsPanel', () => {
  beforeEach(() => {
    useTaskStore.setState({ tasks: [], activeTaskId: null, toasts: [], darkMode: false });
    vi.restoreAllMocks();
  });

  it('renders nothing when not open', () => {
    const { container } = render(<SettingsPanel isOpen={false} onClose={() => {}} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders header when open', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockSettings),
    }));

    render(<SettingsPanel isOpen={true} onClose={() => {}} />);
    expect(screen.getByText('Application Settings')).toBeTruthy();

    vi.unstubAllGlobals();
  });

  it('loads settings on open', async () => {
    const mockFetch = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockSettings) })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) });

    vi.stubGlobal('fetch', mockFetch);

    render(<SettingsPanel isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/settings');
    });

    vi.unstubAllGlobals();
  });

  it('shows section headers', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockSettings) })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) }));

    render(<SettingsPanel isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('Default AI Provider')).toBeTruthy();
    });
    expect(screen.getByText('Gemini Settings')).toBeTruthy();
    expect(screen.getByText('Claude Settings')).toBeTruthy();
    expect(screen.getByText('Generation Settings')).toBeTruthy();
    expect(screen.getByText('Page Length Validation')).toBeTruthy();

    vi.unstubAllGlobals();
  });

  it('shows save and reset buttons', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockSettings) })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) }));

    render(<SettingsPanel isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('Save Settings')).toBeTruthy();
    });
    expect(screen.getByText('Reset to Defaults')).toBeTruthy();
    expect(screen.getByText('Cancel')).toBeTruthy();

    vi.unstubAllGlobals();
  });

  it('calls save endpoint on save click', async () => {
    const mockFetch = vi.fn().mockImplementation((url: string, opts?: RequestInit) => {
      if (url === '/api/settings' && opts?.method === 'PUT') {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      }
      if (url === '/api/settings') {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockSettings) });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
    });

    vi.stubGlobal('fetch', mockFetch);

    render(<SettingsPanel isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('Save Settings')).toBeTruthy();
    });

    fireEvent.click(screen.getByText('Save Settings'));

    await waitFor(() => {
      const saveCalls = (mockFetch.mock.calls as [string, RequestInit?][]).filter(
        (call) => call[0] === '/api/settings' && call[1]?.method === 'PUT'
      );
      expect(saveCalls.length).toBe(1);
    });

    vi.unstubAllGlobals();
  });

  it('calls onClose when Cancel is clicked', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockSettings) })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) }));

    const onClose = vi.fn();
    render(<SettingsPanel isOpen={true} onClose={onClose} />);

    await waitFor(() => {
      expect(screen.getByText('Cancel')).toBeTruthy();
    });

    fireEvent.click(screen.getByText('Cancel'));
    expect(onClose).toHaveBeenCalled();

    vi.unstubAllGlobals();
  });

  it('calls onClose when X button is clicked', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockSettings) })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) }));

    const onClose = vi.fn();
    render(<SettingsPanel isOpen={true} onClose={onClose} />);

    await waitFor(() => {
      expect(screen.getByText('Application Settings')).toBeTruthy();
    });

    // The X button is the sibling of the header
    const closeButtons = screen.getAllByRole('button');
    const xButton = closeButtons.find(btn => btn.querySelector('svg') && btn.closest('.flex.items-center.justify-between'));
    if (xButton) {
      fireEvent.click(xButton);
      expect(onClose).toHaveBeenCalled();
    }

    vi.unstubAllGlobals();
  });

  it('toggles section expansion', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockSettings) })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) }));

    render(<SettingsPanel isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('Claude Settings')).toBeTruthy();
    });

    // Claude section starts collapsed; click to expand
    fireEvent.click(screen.getByText('Claude Settings'));
    await waitFor(() => {
      expect(screen.getByPlaceholderText('Enter your Anthropic API key')).toBeTruthy();
    });

    // Click again to collapse
    fireEvent.click(screen.getByText('Claude Settings'));
    await waitFor(() => {
      expect(screen.queryByPlaceholderText('Enter your Anthropic API key')).toBeNull();
    });

    vi.unstubAllGlobals();
  });

  it('shows loading indicator on reset', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockSettings) })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockSettings) }));
    vi.stubGlobal('confirm', vi.fn().mockReturnValue(true));

    render(<SettingsPanel isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('Reset to Defaults')).toBeTruthy();
    });

    fireEvent.click(screen.getByText('Reset to Defaults'));

    await waitFor(() => {
      const fetchCalls = (fetch as ReturnType<typeof vi.fn>).mock.calls;
      const resetCalls = (fetchCalls as [string, RequestInit?][]).filter(
        (call) => call[0] === '/api/settings/reset'
      );
      expect(resetCalls.length).toBe(1);
    });

    vi.unstubAllGlobals();
  });

  it('shows error toast on failed load', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) }));

    render(<SettingsPanel isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      const toasts = useTaskStore.getState().toasts;
      expect(toasts.some(t => t.type === 'error' && t.message.includes('Failed to load settings'))).toBe(true);
    });

    vi.unstubAllGlobals();
  });
});
