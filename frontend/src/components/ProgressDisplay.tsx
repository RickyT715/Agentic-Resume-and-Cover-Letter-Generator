import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, Loader2, Circle, Ban, Clock } from 'lucide-react';
import { Task, StepProgress, TaskStatus } from '../types/task';

const STEP_LABELS: Record<string, string> = {
  generate_resume: 'Generating Resume with AI',
  compile_latex: 'Compiling LaTeX to PDF',
  extract_text: 'Extracting Text from PDF',
  generate_cover_letter: 'Generating Cover Letter with AI',
  create_cover_pdf: 'Creating Cover Letter PDF',
};

const STEP_DESCRIPTIONS: Record<string, string> = {
  generate_resume: 'Using AI to create a tailored LaTeX resume',
  compile_latex: 'Converting LaTeX code to PDF format',
  extract_text: 'Reading resume content for cover letter generation',
  generate_cover_letter: 'Creating a personalized cover letter',
  create_cover_pdf: 'Formatting and saving the cover letter as PDF',
};

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${Math.floor(seconds)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}m ${secs}s`;
}

function useElapsedTime(startedAt?: string, completedAt?: string, isRunning?: boolean) {
  const [elapsed, setElapsed] = useState<number | null>(null);

  useEffect(() => {
    if (!startedAt) {
      setElapsed(null);
      return;
    }
    const start = new Date(startedAt).getTime();
    if (completedAt) {
      setElapsed((new Date(completedAt).getTime() - start) / 1000);
      return;
    }
    if (!isRunning) {
      setElapsed(null);
      return;
    }
    const update = () => setElapsed((Date.now() - start) / 1000);
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [startedAt, completedAt, isRunning]);

  return elapsed;
}

interface ProgressDisplayProps {
  task: Task;
}

export function ProgressDisplay({ task }: ProgressDisplayProps) {
  const steps = task.steps || [];
  const taskStartedAt = steps.find((s) => s.started_at)?.started_at;
  const isTaskRunning = task.status === 'running';
  const lastCompletedStep = [...steps]
    .reverse()
    .find((s) => s.status === 'completed' || s.status === 'failed');
  const totalElapsed = useElapsedTime(
    taskStartedAt,
    task.completed_at || lastCompletedStep?.completed_at,
    isTaskRunning,
  );

  const getStepIcon = (step: StepProgress) => {
    switch (step.status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'running':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'cancelled':
        return <Ban className="w-5 h-5 text-gray-400" />;
      default:
        return <Circle className="w-5 h-5 text-gray-300 dark:text-gray-600" />;
    }
  };

  const getStepStyles = (status: TaskStatus) => {
    switch (status) {
      case 'completed':
        return 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800';
      case 'failed':
        return 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800';
      case 'running':
        return 'bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800';
      case 'cancelled':
        return 'bg-gray-50 border-gray-200 dark:bg-gray-800 dark:border-gray-700';
      default:
        return 'bg-gray-50 border-gray-200 dark:bg-gray-800/50 dark:border-gray-700';
    }
  };

  const completedSteps = steps.filter((s) => s.status === 'completed').length;
  const totalSteps = steps.length;
  const progressPercent = Math.round((completedSteps / totalSteps) * 100);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
      <div className="px-4 py-3 bg-gray-50 dark:bg-gray-750 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <h3 className="font-medium text-gray-800 dark:text-gray-200">Progress</h3>
        <div className="flex items-center gap-3">
          {totalElapsed !== null && (
            <span className="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              {formatElapsed(totalElapsed)}
            </span>
          )}
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {completedSteps} of {totalSteps} steps ({progressPercent}%)
          </span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1 bg-gray-200 dark:bg-gray-700">
        <div
          className="h-full bg-blue-500 transition-all duration-500"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      <div className="p-4 space-y-3">
        {steps.map((step, index) => (
          <StepRow
            key={step.step}
            step={step}
            index={index}
            getStepIcon={getStepIcon}
            getStepStyles={getStepStyles}
          />
        ))}
      </div>
    </div>
  );
}

function StepRow({
  step,
  index,
  getStepIcon,
  getStepStyles,
}: {
  step: StepProgress;
  index: number;
  getStepIcon: (s: StepProgress) => JSX.Element;
  getStepStyles: (status: TaskStatus) => string;
}) {
  const elapsed = useElapsedTime(step.started_at, step.completed_at, step.status === 'running');

  return (
    <div
      className={`flex items-start gap-3 p-3 rounded-lg border transition-colors ${getStepStyles(step.status)}`}
    >
      <div className="flex-shrink-0 mt-0.5">{getStepIcon(step)}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span className="font-medium text-gray-700 dark:text-gray-200">
            Step {index + 1}: {STEP_LABELS[step.step]}
          </span>
          <div className="flex items-center gap-2">
            {elapsed !== null && (
              <span className="text-xs text-gray-400 dark:text-gray-500 tabular-nums">
                {formatElapsed(elapsed)}
              </span>
            )}
            {step.attempt > 0 && step.step === 'compile_latex' && (
              <span
                className={`text-xs px-2 py-0.5 rounded-full ${
                  step.attempt > 1
                    ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                    : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                }`}
              >
                Attempt {step.attempt}/3
                {step.attempt > 1 && ' (with error feedback)'}
              </span>
            )}
          </div>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
          {STEP_DESCRIPTIONS[step.step]}
        </p>
        {step.message && (
          <p
            className={`text-sm mt-1 ${
              step.status === 'failed'
                ? 'text-red-600 dark:text-red-400'
                : step.status === 'running'
                  ? 'text-blue-600 dark:text-blue-400'
                  : 'text-gray-600 dark:text-gray-400'
            }`}
          >
            {step.message}
          </p>
        )}
      </div>
    </div>
  );
}
