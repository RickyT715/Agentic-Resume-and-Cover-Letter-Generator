import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TaskStatusBar } from '../components/task/TaskStatusBar';
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

describe('TaskStatusBar', () => {
  beforeEach(() => {
    useTaskStore.setState({ tasks: [], activeTaskId: null, toasts: [], darkMode: false });
    vi.restoreAllMocks();
  });

  it('shows "New Task" for pending tasks without company', () => {
    render(<TaskStatusBar activeTask={makeTask()} onRetry={vi.fn()} />);
    expect(screen.getByText('New Task')).toBeTruthy();
  });

  it('shows company and position in header', () => {
    render(
      <TaskStatusBar
        activeTask={makeTask({ company_name: 'Google', position_name: 'SWE', status: 'completed' })}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByText('Google - SWE')).toBeTruthy();
  });

  it('shows company name only when no position', () => {
    render(
      <TaskStatusBar
        activeTask={makeTask({ company_name: 'Meta', status: 'completed' })}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByText('Meta')).toBeTruthy();
  });

  it('shows status text for running task', () => {
    render(<TaskStatusBar activeTask={makeTask({ status: 'running' })} onRetry={vi.fn()} />);
    expect(screen.getByText('Running')).toBeTruthy();
  });

  it('shows status text for completed task', () => {
    render(<TaskStatusBar activeTask={makeTask({ status: 'completed' })} onRetry={vi.fn()} />);
    expect(screen.getByText('Completed')).toBeTruthy();
  });

  it('shows Cancel Task button for running tasks', () => {
    render(<TaskStatusBar activeTask={makeTask({ status: 'running' })} onRetry={vi.fn()} />);
    expect(screen.getByText('Cancel Task')).toBeTruthy();
  });

  it('does not show Cancel Task button for pending tasks', () => {
    render(<TaskStatusBar activeTask={makeTask({ status: 'pending' })} onRetry={vi.fn()} />);
    expect(screen.queryByText('Cancel Task')).toBeNull();
  });

  it('shows Retry Task button for completed tasks', () => {
    render(<TaskStatusBar activeTask={makeTask({ status: 'completed' })} onRetry={vi.fn()} />);
    expect(screen.getByText('Retry Task')).toBeTruthy();
  });

  it('shows Retry Task button for failed tasks', () => {
    render(<TaskStatusBar activeTask={makeTask({ status: 'failed' })} onRetry={vi.fn()} />);
    expect(screen.getByText('Retry Task')).toBeTruthy();
  });

  it('shows Retry Task button for cancelled tasks', () => {
    render(<TaskStatusBar activeTask={makeTask({ status: 'cancelled' })} onRetry={vi.fn()} />);
    expect(screen.getByText('Retry Task')).toBeTruthy();
  });

  it('does not show Retry Task button for pending tasks', () => {
    render(<TaskStatusBar activeTask={makeTask({ status: 'pending' })} onRetry={vi.fn()} />);
    expect(screen.queryByText('Retry Task')).toBeNull();
  });

  it('does not show Retry Task button for running tasks', () => {
    render(<TaskStatusBar activeTask={makeTask({ status: 'running' })} onRetry={vi.fn()} />);
    expect(screen.queryByText('Retry Task')).toBeNull();
  });

  it('calls onRetry when Retry Task is clicked', () => {
    const onRetry = vi.fn();
    render(<TaskStatusBar activeTask={makeTask({ status: 'completed' })} onRetry={onRetry} />);
    fireEvent.click(screen.getByText('Retry Task'));
    expect(onRetry).toHaveBeenCalled();
  });

  it('shows task number for non-pending tasks without company', () => {
    render(
      <TaskStatusBar
        activeTask={makeTask({ status: 'running', task_number: 5 })}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByText('Task 5')).toBeTruthy();
  });
});
