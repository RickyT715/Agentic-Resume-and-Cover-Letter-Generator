import { RefreshCw, Ban } from 'lucide-react';
import { Task } from '../../types/task';
import { useTaskStore } from '../../store/taskStore';

const API_URL = '/api';

interface TaskStatusBarProps {
  activeTask: Task;
  onRetry: () => void;
}

export function TaskStatusBar({ activeTask, onRetry }: TaskStatusBarProps) {
  const { updateTask, addToast } = useTaskStore();

  const isCompleted = activeTask.status === 'completed';
  const isFailed = activeTask.status === 'failed';
  const isCancelled = activeTask.status === 'cancelled';

  const handleCancel = async () => {
    try {
      const response = await fetch(`${API_URL}/tasks/${activeTask.id}/cancel`, { method: 'POST' });
      if (response.ok) {
        const task = await response.json();
        updateTask(activeTask.id, task);
        addToast('info', `Task ${task.task_number} cancellation requested`);
      }
    } catch (e) {
      console.error('Failed to cancel task:', e);
    }
  };

  return (
    <div className="px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100">
            {activeTask.company_name && activeTask.position_name
              ? `${activeTask.company_name} - ${activeTask.position_name}`
              : activeTask.company_name ||
                (activeTask.status === 'pending' ? 'New Task' : `Task ${activeTask.task_number}`)}
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            Status:{' '}
            <span
              className={`font-medium ${
                isCompleted
                  ? 'text-green-600'
                  : isFailed
                    ? 'text-red-600'
                    : activeTask.status === 'running'
                      ? 'text-blue-600'
                      : isCancelled
                        ? 'text-gray-500'
                        : 'text-gray-600 dark:text-gray-400'
              }`}
            >
              {(activeTask.status || 'pending').charAt(0).toUpperCase() +
                (activeTask.status || 'pending').slice(1)}
            </span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          {activeTask.status === 'running' && (
            <button
              onClick={handleCancel}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-medium"
            >
              <Ban className="w-4 h-4" />
              Cancel Task
            </button>
          )}
          {(isCompleted || isFailed || isCancelled) && (
            <button
              onClick={onRetry}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
            >
              <RefreshCw className="w-4 h-4" />
              Retry Task
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
