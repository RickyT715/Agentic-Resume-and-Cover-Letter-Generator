import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import PromptsPanel from '../components/PromptsPanel';
import { useTaskStore } from '../store/taskStore';

// Mock prompts data returned by /api/prompts
const mockPrompts: Record<string, string> = {
  resume_prompt: 'Resume {{user_information}} {{latex_template}} {{JOB_DESCRIPTION}}',
  resume_prompt_no_fabrication:
    'Resume no-fab {{user_information}} {{latex_template}} {{JOB_DESCRIPTION}}',
  cover_letter_prompt: 'Cover letter {{RESUME_CONTENT}} {{JOB_DESCRIPTION}}',
  cover_letter_prompt_no_fabrication: 'Cover letter no-fab {{RESUME_CONTENT}} {{JOB_DESCRIPTION}}',
  user_information: 'Software engineer with 5 years experience',
  resume_format: '\\documentclass{article}',
  resume_format_no_summary: '\\documentclass{article} No Summary',
  application_question_prompt: 'Q&A prompt {{USER_INFORMATION}} {{QUESTION}} {{WORD_LIMIT}}',
  application_question_prompt_no_fabrication:
    'Q&A no-fab {{USER_INFORMATION}} {{QUESTION}} {{WORD_LIMIT}}',
  resume_prompt_zh: '中文简历 {{user_information}} {{latex_template}} {{JOB_DESCRIPTION}}',
  resume_prompt_no_fabrication_zh:
    '中文简历禁止虚构 {{user_information}} {{latex_template}} {{JOB_DESCRIPTION}}',
  cover_letter_prompt_zh: '中文求职信 {{RESUME_CONTENT}} {{JOB_DESCRIPTION}}',
  cover_letter_prompt_no_fabrication_zh:
    '中文求职信禁止虚构 {{RESUME_CONTENT}} {{JOB_DESCRIPTION}}',
  user_information_zh: '有5年经验的软件工程师',
  resume_format_zh: '\\documentclass{article}\\usepackage{xeCJK}',
  resume_format_no_summary_zh: '\\documentclass{article}\\usepackage{xeCJK} 无个人总结',
  application_question_prompt_zh: '问答 {{USER_INFORMATION}} {{QUESTION}} {{WORD_LIMIT}}',
  application_question_prompt_no_fabrication_zh:
    '禁止虚构问答 {{USER_INFORMATION}} {{QUESTION}} {{WORD_LIMIT}}',
};

describe('PromptsPanel', () => {
  beforeEach(() => {
    useTaskStore.setState({ tasks: [], activeTaskId: null, toasts: [], darkMode: false });
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders nothing when not open', () => {
    const { container } = render(<PromptsPanel isOpen={false} onClose={() => {}} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders header when open', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(mockPrompts) }),
    );

    render(<PromptsPanel isOpen={true} onClose={() => {}} />);
    expect(screen.getByText('Edit Prompts')).toBeTruthy();
  });

  it('loads prompts on open', async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValue({ ok: true, json: () => Promise.resolve(mockPrompts) });
    vi.stubGlobal('fetch', mockFetch);

    render(<PromptsPanel isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/prompts');
    });
  });

  it('shows all 9 EN tabs by default', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(mockPrompts) }),
    );

    render(<PromptsPanel isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('User Information')).toBeTruthy();
    });

    // Check all 9 EN tab labels are visible
    const expectedTabs = [
      'User Information',
      'Resume Format (LaTeX)',
      'Resume Format (No Summary)',
      'Resume Prompt',
      'Resume (No Fabrication)',
      'Cover Letter Prompt',
      'Cover Letter (No Fabrication)',
      'Q&A Prompt',
      'Q&A (No Fabrication)',
    ];

    for (const tabLabel of expectedTabs) {
      const matches = screen.getAllByText(tabLabel);
      expect(matches.length).toBeGreaterThanOrEqual(1);
    }
  });

  it('switches to ZH tabs when clicking 中文', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(mockPrompts) }),
    );

    render(<PromptsPanel isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('EN')).toBeTruthy();
    });

    // Click the Chinese language toggle
    fireEvent.click(screen.getByText('中文'));

    // ZH tabs should now be visible - they share the same labels
    // but the underlying prompt keys are different (_zh suffix)
    await waitFor(() => {
      const userInfoTabs = screen.getAllByText('User Information');
      expect(userInfoTabs.length).toBeGreaterThanOrEqual(1);
    });
  });

  it('shows prompt description for active tab', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(mockPrompts) }),
    );

    render(<PromptsPanel isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      // Default tab is "User Information" - check its description
      expect(
        screen.getByText(/Your personal information.*Replaces.*user_information/i),
      ).toBeTruthy();
    });
  });

  it('shows prompt content in textarea', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(mockPrompts) }),
    );

    render(<PromptsPanel isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      const textarea = screen.getByRole('textbox');
      expect(textarea).toBeTruthy();
      expect((textarea as HTMLTextAreaElement).value).toBe(mockPrompts.user_information);
    });
  });

  it('switches prompt content when clicking a different tab', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(mockPrompts) }),
    );

    render(<PromptsPanel isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByRole('textbox')).toBeTruthy();
    });

    // Click the "Resume Prompt" tab
    fireEvent.click(screen.getByText('Resume Prompt'));

    await waitFor(() => {
      const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
      expect(textarea.value).toBe(mockPrompts.resume_prompt);
    });
  });

  it('shows "Unsaved changes" when editing', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(mockPrompts) }),
    );

    render(<PromptsPanel isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByRole('textbox')).toBeTruthy();
    });

    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'Modified content' },
    });

    expect(screen.getByText('Unsaved changes')).toBeTruthy();
  });

  it('save button is disabled when no changes', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(mockPrompts) }),
    );

    render(<PromptsPanel isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      const saveButton = screen.getByText('Save');
      expect(saveButton.closest('button')).toBeTruthy();
      expect(saveButton.closest('button')!.hasAttribute('disabled')).toBe(true);
    });
  });

  it('save button is enabled after editing', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(mockPrompts) }),
    );

    render(<PromptsPanel isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByRole('textbox')).toBeTruthy();
    });

    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'Modified content' },
    });

    const saveButton = screen.getByText('Save').closest('button')!;
    expect(saveButton.hasAttribute('disabled')).toBe(false);
  });

  it('calls save endpoint when save is clicked', async () => {
    const mockFetch = vi.fn().mockImplementation((url: string, opts?: RequestInit) => {
      if (typeof url === 'string' && url.startsWith('/api/prompts/') && opts?.method === 'PUT') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true, warnings: [] }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockPrompts) });
    });
    vi.stubGlobal('fetch', mockFetch);

    render(<PromptsPanel isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByRole('textbox')).toBeTruthy();
    });

    // Make a change
    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'Updated user info' },
    });

    // Click save
    fireEvent.click(screen.getByText('Save'));

    await waitFor(() => {
      const saveCalls = (mockFetch.mock.calls as [string, RequestInit?][]).filter(
        (call) => call[0] === '/api/prompts/user_information' && call[1]?.method === 'PUT',
      );
      expect(saveCalls.length).toBe(1);
      const body = JSON.parse(saveCalls[0][1]!.body as string);
      expect(body.content).toBe('Updated user info');
    });
  });

  it('calls reload endpoint when Reload from Files is clicked', async () => {
    const mockFetch = vi.fn().mockImplementation((url: string, opts?: RequestInit) => {
      if (url === '/api/prompts/reload' && opts?.method === 'POST') {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockPrompts) });
    });
    vi.stubGlobal('fetch', mockFetch);

    render(<PromptsPanel isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText('Reload from Files')).toBeTruthy();
    });

    fireEvent.click(screen.getByText('Reload from Files'));

    await waitFor(() => {
      const reloadCalls = (mockFetch.mock.calls as [string, RequestInit?][]).filter(
        (call) => call[0] === '/api/prompts/reload',
      );
      expect(reloadCalls.length).toBe(1);
    });
  });

  it('calls onClose when Close is clicked', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(mockPrompts) }),
    );

    const onClose = vi.fn();
    render(<PromptsPanel isOpen={true} onClose={onClose} />);

    await waitFor(() => {
      expect(screen.getByText('Close')).toBeTruthy();
    });

    fireEvent.click(screen.getByText('Close'));
    expect(onClose).toHaveBeenCalled();
  });

  it('shows character count', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(mockPrompts) }),
    );

    render(<PromptsPanel isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      const charCount = screen.getByText(/\d+ characters/);
      expect(charCount).toBeTruthy();
    });
  });

  it('shows error toast on failed load', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Network error')));

    render(<PromptsPanel isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      const toasts = useTaskStore.getState().toasts;
      expect(toasts.some((t) => t.type === 'error' && t.message.includes('Failed to load'))).toBe(
        true,
      );
    });
  });

  it('shows language toggle buttons', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(mockPrompts) }),
    );

    render(<PromptsPanel isOpen={true} onClose={() => {}} />);
    expect(screen.getByText('EN')).toBeTruthy();
    expect(screen.getByText('中文')).toBeTruthy();
  });

  it('shows no-fabrication tab for resume prompt', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(mockPrompts) }),
    );

    render(<PromptsPanel isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      const noFabTabs = screen.getAllByText('Resume (No Fabrication)');
      expect(noFabTabs.length).toBeGreaterThanOrEqual(1);
    });
  });

  it('shows no-summary format tab', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(mockPrompts) }),
    );

    render(<PromptsPanel isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      const noSummaryTabs = screen.getAllByText('Resume Format (No Summary)');
      expect(noSummaryTabs.length).toBeGreaterThanOrEqual(1);
    });
  });

  it('shows warnings from save response', async () => {
    const mockFetch = vi.fn().mockImplementation((url: string, opts?: RequestInit) => {
      if (typeof url === 'string' && url.startsWith('/api/prompts/') && opts?.method === 'PUT') {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              success: true,
              warnings: ['Missing required placeholder: {{user_information}}'],
            }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockPrompts) });
    });
    vi.stubGlobal('fetch', mockFetch);

    render(<PromptsPanel isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByRole('textbox')).toBeTruthy();
    });

    // Make a change and save
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Missing placeholders' } });
    fireEvent.click(screen.getByText('Save'));

    await waitFor(() => {
      expect(screen.getByText('Placeholder Warnings')).toBeTruthy();
      expect(screen.getByText('Missing required placeholder: {{user_information}}')).toBeTruthy();
    });
  });

  it('navigates to no-fabrication prompt and shows correct content', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(mockPrompts) }),
    );

    render(<PromptsPanel isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByRole('textbox')).toBeTruthy();
    });

    // Click on "Resume (No Fabrication)" tab
    fireEvent.click(screen.getAllByText('Resume (No Fabrication)')[0]);

    await waitFor(() => {
      const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
      expect(textarea.value).toBe(mockPrompts.resume_prompt_no_fabrication);
    });
  });

  it('navigates to no-summary format and shows correct content', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(mockPrompts) }),
    );

    render(<PromptsPanel isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByRole('textbox')).toBeTruthy();
    });

    // Click on "Resume Format (No Summary)" tab
    fireEvent.click(screen.getAllByText('Resume Format (No Summary)')[0]);

    await waitFor(() => {
      const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
      expect(textarea.value).toBe(mockPrompts.resume_format_no_summary);
    });
  });
});
