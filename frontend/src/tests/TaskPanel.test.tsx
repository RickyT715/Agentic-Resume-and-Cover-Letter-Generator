import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TaskPanel } from '../components/TaskPanel';
import { useTaskStore } from '../store/taskStore';
import type { Task } from '../types/task';

function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 'test-1',
    task_number: 1,
    job_description: 'Looking for a Python developer',
    status: 'pending',
    generate_cover_letter: true,
    template_id: 'classic',
    steps: [
      { step: 'generate_resume', status: 'pending', message: '', attempt: 0 },
      { step: 'compile_latex', status: 'pending', message: '', attempt: 0 },
      { step: 'extract_text', status: 'pending', message: '', attempt: 0 },
      { step: 'generate_cover_letter', status: 'pending', message: '', attempt: 0 },
      { step: 'create_cover_pdf', status: 'pending', message: '', attempt: 0 },
    ],
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

describe('TaskPanel', () => {
  beforeEach(() => {
    useTaskStore.setState({ tasks: [], activeTaskId: null, toasts: [], darkMode: false });
    vi.restoreAllMocks();
    // Mock fetch for template loading
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([]),
    }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('shows empty state when no task selected', () => {
    render(<TaskPanel />);
    expect(screen.getByText('No task selected')).toBeTruthy();
    expect(screen.getByText(/Create a new task or select one from the sidebar/)).toBeTruthy();
  });

  it('shows task header with New Task for pending', () => {
    const task = makeTask();
    useTaskStore.setState({ tasks: [task], activeTaskId: 'test-1' });
    render(<TaskPanel />);
    expect(screen.getByText('New Task')).toBeTruthy();
  });

  it('shows company and position in header', () => {
    const task = makeTask({ company_name: 'Google', position_name: 'SWE', status: 'completed' });
    useTaskStore.setState({ tasks: [task], activeTaskId: 'test-1' });
    render(<TaskPanel />);
    expect(screen.getByText('Google - SWE')).toBeTruthy();
  });

  it('shows status text', () => {
    const task = makeTask({ status: 'running' });
    useTaskStore.setState({ tasks: [task], activeTaskId: 'test-1' });
    render(<TaskPanel />);
    expect(screen.getByText('Running')).toBeTruthy();
  });

  it('shows job description textarea', () => {
    const task = makeTask();
    useTaskStore.setState({ tasks: [task], activeTaskId: 'test-1' });
    render(<TaskPanel />);
    const textarea = screen.getByPlaceholderText('Paste the job description here...');
    expect(textarea).toBeTruthy();
    expect((textarea as HTMLTextAreaElement).value).toBe('Looking for a Python developer');
  });

  it('shows Start Task button for pending task', () => {
    const task = makeTask();
    useTaskStore.setState({ tasks: [task], activeTaskId: 'test-1' });
    render(<TaskPanel />);
    expect(screen.getByText('Start Task')).toBeTruthy();
  });

  it('does not show Start Task for running task', () => {
    const task = makeTask({ status: 'running' });
    useTaskStore.setState({ tasks: [task], activeTaskId: 'test-1' });
    render(<TaskPanel />);
    expect(screen.queryByText('Start Task')).toBeNull();
  });

  it('shows Retry Task button for completed tasks', () => {
    const task = makeTask({ status: 'completed' });
    useTaskStore.setState({ tasks: [task], activeTaskId: 'test-1' });
    render(<TaskPanel />);
    expect(screen.getByText('Retry Task')).toBeTruthy();
  });

  it('shows Retry Task button for failed tasks', () => {
    const task = makeTask({ status: 'failed', error_message: 'Something went wrong' });
    useTaskStore.setState({ tasks: [task], activeTaskId: 'test-1' });
    render(<TaskPanel />);
    expect(screen.getByText('Retry Task')).toBeTruthy();
  });

  it('shows error message for failed task', () => {
    const task = makeTask({ status: 'failed', error_message: 'LaTeX compilation failed' });
    useTaskStore.setState({ tasks: [task], activeTaskId: 'test-1' });
    render(<TaskPanel />);
    expect(screen.getByText('Task Failed')).toBeTruthy();
    expect(screen.getByText('LaTeX compilation failed')).toBeTruthy();
  });

  it('shows cancelled message', () => {
    const task = makeTask({ status: 'cancelled', error_message: 'Cancelled by user' });
    useTaskStore.setState({ tasks: [task], activeTaskId: 'test-1' });
    render(<TaskPanel />);
    expect(screen.getByText('Task Cancelled')).toBeTruthy();
    expect(screen.getByText('Cancelled by user')).toBeTruthy();
  });

  it('shows download buttons for completed task with resume', () => {
    const task = makeTask({
      status: 'completed',
      resume_pdf_path: '/output/resume.pdf',
      latex_source: '\\documentclass{article}...',
    });
    useTaskStore.setState({ tasks: [task], activeTaskId: 'test-1' });
    render(<TaskPanel />);
    expect(screen.getByText('Resume (PDF)')).toBeTruthy();
    expect(screen.getByText('LaTeX Source (.tex)')).toBeTruthy();
  });

  it('shows cover letter download for completed task with cover letter', () => {
    const task = makeTask({
      status: 'completed',
      resume_pdf_path: '/output/resume.pdf',
      cover_letter_pdf_path: '/output/cover.pdf',
      generate_cover_letter: true,
    });
    useTaskStore.setState({ tasks: [task], activeTaskId: 'test-1' });
    render(<TaskPanel />);
    expect(screen.getByText('Cover Letter (PDF)')).toBeTruthy();
  });

  it('shows partial result notice for failed task with resume', () => {
    const task = makeTask({
      status: 'failed',
      resume_pdf_path: '/output/resume.pdf',
      error_message: 'Cover letter generation failed',
    });
    useTaskStore.setState({ tasks: [task], activeTaskId: 'test-1' });
    render(<TaskPanel />);
    expect(screen.getByText(/Resume was generated before the failure/)).toBeTruthy();
  });

  it('shows pipeline version toggle for pending task', () => {
    const task = makeTask();
    useTaskStore.setState({ tasks: [task], activeTaskId: 'test-1' });
    render(<TaskPanel />);
    expect(screen.getByText('v3 Multi-Agent')).toBeTruthy();
    expect(screen.getByText('v2 Classic')).toBeTruthy();
  });

  it('shows cover letter toggle for pending task', () => {
    const task = makeTask();
    useTaskStore.setState({ tasks: [task], activeTaskId: 'test-1' });
    render(<TaskPanel />);
    expect(screen.getByText('Generate Cover Letter')).toBeTruthy();
  });

  it('disables textarea for non-pending task', () => {
    const task = makeTask({ status: 'running' });
    useTaskStore.setState({ tasks: [task], activeTaskId: 'test-1' });
    render(<TaskPanel />);
    const textarea = screen.getByPlaceholderText('Paste the job description here...');
    expect((textarea as HTMLTextAreaElement).disabled).toBe(true);
  });
});
