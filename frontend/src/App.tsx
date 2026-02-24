import { useState, useEffect, useCallback } from 'react';
import { TaskSidebar } from './components/TaskSidebar';
import { TaskPanel } from './components/TaskPanel';
import { SettingsPanel } from './components/SettingsPanel';
import { PromptsPanel } from './components/PromptsPanel';
import { ToastContainer } from './components/ToastContainer';
import { useWebSocket } from './hooks/useWebSocket';
import { useTaskStore } from './store/taskStore';
import { Wifi, WifiOff, Settings, FileText, Moon, Sun } from 'lucide-react';

const API_URL = '/api';

function App() {
  const { isConnected } = useWebSocket();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [promptsOpen, setPromptsOpen] = useState(false);
  const { darkMode, toggleDarkMode, setTasks, addTask } = useTaskStore();

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
        const res = await fetch(`${API_URL}/tasks`);
        const existing = res.ok ? await res.json() : [];
        if (existing.length > 0) {
          setTasks(existing);
        }
        const hasPending = existing.some((t: { status: string }) => t.status === 'pending');
        if (!hasPending) {
          const createRes = await fetch(`${API_URL}/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_description: '' }),
          });
          if (createRes.ok) {
            const newTask = await createRes.json();
            addTask(newTask);
          }
        }
      } catch (_) {}
    })();
  }, [setTasks, addTask]);

  // Global keyboard shortcuts
  const handleKeyDown = useCallback(
    async (e: KeyboardEvent) => {
      // Ctrl+N: New task
      if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
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
        } catch (_) {}
      }

      // Escape: Close modals
      if (e.key === 'Escape') {
        setSettingsOpen(false);
        setPromptsOpen(false);
      }
    },
    [addTask]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return (
    <div className="flex h-screen bg-gray-100 dark:bg-gray-900 transition-colors">
      <TaskSidebar />

      <div className="flex-1 flex flex-col">
        {/* Top bar */}
        <div className="flex items-center justify-between px-4 py-2 bg-white dark:bg-gray-800 border-b dark:border-gray-700 shadow-sm">
          {/* Connection status */}
          <div
            className={`text-xs flex items-center gap-1 px-2 py-1 rounded ${
              isConnected
                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
            }`}
          >
            {isConnected ? (
              <>
                <Wifi className="w-3 h-3" />
                Connected
              </>
            ) : (
              <>
                <WifiOff className="w-3 h-3" />
                Disconnected
              </>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={toggleDarkMode}
              className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 transition-colors"
              title={darkMode ? 'Light Mode' : 'Dark Mode'}
            >
              {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
            <button
              onClick={() => setPromptsOpen(true)}
              className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 hover:bg-blue-100 dark:hover:bg-blue-900/50 border border-blue-200 dark:border-blue-800 rounded-lg transition-colors"
            >
              <FileText className="w-4 h-4" />
              Prompts
            </button>
            <button
              onClick={() => setSettingsOpen(true)}
              className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 border border-gray-300 dark:border-gray-600 rounded-lg transition-colors"
            >
              <Settings className="w-4 h-4" />
              Settings
            </button>
          </div>
        </div>

        <TaskPanel />
      </div>

      <SettingsPanel isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <PromptsPanel isOpen={promptsOpen} onClose={() => setPromptsOpen(false)} />
      <ToastContainer />
    </div>
  );
}

export default App;
