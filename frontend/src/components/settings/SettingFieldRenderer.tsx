import { AppSettings } from '../../types/task';

export type SettingField = {
  key: string;
  label: string;
  type: 'text' | 'password' | 'select' | 'number' | 'toggle' | 'url';
  options?: { value: string; label: string }[];
  helpText?: string;
  placeholder?: string;
  min?: number;
  max?: number;
  step?: number;
  conditional?: (settings: AppSettings) => boolean;
};

export type SettingsSection = {
  id: string;
  title: string;
  defaultExpanded?: boolean;
  fields: SettingField[];
};

interface SettingFieldRendererProps {
  field: SettingField;
  value: unknown;
  onChange: (key: string, value: unknown) => void;
}

export function SettingFieldRenderer({ field, value, onChange }: SettingFieldRendererProps) {
  const inputClass =
    'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100';

  if (field.type === 'toggle') {
    return (
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id={field.key}
          checked={!!value}
          onChange={(e) => onChange(field.key, e.target.checked)}
          className="w-4 h-4 text-blue-600 rounded"
        />
        <label htmlFor={field.key} className="text-sm text-gray-700 dark:text-gray-300">
          {field.label}
        </label>
        {field.helpText && (
          <p className="text-xs text-gray-500 dark:text-gray-400 ml-2">{field.helpText}</p>
        )}
      </div>
    );
  }

  if (field.type === 'select') {
    return (
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          {field.label}
        </label>
        <select
          value={(value as string) || ''}
          onChange={(e) => onChange(field.key, e.target.value)}
          className={inputClass}
        >
          {field.options?.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {field.helpText && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{field.helpText}</p>
        )}
      </div>
    );
  }

  if (field.type === 'number') {
    return (
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          {field.label}
        </label>
        <input
          type="number"
          step={field.step}
          min={field.min}
          max={field.max}
          value={(value as string | number) ?? ''}
          onChange={(e) => {
            const v = e.target.value;
            if (v === '') {
              onChange(field.key, null);
            } else if (field.step && field.step < 1) {
              onChange(field.key, parseFloat(v));
            } else {
              onChange(field.key, parseInt(v));
            }
          }}
          className={inputClass}
          placeholder={field.placeholder}
        />
        {field.helpText && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{field.helpText}</p>
        )}
      </div>
    );
  }

  // text, password, url
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        {field.label}
      </label>
      <input
        type={field.type}
        value={(value as string) || ''}
        onChange={(e) => onChange(field.key, e.target.value)}
        className={inputClass}
        placeholder={field.placeholder}
      />
      {field.helpText && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{field.helpText}</p>
      )}
    </div>
  );
}
