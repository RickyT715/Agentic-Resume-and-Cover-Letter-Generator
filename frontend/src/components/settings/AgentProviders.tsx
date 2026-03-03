import { AppSettings } from '../../types/task';
import { AGENT_LABELS, AGENT_PROVIDER_OPTIONS } from './settingsSchema';

interface AgentProvidersProps {
  settings: AppSettings;
  onUpdate: (agent: string, provider: string) => void;
}

export function AgentProviders({ settings, onUpdate }: AgentProvidersProps) {
  return (
    <div className="p-4 space-y-3">
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
        Override the AI provider for individual pipeline agents. Leave as "Use Default" to use the
        task-level provider.
      </p>
      {Object.entries(AGENT_LABELS).map(([agent, label]) => (
        <div key={agent} className="flex items-center gap-3">
          <label className="text-sm text-gray-700 dark:text-gray-300 w-40 shrink-0">{label}</label>
          <select
            value={(settings.agent_providers || {})[agent] || ''}
            onChange={(e) => onUpdate(agent, e.target.value)}
            className="flex-1 px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
          >
            {AGENT_PROVIDER_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      ))}
    </div>
  );
}
