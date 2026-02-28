import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useTaskStore } from '../store/taskStore';
import type { Task, ProgressUpdate, Toast } from '../types/task';

function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 'test-1',
    task_number: 1,
    job_description: 'Test JD',
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

describe('taskStore', () => {
  beforeEach(() => {
    useTaskStore.setState({
      tasks: [],
      activeTaskId: null,
      toasts: [],
      darkMode: false,
    });
  });

  describe('addTask', () => {
    it('adds a task and sets it active', () => {
      const task = makeTask();
      useTaskStore.getState().addTask(task);
      expect(useTaskStore.getState().tasks).toHaveLength(1);
      expect(useTaskStore.getState().activeTaskId).toBe('test-1');
    });

    it('adds multiple tasks', () => {
      useTaskStore.getState().addTask(makeTask({ id: 't1' }));
      useTaskStore.getState().addTask(makeTask({ id: 't2' }));
      expect(useTaskStore.getState().tasks).toHaveLength(2);
      expect(useTaskStore.getState().activeTaskId).toBe('t2');
    });
  });

  describe('setActiveTask', () => {
    it('sets the active task ID', () => {
      useTaskStore.getState().setActiveTask('abc');
      expect(useTaskStore.getState().activeTaskId).toBe('abc');
    });

    it('can set to null', () => {
      useTaskStore.getState().setActiveTask(null);
      expect(useTaskStore.getState().activeTaskId).toBeNull();
    });
  });

  describe('updateTask', () => {
    it('updates task fields', () => {
      useTaskStore.getState().addTask(makeTask());
      useTaskStore.getState().updateTask('test-1', { status: 'completed' });
      const task = useTaskStore.getState().tasks[0];
      expect(task.status).toBe('completed');
    });

    it('does not modify other tasks', () => {
      useTaskStore.getState().addTask(makeTask({ id: 't1' }));
      useTaskStore.getState().addTask(makeTask({ id: 't2' }));
      useTaskStore.getState().updateTask('t1', { status: 'failed' });
      const t2 = useTaskStore.getState().tasks.find(t => t.id === 't2');
      expect(t2?.status).toBe('pending');
    });
  });

  describe('updateTaskJobDescription', () => {
    it('updates only job_description', () => {
      useTaskStore.getState().addTask(makeTask());
      useTaskStore.getState().updateTaskJobDescription('test-1', 'New JD');
      expect(useTaskStore.getState().tasks[0].job_description).toBe('New JD');
    });
  });

  describe('removeTask', () => {
    it('removes a task', () => {
      useTaskStore.getState().addTask(makeTask());
      useTaskStore.getState().removeTask('test-1');
      expect(useTaskStore.getState().tasks).toHaveLength(0);
    });

    it('selects last task when active is removed', () => {
      useTaskStore.getState().addTask(makeTask({ id: 't1' }));
      useTaskStore.getState().addTask(makeTask({ id: 't2' }));
      useTaskStore.getState().setActiveTask('t2');
      useTaskStore.getState().removeTask('t2');
      expect(useTaskStore.getState().activeTaskId).toBe('t1');
    });

    it('sets null when all tasks removed', () => {
      useTaskStore.getState().addTask(makeTask());
      useTaskStore.getState().removeTask('test-1');
      expect(useTaskStore.getState().activeTaskId).toBeNull();
    });

    it('keeps activeTaskId when non-active removed', () => {
      useTaskStore.getState().addTask(makeTask({ id: 't1' }));
      useTaskStore.getState().addTask(makeTask({ id: 't2' }));
      useTaskStore.getState().setActiveTask('t1');
      useTaskStore.getState().removeTask('t2');
      expect(useTaskStore.getState().activeTaskId).toBe('t1');
    });
  });

  describe('setTasks', () => {
    it('replaces all tasks', () => {
      useTaskStore.getState().addTask(makeTask({ id: 'old' }));
      useTaskStore.getState().setTasks([makeTask({ id: 'new' })]);
      expect(useTaskStore.getState().tasks).toHaveLength(1);
      expect(useTaskStore.getState().tasks[0].id).toBe('new');
    });
  });

  describe('getActiveTask', () => {
    it('returns the active task', () => {
      useTaskStore.getState().addTask(makeTask());
      const active = useTaskStore.getState().getActiveTask();
      expect(active?.id).toBe('test-1');
    });

    it('returns undefined when no active task', () => {
      expect(useTaskStore.getState().getActiveTask()).toBeUndefined();
    });
  });

  describe('updateTaskProgress', () => {
    it('updates step status and message', () => {
      useTaskStore.getState().addTask(makeTask());
      const update: ProgressUpdate = {
        task_id: 'test-1',
        task_number: 1,
        step: 'generate_resume',
        status: 'running',
        message: 'Generating...',
        attempt: 1,
      };
      useTaskStore.getState().updateTaskProgress(update);
      const task = useTaskStore.getState().tasks[0];
      const step = task.steps.find(s => s.step === 'generate_resume');
      expect(step?.status).toBe('running');
      expect(step?.message).toBe('Generating...');
      expect(task.status).toBe('running');
    });

    it('sets task status to failed on failure', () => {
      useTaskStore.getState().addTask(makeTask({ status: 'running' }));
      useTaskStore.getState().updateTaskProgress({
        task_id: 'test-1',
        task_number: 1,
        step: 'compile_latex',
        status: 'failed',
        message: 'Compilation error',
        attempt: 1,
      });
      expect(useTaskStore.getState().tasks[0].status).toBe('failed');
    });

    it('sets task status to cancelled', () => {
      useTaskStore.getState().addTask(makeTask({ status: 'running' }));
      useTaskStore.getState().updateTaskProgress({
        task_id: 'test-1',
        task_number: 1,
        step: 'generate_resume',
        status: 'cancelled',
        message: 'Cancelled',
        attempt: 0,
      });
      expect(useTaskStore.getState().tasks[0].status).toBe('cancelled');
    });

    it('sets completed on last step for cover letter task', () => {
      useTaskStore.getState().addTask(makeTask({ status: 'running' }));
      useTaskStore.getState().updateTaskProgress({
        task_id: 'test-1',
        task_number: 1,
        step: 'create_cover_pdf',
        status: 'completed',
        message: 'Done',
        attempt: 0,
      });
      expect(useTaskStore.getState().tasks[0].status).toBe('completed');
    });

    it('sets completed on compile_latex for resume-only task', () => {
      useTaskStore.getState().addTask(makeTask({
        status: 'running',
        generate_cover_letter: false,
      }));
      useTaskStore.getState().updateTaskProgress({
        task_id: 'test-1',
        task_number: 1,
        step: 'compile_latex',
        status: 'completed',
        message: 'Done',
        attempt: 0,
      });
      expect(useTaskStore.getState().tasks[0].status).toBe('completed');
    });
  });

  describe('toasts', () => {
    it('adds a toast', () => {
      vi.useFakeTimers();
      useTaskStore.getState().addToast('success', 'Test message');
      expect(useTaskStore.getState().toasts).toHaveLength(1);
      expect(useTaskStore.getState().toasts[0].type).toBe('success');
      vi.useRealTimers();
    });

    it('removes a toast by id', () => {
      vi.useFakeTimers();
      useTaskStore.getState().addToast('error', 'Error!');
      const id = useTaskStore.getState().toasts[0].id;
      useTaskStore.getState().removeToast(id);
      expect(useTaskStore.getState().toasts).toHaveLength(0);
      vi.useRealTimers();
    });

    it('auto-removes toast after timeout', () => {
      vi.useFakeTimers();
      useTaskStore.getState().addToast('info', 'Auto remove');
      expect(useTaskStore.getState().toasts).toHaveLength(1);
      vi.advanceTimersByTime(5000);
      expect(useTaskStore.getState().toasts).toHaveLength(0);
      vi.useRealTimers();
    });
  });

  describe('darkMode', () => {
    it('toggles dark mode', () => {
      expect(useTaskStore.getState().darkMode).toBe(false);
      useTaskStore.getState().toggleDarkMode();
      expect(useTaskStore.getState().darkMode).toBe(true);
    });

    it('persists to localStorage', () => {
      useTaskStore.getState().toggleDarkMode();
      expect(localStorage.getItem('darkMode')).toBe('true');
    });

    it('toggles back', () => {
      useTaskStore.getState().toggleDarkMode();
      useTaskStore.getState().toggleDarkMode();
      expect(useTaskStore.getState().darkMode).toBe(false);
      expect(localStorage.getItem('darkMode')).toBe('false');
    });
  });
});
