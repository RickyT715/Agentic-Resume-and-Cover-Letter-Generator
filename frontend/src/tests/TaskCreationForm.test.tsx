import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TaskCreationForm } from '../components/task/TaskCreationForm';
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

describe('TaskCreationForm', () => {
  const defaultProps = {
    activeTask: makeTask(),
    jobDescription: 'Looking for a Python developer',
    onJobDescriptionChange: vi.fn(),
    onStartTask: vi.fn(),
    isStarting: false,
    error: null,
  };

  beforeEach(() => {
    useTaskStore.setState({ tasks: [], activeTaskId: null, toasts: [], darkMode: false });
    vi.restoreAllMocks();
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([]),
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders job description textarea', () => {
    renderWithQuery(<TaskCreationForm {...defaultProps} />);
    const textarea = screen.getByPlaceholderText('Paste the job description here...');
    expect(textarea).toBeTruthy();
    expect((textarea as HTMLTextAreaElement).value).toBe('Looking for a Python developer');
  });

  it('renders Start Task button for pending task', () => {
    renderWithQuery(<TaskCreationForm {...defaultProps} />);
    expect(screen.getByText('Start Task')).toBeTruthy();
  });

  it('calls onStartTask when Start Task button is clicked', () => {
    const onStartTask = vi.fn();
    renderWithQuery(<TaskCreationForm {...defaultProps} onStartTask={onStartTask} />);
    fireEvent.click(screen.getByText('Start Task'));
    expect(onStartTask).toHaveBeenCalled();
  });

  it('disables textarea for non-pending task', () => {
    renderWithQuery(
      <TaskCreationForm {...defaultProps} activeTask={makeTask({ status: 'running' })} />,
    );
    const textarea = screen.getByPlaceholderText('Paste the job description here...');
    expect((textarea as HTMLTextAreaElement).disabled).toBe(true);
  });

  it('does not show Start Task button for non-pending task', () => {
    renderWithQuery(
      <TaskCreationForm {...defaultProps} activeTask={makeTask({ status: 'running' })} />,
    );
    expect(screen.queryByText('Start Task')).toBeNull();
  });

  it('shows error message when error prop is set', () => {
    renderWithQuery(<TaskCreationForm {...defaultProps} error="Please enter a job description" />);
    expect(screen.getByText('Please enter a job description')).toBeTruthy();
  });

  it('shows Starting... text when isStarting is true', () => {
    renderWithQuery(<TaskCreationForm {...defaultProps} isStarting={true} />);
    expect(screen.getByText('Starting...')).toBeTruthy();
  });

  it('calls onJobDescriptionChange when textarea value changes', () => {
    const onChange = vi.fn();
    renderWithQuery(<TaskCreationForm {...defaultProps} onJobDescriptionChange={onChange} />);
    const textarea = screen.getByPlaceholderText('Paste the job description here...');
    fireEvent.change(textarea, { target: { value: 'New JD' } });
    expect(onChange).toHaveBeenCalledWith('New JD');
  });

  it('shows language toggle buttons', () => {
    renderWithQuery(<TaskCreationForm {...defaultProps} />);
    expect(screen.getByText('EN')).toBeTruthy();
  });

  it('shows experience level buttons', () => {
    renderWithQuery(<TaskCreationForm {...defaultProps} />);
    expect(screen.getByText('Auto')).toBeTruthy();
    expect(screen.getByText('New Grad')).toBeTruthy();
    expect(screen.getByText('Experienced')).toBeTruthy();
  });

  it('shows cover letter toggle', () => {
    renderWithQuery(<TaskCreationForm {...defaultProps} />);
    expect(screen.getByText('Generate Cover Letter')).toBeTruthy();
  });

  it('shows pipeline version toggle', () => {
    renderWithQuery(<TaskCreationForm {...defaultProps} />);
    expect(screen.getByText('v3 Multi-Agent')).toBeTruthy();
    expect(screen.getByText('v2 Classic')).toBeTruthy();
  });

  it('shows AI provider selector', () => {
    renderWithQuery(<TaskCreationForm {...defaultProps} />);
    expect(screen.getByText('Default (from Settings)')).toBeTruthy();
  });

  it('shows company URL input', () => {
    renderWithQuery(<TaskCreationForm {...defaultProps} />);
    expect(screen.getByPlaceholderText('https://company.com (optional)')).toBeTruthy();
  });

  it('shows History button for pending task', () => {
    renderWithQuery(<TaskCreationForm {...defaultProps} />);
    expect(screen.getByText('History')).toBeTruthy();
  });

  it('disables start button when job description is empty', () => {
    renderWithQuery(<TaskCreationForm {...defaultProps} jobDescription="" />);
    const startButton = screen.getByText('Start Task').closest('button');
    expect(startButton?.disabled).toBe(true);
  });
});
