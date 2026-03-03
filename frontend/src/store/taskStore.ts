import { create } from 'zustand';
import { Task, ProgressUpdate, TaskStatus, Toast } from '../types/task';

let toastId = 0;

interface TaskStore {
  tasks: Task[];
  activeTaskId: string | null;
  toasts: Toast[];
  darkMode: boolean;

  addTask: (task: Task) => void;
  setActiveTask: (taskId: string | null) => void;
  updateTaskProgress: (update: ProgressUpdate) => void;
  updateTask: (taskId: string, updates: Partial<Task>) => void;
  updateTaskJobDescription: (taskId: string, jobDescription: string) => void;
  removeTask: (taskId: string) => void;
  setTasks: (tasks: Task[]) => void;
  getActiveTask: () => Task | undefined;

  addToast: (type: Toast['type'], message: string) => void;
  removeToast: (id: string) => void;

  toggleDarkMode: () => void;
}

export const useTaskStore = create<TaskStore>((set, get) => ({
  tasks: [],
  activeTaskId: null,
  toasts: [],
  darkMode: localStorage.getItem('darkMode') === 'true',

  addTask: (task) =>
    set((state) => ({
      tasks: [...state.tasks, task],
      activeTaskId: task.id,
    })),

  setActiveTask: (taskId) => set({ activeTaskId: taskId }),

  updateTaskProgress: (update) =>
    set((state) => {
      const newTasks = state.tasks.map((task) => {
        if (task.id !== update.task_id) return task;

        let newTaskStatus = task.status;
        if (update.status === 'failed') {
          newTaskStatus = 'failed';
        } else if (update.status === 'cancelled') {
          newTaskStatus = 'cancelled';
        } else if (update.status === 'completed') {
          const isLastStep = task.generate_cover_letter
            ? update.step === 'create_cover_pdf'
            : update.step === 'compile_latex';
          if (isLastStep) {
            newTaskStatus = 'completed';
          }
        } else if (
          update.status === 'running' &&
          (task.status === 'pending' || task.status === 'queued')
        ) {
          newTaskStatus = 'running';
        }

        return {
          ...task,
          status: newTaskStatus,
          steps: task.steps.map((step) => {
            if (step.step !== update.step) return step;
            return {
              ...step,
              status: update.status as TaskStatus,
              message: update.message,
              attempt: update.attempt,
            };
          }),
        };
      });

      return { tasks: newTasks };
    }),

  updateTask: (taskId, updates) =>
    set((state) => ({
      tasks: state.tasks.map((task) => (task.id === taskId ? { ...task, ...updates } : task)),
    })),

  updateTaskJobDescription: (taskId, jobDescription) =>
    set((state) => ({
      tasks: state.tasks.map((task) =>
        task.id === taskId ? { ...task, job_description: jobDescription } : task,
      ),
    })),

  removeTask: (taskId) =>
    set((state) => {
      const newTasks = state.tasks.filter((t) => t.id !== taskId);
      const newActiveId =
        state.activeTaskId === taskId
          ? newTasks.length > 0
            ? newTasks[newTasks.length - 1].id
            : null
          : state.activeTaskId;
      return { tasks: newTasks, activeTaskId: newActiveId };
    }),

  setTasks: (tasks) => set({ tasks }),

  getActiveTask: () => {
    const state = get();
    return state.tasks.find((t) => t.id === state.activeTaskId);
  },

  addToast: (type, message) =>
    set((state) => {
      const id = String(++toastId);
      setTimeout(() => {
        get().removeToast(id);
      }, 4000);
      return { toasts: [...state.toasts, { id, type, message }] };
    }),

  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),

  toggleDarkMode: () =>
    set((state) => {
      const newMode = !state.darkMode;
      localStorage.setItem('darkMode', String(newMode));
      if (newMode) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
      return { darkMode: newMode };
    }),
}));
