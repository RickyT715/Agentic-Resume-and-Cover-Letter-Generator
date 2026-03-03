import React, { useState, useEffect, useCallback, Suspense } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TaskSidebar } from './components/TaskSidebar';
import { TaskPanel } from './components/TaskPanel';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ToastContainer } from './components/ToastContainer';
import { useWebSocket } from './hooks/useWebSocket';
import { useTaskStore } from './store/taskStore';
import { useCreateTaskMutation } from './hooks/useTaskQuery';
import { Wifi, WifiOff, Settings, FileText, Moon, Sun } from 'lucide-react';

const SettingsPanel = React.lazy(() => import('./components/SettingsPanel'));
const PromptsPanel = React.lazy(() => import('./components/PromptsPanel'));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function AppContent() {
  const { isConnected } = useWebSocket();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [promptsOpen, setPromptsOpen] = useState(false);
  const { darkMode, toggleDarkMode, setTasks, addTask } = useTaskStore();
  const createTaskMutation = useCreateTaskMutation();

  // Initialize dark mode class on mount
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    }
  }, []);

  // Load persisted tasks on mount; auto-create a fresh task only if none are pending
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch('/api/tasks');
        const existing = res.ok ? await res.json() : [];
        if (existing.length > 0) {
          setTasks(existing);
        }
        const hasPending = existing.some((t: { status: string }) => t.status === 'pending');
        if (!hasPending) {
          createTaskMutation.mutate(
            { job_description: '' },
            { onSuccess: (task) => addTask(task) },
          );
        }
      } catch {
        // ignore fetch errors on initial load
      }
    })();
  }, [setTasks, addTask]);

  // Global keyboard shortcuts
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Ctrl+N: New task
      if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
        createTaskMutation.mutate({ job_description: '' }, { onSuccess: (task) => addTask(task) });
      }

      // Escape: Close modals
      if (e.key === 'Escape') {
        setSettingsOpen(false);
        setPromptsOpen(false);
      }
    },
    [addTask, createTaskMutation],
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return (
    <div className="flex h-screen bg-gray-100 dark:bg-gray-900 transition-colors">
      <TaskSidebar />

      <main role="main" className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <div className="flex items-center justify-between px-4 py-2 bg-white dark:bg-gray-800 border-b dark:border-gray-700 shadow-sm">
          {/* Connection status */}
          <div
            aria-live="polite"
            aria-label={isConnected ? 'Connected to server' : 'Disconnected from server'}
            className={`text-xs flex items-center gap-1 px-2 py-1 rounded ${
              isConnected
                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
            }`}
          >
            {isConnected ? (
              <>
                <Wifi className="w-3 h-3" aria-hidden="true" />
                Connected
              </>
            ) : (
              <>
                <WifiOff className="w-3 h-3" aria-hidden="true" />
                Disconnected
              </>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={toggleDarkMode}
              className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 transition-colors"
              aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
              title={darkMode ? 'Light Mode' : 'Dark Mode'}
            >
              {darkMode ? (
                <Sun className="w-4 h-4" aria-hidden="true" />
              ) : (
                <Moon className="w-4 h-4" aria-hidden="true" />
              )}
            </button>
            <button
              onClick={() => setPromptsOpen(true)}
              className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 hover:bg-blue-100 dark:hover:bg-blue-900/50 border border-blue-200 dark:border-blue-800 rounded-lg transition-colors"
            >
              <FileText className="w-4 h-4" aria-hidden="true" />
              Prompts
            </button>
            <button
              onClick={() => setSettingsOpen(true)}
              className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 border border-gray-300 dark:border-gray-600 rounded-lg transition-colors"
            >
              <Settings className="w-4 h-4" aria-hidden="true" />
              Settings
            </button>
          </div>
        </div>

        <TaskPanel />
      </main>

      <Suspense fallback={null}>
        <SettingsPanel isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
        <PromptsPanel isOpen={promptsOpen} onClose={() => setPromptsOpen(false)} />
      </Suspense>
      <ToastContainer />
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <AppContent />
      </ErrorBoundary>
    </QueryClientProvider>
  );
}

export default App;
