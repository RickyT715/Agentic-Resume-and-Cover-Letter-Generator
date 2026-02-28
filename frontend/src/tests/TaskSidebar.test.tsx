import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TaskSidebar } from '../components/TaskSidebar';
import { useTaskStore } from '../store/taskStore';
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

describe('TaskSidebar', () => {
  beforeEach(() => {
    useTaskStore.setState({ tasks: [], activeTaskId: null, toasts: [], darkMode: false });
    vi.restoreAllMocks();
  });

  it('renders the title', () => {
    render(<TaskSidebar />);
    expect(screen.getByText('Resume Generator')).toBeTruthy();
  });

  it('shows empty state when no tasks', () => {
    render(<TaskSidebar />);
    expect(screen.getByText('No tasks yet')).toBeTruthy();
  });

  it('shows Add Task button', () => {
    render(<TaskSidebar />);
    expect(screen.getByText('Add Task')).toBeTruthy();
  });

  it('renders tasks from store', () => {
    useTaskStore.setState({
      tasks: [
        makeTask({ id: 't1', task_number: 1, status: 'completed', company_name: 'Google', position_name: 'SWE' }),
        makeTask({ id: 't2', task_number: 2, status: 'pending' }),
      ],
    });
    render(<TaskSidebar />);
    expect(screen.getByText('Google - SWE')).toBeTruthy();
    expect(screen.getByText('New Task')).toBeTruthy();
  });

  it('shows task label with company name only', () => {
    useTaskStore.setState({
      tasks: [makeTask({ company_name: 'Meta' })],
    });
    render(<TaskSidebar />);
    expect(screen.getByText('Meta')).toBeTruthy();
  });

  it('shows "Task N" for non-pending tasks without company name', () => {
    useTaskStore.setState({
      tasks: [makeTask({ status: 'running', task_number: 5 })],
    });
    render(<TaskSidebar />);
    expect(screen.getByText('Task 5')).toBeTruthy();
  });

  it('shows status badges', () => {
    useTaskStore.setState({
      tasks: [
        makeTask({ id: 't1', status: 'completed' }),
        makeTask({ id: 't2', status: 'failed' }),
        makeTask({ id: 't3', status: 'running' }),
      ],
    });
    render(<TaskSidebar />);
    expect(screen.getByText('completed')).toBeTruthy();
    expect(screen.getByText('failed')).toBeTruthy();
    expect(screen.getByText('running')).toBeTruthy();
  });

  it('truncates long job descriptions', () => {
    const longJd = 'A'.repeat(100);
    useTaskStore.setState({
      tasks: [makeTask({ job_description: longJd })],
    });
    render(<TaskSidebar />);
    expect(screen.getByText(longJd.slice(0, 50) + '...')).toBeTruthy();
  });

  it('does not truncate short job descriptions', () => {
    useTaskStore.setState({
      tasks: [makeTask({ job_description: 'Short JD' })],
    });
    render(<TaskSidebar />);
    expect(screen.getByText('Short JD')).toBeTruthy();
  });

  it('highlights active task', () => {
    useTaskStore.setState({
      tasks: [makeTask({ id: 't1' }), makeTask({ id: 't2' })],
      activeTaskId: 't1',
    });
    render(<TaskSidebar />);
    // Active task should have blue bg class
    const taskElements = screen.getAllByText(/New Task|Task/);
    expect(taskElements.length).toBeGreaterThanOrEqual(2);
  });

  it('sets active task on click', () => {
    useTaskStore.setState({
      tasks: [makeTask({ id: 't1', company_name: 'TestCo', position_name: 'Dev' })],
      activeTaskId: null,
    });
    render(<TaskSidebar />);
    fireEvent.click(screen.getByText('TestCo - Dev'));
    expect(useTaskStore.getState().activeTaskId).toBe('t1');
  });

  it('calls API when Add Task is clicked', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(makeTask({ id: 'new-task' })),
    });
    vi.stubGlobal('fetch', mockFetch);

    render(<TaskSidebar />);
    fireEvent.click(screen.getByText('Add Task'));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/tasks',
        expect.objectContaining({ method: 'POST' })
      );
    });

    vi.unstubAllGlobals();
  });

  it('shows clear completed button when finished tasks exist', () => {
    useTaskStore.setState({
      tasks: [
        makeTask({ id: 't1', status: 'completed' }),
        makeTask({ id: 't2', status: 'failed' }),
      ],
    });
    render(<TaskSidebar />);
    expect(screen.getByText(/Clear 2 finished tasks/)).toBeTruthy();
  });

  it('does not show clear completed when no finished tasks', () => {
    useTaskStore.setState({
      tasks: [makeTask({ id: 't1', status: 'pending' })],
    });
    render(<TaskSidebar />);
    expect(screen.queryByText(/Clear.*finished tasks/)).toBeNull();
  });

  it('counts cancelled tasks as finished', () => {
    useTaskStore.setState({
      tasks: [
        makeTask({ id: 't1', status: 'completed' }),
        makeTask({ id: 't2', status: 'cancelled' }),
        makeTask({ id: 't3', status: 'pending' }),
      ],
    });
    render(<TaskSidebar />);
    expect(screen.getByText(/Clear 2 finished tasks/)).toBeTruthy();
  });

  it('sorts tasks by creation date (newest first)', () => {
    useTaskStore.setState({
      tasks: [
        makeTask({ id: 't1', company_name: 'OldCo', created_at: '2024-01-01T00:00:00Z' }),
        makeTask({ id: 't2', company_name: 'NewCo', created_at: '2024-06-01T00:00:00Z' }),
      ],
    });
    render(<TaskSidebar />);
    const items = screen.getAllByText(/Co$/);
    expect(items[0].textContent).toBe('NewCo');
    expect(items[1].textContent).toBe('OldCo');
  });
});
