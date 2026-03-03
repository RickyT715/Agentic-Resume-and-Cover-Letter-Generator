import { useMemo, useState } from 'react';
import {
  Plus,
  FileText,
  CheckCircle,
  XCircle,
  Loader2,
  Trash2,
  Ban,
  Clock,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { useTaskStore } from '../store/taskStore';
import { Task, TaskStatus } from '../types/task';

const API_URL = '/api';

export function TaskSidebar() {
  const { tasks, activeTaskId, setActiveTask, addTask, removeTask, updateTask, addToast } =
    useTaskStore();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const sortedTasks = useMemo(
    () =>
      [...tasks].sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      ),
    [tasks],
  );

  const getTaskLabel = (task: Task) => {
    if (task.company_name && task.position_name)
      return `${task.company_name} - ${task.position_name}`;
    if (task.company_name) return task.company_name;
    if (task.status === 'pending') return 'New Task';
    return `Task ${task.task_number}`;
  };

  const handleAddTask = async () => {
    try {
      const response = await fetch(`${API_URL}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_description: '' }),
      });
      if (response.ok) {
        const task = await response.json();
        addTask(task);
      }
    } catch (e) {
      console.error('Failed to create task:', e);
    }
  };

  const handleDeleteTask = async (e: React.MouseEvent, taskId: string) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this task? This cannot be undone.')) {
      return;
    }
    try {
      const response = await fetch(`${API_URL}/tasks/${taskId}`, { method: 'DELETE' });
      if (response.ok) {
        removeTask(taskId);
      }
    } catch (e) {
      console.error('Failed to delete task:', e);
    }
  };

  const handleCancelTask = async (e: React.MouseEvent, taskId: string) => {
    e.stopPropagation();
    try {
      const response = await fetch(`${API_URL}/tasks/${taskId}/cancel`, { method: 'POST' });
      if (response.ok) {
        const task = await response.json();
        updateTask(taskId, task);
        addToast('info', `Task ${task.task_number} cancellation requested`);
      }
    } catch (e) {
      console.error('Failed to cancel task:', e);
    }
  };

  const handleClearCompleted = async () => {
    try {
      const response = await fetch(`${API_URL}/tasks`, { method: 'DELETE' });
      if (response.ok) {
        const data = await response.json();
        // Reload tasks from server
        const tasksRes = await fetch(`${API_URL}/tasks`);
        if (tasksRes.ok) {
          const remaining = await tasksRes.json();
          useTaskStore.setState({
            tasks: remaining,
            activeTaskId: remaining.length > 0 ? remaining[remaining.length - 1].id : null,
          });
        }
        if (data.count > 0) {
          addToast('success', `Cleared ${data.count} tasks`);
        }
      }
    } catch (e) {
      console.error('Failed to clear tasks:', e);
    }
  };

  const getStatusIcon = (status: TaskStatus) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" aria-hidden="true" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" aria-hidden="true" />;
      case 'running':
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" aria-hidden="true" />;
      case 'cancelled':
        return <Ban className="w-4 h-4 text-gray-400" aria-hidden="true" />;
      case 'queued':
        return <Clock className="w-4 h-4 text-yellow-500" aria-hidden="true" />;
      default:
        return <FileText className="w-4 h-4 text-gray-400" aria-hidden="true" />;
    }
  };

  const getStatusBadge = (status: TaskStatus) => {
    const colors: Record<string, string> = {
      pending: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
      queued: 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400',
      running: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
      completed: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400',
      failed: 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400',
      cancelled: 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-500',
    };
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full ${colors[status] || colors.pending}`}>
        {status}
      </span>
    );
  };

  const completedCount = tasks.filter(
    (t) => t.status === 'completed' || t.status === 'failed' || t.status === 'cancelled',
  ).length;

  return (
    <>
      {/* Mobile toggle button (visible only when sidebar is closed on small screens) */}
      {!sidebarOpen && (
        <button
          onClick={() => setSidebarOpen(true)}
          className="md:hidden fixed left-0 top-1/2 -translate-y-1/2 z-30 p-1.5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-r-lg shadow-md text-gray-500 dark:text-gray-400"
          aria-label="Open task list sidebar"
        >
          <ChevronRight className="w-4 h-4" aria-hidden="true" />
        </button>
      )}

      <nav
        aria-label="Task list"
        className={`${sidebarOpen ? 'flex' : 'hidden'} md:flex w-72 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex-col`}
      >
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
              Resume Generator
            </h1>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Powered by Gemini 3 Pro</p>
          </div>
          {/* Mobile close button */}
          <button
            onClick={() => setSidebarOpen(false)}
            className="md:hidden p-1 rounded text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
            aria-label="Close task list sidebar"
          >
            <ChevronLeft className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          {tasks.length === 0 ? (
            <div className="text-center text-gray-400 dark:text-gray-500 py-8">
              <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" aria-hidden="true" />
              <p className="text-sm">No tasks yet</p>
              <p className="text-xs">Click "Add Task" or press Ctrl+N</p>
            </div>
          ) : (
            sortedTasks.map((task) => (
              <div
                key={task.id}
                onClick={() => setActiveTask(task.id)}
                role="button"
                tabIndex={0}
                aria-current={activeTaskId === task.id ? 'true' : undefined}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') setActiveTask(task.id);
                }}
                className={`group w-full flex items-center gap-3 px-3 py-3 rounded-lg mb-1 transition-colors text-left cursor-pointer ${
                  activeTaskId === task.id
                    ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800'
                    : 'hover:bg-gray-50 dark:hover:bg-gray-700/50 border border-transparent'
                }`}
              >
                {getStatusIcon(task.status)}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-gray-700 dark:text-gray-200 truncate">
                      {getTaskLabel(task)}
                    </span>
                    {getStatusBadge(task.status)}
                  </div>
                  {task.job_description && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
                      {task.job_description.slice(0, 50)}
                      {task.job_description.length > 50 ? '...' : ''}
                    </p>
                  )}
                </div>

                {/* Action buttons (visible on hover) */}
                <div className="hidden group-hover:flex items-center gap-1">
                  {task.status === 'running' && (
                    <button
                      onClick={(e) => handleCancelTask(e, task.id)}
                      className="p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-red-500"
                      aria-label={`Cancel task ${getTaskLabel(task)}`}
                      title="Cancel task"
                    >
                      <Ban className="w-3.5 h-3.5" aria-hidden="true" />
                    </button>
                  )}
                  {task.status !== 'running' && (
                    <button
                      onClick={(e) => handleDeleteTask(e, task.id)}
                      className="p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-gray-400 hover:text-red-500"
                      aria-label={`Delete task ${getTaskLabel(task)}`}
                      title="Delete task"
                    >
                      <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        <div className="p-3 border-t border-gray-200 dark:border-gray-700 space-y-2">
          {completedCount > 0 && (
            <button
              onClick={handleClearCompleted}
              className="w-full text-xs text-gray-500 dark:text-gray-400 hover:text-red-500 dark:hover:text-red-400 py-1 transition-colors"
            >
              Clear {completedCount} finished tasks
            </button>
          )}
          <button
            onClick={handleAddTask}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            aria-label="Add new task"
          >
            <Plus className="w-4 h-4" aria-hidden="true" />
            Add Task
          </button>
        </div>
      </nav>
    </>
  );
}
