import { useState } from 'react';
import {
  Download,
  AlertCircle,
  Code,
  Eye,
  Copy,
  Check,
  Zap,
  Loader2,
  BarChart2,
} from 'lucide-react';
import { Task, EvaluationData } from '../../types/task';
import { ProgressDisplay } from '../ProgressDisplay';
import { SkillMatchChart } from '../SkillMatchChart';
import {
  useEvaluationQuery,
  useEvaluateTaskMutation,
  useCoverLetterTextQuery,
} from '../../hooks/useTaskQuery';

const API_URL = '/api';

interface TaskResultsProps {
  activeTask: Task;
}

export function TaskResults({ activeTask }: TaskResultsProps) {
  const [previewTab, setPreviewTab] = useState<'resume' | 'cover' | 'cover-text'>('resume');
  const [copiedCoverLetter, setCopiedCoverLetter] = useState(false);

  const isCompleted = activeTask.status === 'completed';
  const isFailed = activeTask.status === 'failed';
  const isCancelled = activeTask.status === 'cancelled';
  const hasResume = !!activeTask.resume_pdf_path;
  const hasCoverLetter = activeTask.generate_cover_letter && !!activeTask.cover_letter_pdf_path;

  const shouldShowEvaluation = activeTask && (isCompleted || (isFailed && hasResume));

  const {
    data: evaluation,
    isLoading: evalLoading,
    error: evalError,
  } = useEvaluationQuery(shouldShowEvaluation ? activeTask.id : undefined);
  const evaluateMutation = useEvaluateTaskMutation();
  const { data: coverLetterTextData } = useCoverLetterTextQuery(
    activeTask.id,
    previewTab === 'cover-text' && !!activeTask.cover_letter_pdf_path,
  );

  return (
    <>
      {/* Progress */}
      {activeTask.status !== 'pending' && <ProgressDisplay task={activeTask} />}

      {/* Error / partial result */}
      {(isFailed || isCancelled) && activeTask.error_message && (
        <div
          className={`${isCancelled ? 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700' : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'} border rounded-xl p-4`}
        >
          <div className="flex items-start gap-3">
            <AlertCircle
              className={`w-5 h-5 flex-shrink-0 mt-0.5 ${isCancelled ? 'text-gray-500' : 'text-red-500'}`}
            />
            <div>
              <h3
                className={`font-medium ${isCancelled ? 'text-gray-700 dark:text-gray-300' : 'text-red-800 dark:text-red-300'}`}
              >
                {isCancelled ? 'Task Cancelled' : 'Task Failed'}
              </h3>
              <p
                className={`text-sm mt-1 ${isCancelled ? 'text-gray-600 dark:text-gray-400' : 'text-red-600 dark:text-red-400'}`}
              >
                {activeTask.error_message}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Partial result notice */}
      {isFailed && hasResume && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-xl p-4">
          <p className="text-sm text-yellow-800 dark:text-yellow-300 font-medium">
            Resume was generated before the failure and is available for download.
          </p>
        </div>
      )}

      {/* Validation Warnings */}
      {(isCompleted || isFailed) &&
        activeTask.validation_warnings &&
        activeTask.validation_warnings.length > 0 && (
          <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5 text-amber-500" />
              <div>
                <h3 className="font-medium text-amber-800 dark:text-amber-300">
                  Validation Warnings
                </h3>
                <ul className="mt-2 space-y-1">
                  {activeTask.validation_warnings.map((warning, i) => (
                    <li key={i} className="text-sm text-amber-700 dark:text-amber-400">
                      {warning}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

      {/* Downloads */}
      {(isCompleted || (isFailed && hasResume)) && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl p-5">
          <h3 className="font-semibold text-green-800 dark:text-green-300 mb-4 flex items-center gap-2">
            <CheckCircleIcon />
            Files Ready for Download
          </h3>
          <div className="flex flex-wrap gap-3">
            {hasResume && (
              <a
                href={`${API_URL}/tasks/${activeTask.id}/resume`}
                download
                className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 border border-green-300 dark:border-green-700 rounded-lg text-green-700 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20 transition-colors font-medium shadow-sm text-sm"
              >
                <Download className="w-4 h-4" />
                Resume (PDF)
              </a>
            )}
            {hasCoverLetter && (
              <a
                href={`${API_URL}/tasks/${activeTask.id}/cover-letter`}
                download
                className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 border border-green-300 dark:border-green-700 rounded-lg text-green-700 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20 transition-colors font-medium shadow-sm text-sm"
              >
                <Download className="w-4 h-4" />
                Cover Letter (PDF)
              </a>
            )}
            {activeTask.latex_source && (
              <a
                href={`${API_URL}/tasks/${activeTask.id}/latex`}
                download
                className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors font-medium shadow-sm text-sm"
              >
                <Code className="w-4 h-4" />
                LaTeX Source (.tex)
              </a>
            )}
          </div>
        </div>
      )}

      {/* ATS Evaluation */}
      {shouldShowEvaluation && (
        <div className="space-y-3">
          {evalLoading && (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm p-6 flex items-center gap-3">
              <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Loading evaluation scores...
              </span>
            </div>
          )}
          {!!evaluation && <SkillMatchChart evaluation={evaluation as EvaluationData} />}
          {evalError && !evaluation && (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm p-4 flex items-center gap-3">
              <BarChart2 className="w-5 h-5 text-gray-400" />
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Evaluation not available yet.
              </span>
              <button
                onClick={() => evaluateMutation.mutate(activeTask.id)}
                disabled={evaluateMutation.isPending}
                className="ml-auto flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors"
              >
                {evaluateMutation.isPending ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <BarChart2 className="w-3.5 h-3.5" />
                )}
                Run Evaluation
              </button>
            </div>
          )}
          {!!evaluation && !evaluation.llm_breakdown && (
            <div className="flex justify-end">
              <button
                onClick={() => evaluateMutation.mutate(activeTask.id)}
                disabled={evaluateMutation.isPending}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-purple-700 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg hover:bg-purple-100 dark:hover:bg-purple-900/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {evaluateMutation.isPending ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Zap className="w-3.5 h-3.5" />
                )}
                Run AI Expert Review
              </button>
            </div>
          )}
        </div>
      )}

      {/* PDF Preview */}
      {(isCompleted || (isFailed && hasResume)) && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 dark:bg-gray-750 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
            <Eye className="w-4 h-4 text-gray-500" />
            <span className="font-medium text-gray-700 dark:text-gray-300 text-sm">
              PDF Preview
            </span>
            {hasCoverLetter && (
              <div className="flex ml-auto gap-1">
                <button
                  onClick={() => setPreviewTab('resume')}
                  className={`px-3 py-1 text-xs rounded ${
                    previewTab === 'resume'
                      ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
                      : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                >
                  Resume
                </button>
                <button
                  onClick={() => setPreviewTab('cover')}
                  className={`px-3 py-1 text-xs rounded ${
                    previewTab === 'cover'
                      ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
                      : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                >
                  Cover Letter
                </button>
                <button
                  onClick={() => setPreviewTab('cover-text')}
                  className={`px-3 py-1 text-xs rounded ${
                    previewTab === 'cover-text'
                      ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                      : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                >
                  Cover Letter (Text)
                </button>
              </div>
            )}
          </div>
          <div className="p-4">
            {previewTab === 'cover-text' && hasCoverLetter ? (
              <div className="relative">
                <button
                  onClick={async () => {
                    if (coverLetterTextData?.text) {
                      await navigator.clipboard.writeText(coverLetterTextData.text);
                      setCopiedCoverLetter(true);
                      setTimeout(() => setCopiedCoverLetter(false), 2000);
                    }
                  }}
                  className="absolute top-3 right-3 flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors shadow-sm z-10"
                >
                  {copiedCoverLetter ? (
                    <Check className="w-3.5 h-3.5 text-green-500" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                  {copiedCoverLetter ? 'Copied!' : 'Copy Text'}
                </button>
                <div className="w-full h-[600px] overflow-y-auto rounded border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-900 p-6">
                  {coverLetterTextData?.text ? (
                    <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-gray-800 dark:text-gray-200">
                      {coverLetterTextData.text}
                    </pre>
                  ) : (
                    <p className="text-gray-400 text-sm">Loading cover letter text...</p>
                  )}
                </div>
              </div>
            ) : (
              <iframe
                src={
                  previewTab === 'cover' && hasCoverLetter
                    ? `${API_URL}/tasks/${activeTask.id}/cover-letter?inline=true`
                    : `${API_URL}/tasks/${activeTask.id}/resume?inline=true`
                }
                className="w-full h-[600px] rounded border border-gray-200 dark:border-gray-600 bg-white"
                title="PDF Preview"
              />
            )}
          </div>
        </div>
      )}
    </>
  );
}

function CheckCircleIcon() {
  return (
    <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}
