import { X, CheckCircle, AlertCircle, Info } from 'lucide-react';
import { useTaskStore } from '../store/taskStore';

export function ToastContainer() {
  const { toasts, removeToast } = useTaskStore();

  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-sm"
      role="status"
      aria-live="polite"
      aria-label="Notifications"
    >
      {toasts.map((toast) => {
        const styles = {
          success: 'bg-green-600 text-white',
          error: 'bg-red-600 text-white',
          info: 'bg-blue-600 text-white',
        }[toast.type];

        const Icon = {
          success: CheckCircle,
          error: AlertCircle,
          info: Info,
        }[toast.type];

        return (
          <div
            key={toast.id}
            className={`flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg animate-slide-in ${styles}`}
            role="alert"
          >
            <Icon className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
            <span className="text-sm font-medium flex-1">{toast.message}</span>
            <button
              onClick={() => removeToast(toast.id)}
              className="p-0.5 hover:bg-white/20 rounded"
              aria-label="Dismiss notification"
            >
              <X className="w-3.5 h-3.5" aria-hidden="true" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
