import { useState, useEffect, useCallback } from 'react';
import { FileText } from 'lucide-react';
import { useTaskStore } from '../store/taskStore';
import { QuestionsSection } from './QuestionsSection';
import { TaskCreationForm, TaskStatusBar, TaskResults, GeneratedAnswers } from './task';

const API_URL = '/api';

export function TaskPanel() {
  const { activeTaskId, tasks, updateTask, updateTaskJobDescription, addToast } = useTaskStore();
  const activeTask = tasks.find((t) => t.id === activeTaskId);
  const [jobDescription, setJobDescription] = useState('');
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (activeTask) {
      setJobDescription(activeTask.job_description);
      setError(null);
    }
  }, [activeTaskId, activeTask]);

  const handleJobDescriptionChange = (value: string) => {
    setJobDescription(value);
    if (activeTask && activeTask.status === 'pending') {
      updateTaskJobDescription(activeTask.id, value);
    }
  };

  const handleStartTask = useCallback(async () => {
    if (!activeTask || !jobDescription.trim()) {
      setError('Please enter a job description');
      return;
    }
    setIsStarting(true);
    setError(null);
    try {
      const updateResponse = await fetch(`${API_URL}/tasks/${activeTask.id}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_description: jobDescription,
          generate_cover_letter: activeTask.generate_cover_letter,
          template_id: activeTask.template_id,
          experience_level: activeTask.experience_level || 'auto',
          provider: activeTask.provider || undefined,
        }),
      });
      if (!updateResponse.ok) {
        const data = await updateResponse.json();
        throw new Error(data.detail || 'Failed to update task');
      }
      updateTask(activeTask.id, {
        job_description: jobDescription,
        status: 'running',
      });
      const startResponse = await fetch(`${API_URL}/tasks/${activeTask.id}/start-v3`, {
        method: 'POST',
      });
      if (!startResponse.ok) {
        const data = await startResponse.json();
        throw new Error(data.detail || 'Failed to start task');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'An error occurred');
      if (activeTask) updateTask(activeTask.id, { status: 'pending' });
    } finally {
      setIsStarting(false);
    }
  }, [activeTask, jobDescription, updateTask]);

  const handleRetry = async () => {
    if (!activeTask) return;
    try {
      const response = await fetch(`${API_URL}/tasks/${activeTask.id}/retry`, { method: 'POST' });
      if (!response.ok) {
        addToast('error', 'Failed to retry task');
        return;
      }
      const taskRes = await fetch(`${API_URL}/tasks/${activeTask.id}`);
      if (taskRes.ok) {
        const task = await taskRes.json();
        updateTask(activeTask.id, task);
        addToast('info', 'Task reset for retry');
      }
    } catch (e) {
      console.error('Failed to retry task:', e);
      addToast('error', 'Failed to retry task');
    }
  };

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && activeTask?.status === 'pending') {
        e.preventDefault();
        handleStartTask();
      }
    },
    [activeTask, handleStartTask],
  );

  if (!activeTask) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center text-gray-500 dark:text-gray-400">
          <FileText className="w-16 h-16 mx-auto mb-4 opacity-30" />
          <p className="text-lg font-medium">No task selected</p>
          <p className="text-sm mt-1">Create a new task or select one from the sidebar</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="flex-1 flex flex-col overflow-hidden bg-gray-50 dark:bg-gray-900"
      onKeyDown={handleKeyDown}
    >
      <TaskStatusBar activeTask={activeTask} onRetry={handleRetry} />

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <TaskCreationForm
          activeTask={activeTask}
          jobDescription={jobDescription}
          onJobDescriptionChange={handleJobDescriptionChange}
          onStartTask={handleStartTask}
          isStarting={isStarting}
          error={error}
        />

        <QuestionsSection
          taskId={activeTask.id}
          questions={activeTask.questions || []}
          jobDescription={jobDescription}
        />

        <GeneratedAnswers questions={activeTask.questions || []} />

        <TaskResults activeTask={activeTask} />
      </div>
    </div>
  );
}
