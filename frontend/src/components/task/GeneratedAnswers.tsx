import { useState } from 'react';
import { ClipboardList, Copy, Check } from 'lucide-react';
import { ApplicationQuestion } from '../../types/task';
import { useTaskStore } from '../../store/taskStore';

interface GeneratedAnswersProps {
  questions: ApplicationQuestion[];
}

export function GeneratedAnswers({ questions }: GeneratedAnswersProps) {
  const addToast = useTaskStore((s) => s.addToast);
  const [copiedAnswerId, setCopiedAnswerId] = useState<string | null>(null);
  const [copiedAll, setCopiedAll] = useState(false);

  const answeredQuestions = questions.filter((q) => q.answer);
  if (answeredQuestions.length === 0) return null;

  const handleCopyAnswer = async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedAnswerId(id);
      setTimeout(() => setCopiedAnswerId(null), 2000);
    } catch {
      addToast('error', 'Failed to copy');
    }
  };

  const handleCopyAll = async () => {
    const formatted = answeredQuestions.map((q) => `Q: ${q.question}\nA: ${q.answer}`).join('\n\n');
    try {
      await navigator.clipboard.writeText(formatted);
      setCopiedAll(true);
      setTimeout(() => setCopiedAll(false), 2000);
    } catch {
      addToast('error', 'Failed to copy');
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
      <div className="px-4 py-3 bg-gray-50 dark:bg-gray-750 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
        <ClipboardList className="w-4 h-4 text-purple-500" />
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
          Generated Answers
        </span>
        <span className="px-2 py-0.5 text-xs rounded-full bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400">
          {answeredQuestions.length}
        </span>
        <button
          onClick={handleCopyAll}
          className="ml-auto flex items-center gap-1.5 px-3 py-1 text-xs font-medium text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-900/20 rounded transition-colors"
        >
          {copiedAll ? (
            <Check className="w-3.5 h-3.5 text-green-500" />
          ) : (
            <Copy className="w-3.5 h-3.5" />
          )}
          {copiedAll ? 'Copied!' : 'Copy All'}
        </button>
      </div>
      <div className="p-4 space-y-4">
        {answeredQuestions.map((q) => (
          <div
            key={q.id}
            className="border border-gray-200 dark:border-gray-600 rounded-lg overflow-hidden"
          >
            <div className="px-3 py-2 bg-gray-50 dark:bg-gray-750">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{q.question}</p>
            </div>
            <div className="px-3 py-2 bg-white dark:bg-gray-800">
              <div className="flex items-start gap-2">
                <p className="flex-1 text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                  {q.answer}
                </p>
                <button
                  onClick={() => handleCopyAnswer(q.answer!, q.id)}
                  className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 flex-shrink-0"
                  title="Copy answer"
                >
                  {copiedAnswerId === q.id ? (
                    <Check className="w-4 h-4 text-green-500" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </button>
              </div>
              <span className="text-xs text-gray-400 dark:text-gray-500 mt-1 block">
                {q.answer!.split(/\s+/).length} words
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
