import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TaskResults } from '../components/task/TaskResults';
import type { Task } from '../types/task';

function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 'test-1',
    task_number: 1,
    job_description: 'Test JD',
    status: 'pending',
    generate_cover_letter: true,
    template_id: 'classic',
    steps: [],
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('TaskResults', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({}),
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders nothing visible for pending tasks', () => {
    const { container } = renderWithQuery(<TaskResults activeTask={makeTask()} />);
    // Pending tasks shouldn't show progress, errors, or downloads
    expect(screen.queryByText('Files Ready for Download')).toBeNull();
    expect(screen.queryByText('Task Failed')).toBeNull();
    expect(container.querySelector('iframe')).toBeNull();
  });

  it('shows error message for failed tasks', () => {
    renderWithQuery(
      <TaskResults
        activeTask={makeTask({
          status: 'failed',
          error_message: 'LaTeX compilation failed',
        })}
      />,
    );
    expect(screen.getByText('Task Failed')).toBeTruthy();
    expect(screen.getByText('LaTeX compilation failed')).toBeTruthy();
  });

  it('shows cancelled message for cancelled tasks', () => {
    renderWithQuery(
      <TaskResults
        activeTask={makeTask({
          status: 'cancelled',
          error_message: 'Cancelled by user',
        })}
      />,
    );
    expect(screen.getByText('Task Cancelled')).toBeTruthy();
    expect(screen.getByText('Cancelled by user')).toBeTruthy();
  });

  it('shows download buttons for completed task with resume', () => {
    renderWithQuery(
      <TaskResults
        activeTask={makeTask({
          status: 'completed',
          resume_pdf_path: '/output/resume.pdf',
          latex_source: '\\documentclass{article}...',
        })}
      />,
    );
    expect(screen.getByText('Resume (PDF)')).toBeTruthy();
    expect(screen.getByText('LaTeX Source (.tex)')).toBeTruthy();
  });

  it('shows cover letter download for completed task with cover letter', () => {
    renderWithQuery(
      <TaskResults
        activeTask={makeTask({
          status: 'completed',
          resume_pdf_path: '/output/resume.pdf',
          cover_letter_pdf_path: '/output/cover.pdf',
          generate_cover_letter: true,
        })}
      />,
    );
    expect(screen.getByText('Cover Letter (PDF)')).toBeTruthy();
  });

  it('does not show cover letter download when no cover letter path', () => {
    renderWithQuery(
      <TaskResults
        activeTask={makeTask({
          status: 'completed',
          resume_pdf_path: '/output/resume.pdf',
          generate_cover_letter: true,
        })}
      />,
    );
    expect(screen.queryByText('Cover Letter (PDF)')).toBeNull();
  });

  it('shows partial result notice for failed task with resume', () => {
    renderWithQuery(
      <TaskResults
        activeTask={makeTask({
          status: 'failed',
          resume_pdf_path: '/output/resume.pdf',
          error_message: 'Cover letter generation failed',
        })}
      />,
    );
    expect(screen.getByText(/Resume was generated before the failure/)).toBeTruthy();
  });

  it('shows PDF preview iframe for completed task with resume', () => {
    const { container } = renderWithQuery(
      <TaskResults
        activeTask={makeTask({
          status: 'completed',
          resume_pdf_path: '/output/resume.pdf',
        })}
      />,
    );
    const iframe = container.querySelector('iframe');
    expect(iframe).toBeTruthy();
    expect(iframe?.getAttribute('title')).toBe('PDF Preview');
  });

  it('shows preview tab buttons when cover letter exists', () => {
    renderWithQuery(
      <TaskResults
        activeTask={makeTask({
          status: 'completed',
          resume_pdf_path: '/output/resume.pdf',
          cover_letter_pdf_path: '/output/cover.pdf',
          generate_cover_letter: true,
        })}
      />,
    );
    expect(screen.getByText('Resume')).toBeTruthy();
    expect(screen.getByText('Cover Letter')).toBeTruthy();
    expect(screen.getByText('Cover Letter (Text)')).toBeTruthy();
  });

  it('shows validation warnings when present', () => {
    renderWithQuery(
      <TaskResults
        activeTask={makeTask({
          status: 'completed',
          resume_pdf_path: '/output/resume.pdf',
          validation_warnings: ['LinkedIn URL was corrected', 'Phone number format fixed'],
        })}
      />,
    );
    expect(screen.getByText('Validation Warnings')).toBeTruthy();
    expect(screen.getByText('LinkedIn URL was corrected')).toBeTruthy();
    expect(screen.getByText('Phone number format fixed')).toBeTruthy();
  });

  it('does not show validation warnings when array is empty', () => {
    renderWithQuery(
      <TaskResults
        activeTask={makeTask({
          status: 'completed',
          resume_pdf_path: '/output/resume.pdf',
          validation_warnings: [],
        })}
      />,
    );
    expect(screen.queryByText('Validation Warnings')).toBeNull();
  });

  it('shows download section for failed task with partial resume', () => {
    renderWithQuery(
      <TaskResults
        activeTask={makeTask({
          status: 'failed',
          resume_pdf_path: '/output/resume.pdf',
          error_message: 'Something went wrong after resume was generated',
        })}
      />,
    );
    expect(screen.getByText('Files Ready for Download')).toBeTruthy();
    expect(screen.getByText('Resume (PDF)')).toBeTruthy();
  });
});
