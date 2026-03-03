import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SettingFieldRenderer } from '../components/settings/SettingFieldRenderer';
import type { SettingField } from '../components/settings/SettingFieldRenderer';

describe('SettingFieldRenderer', () => {
  it('renders text input with label', () => {
    const field: SettingField = {
      key: 'test_field',
      label: 'Test Field',
      type: 'text',
      placeholder: 'Enter value',
    };
    render(<SettingFieldRenderer field={field} value="hello" onChange={vi.fn()} />);
    expect(screen.getByText('Test Field')).toBeTruthy();
    const input = screen.getByPlaceholderText('Enter value');
    expect((input as HTMLInputElement).value).toBe('hello');
  });

  it('calls onChange for text input', () => {
    const onChange = vi.fn();
    const field: SettingField = {
      key: 'my_text',
      label: 'My Text',
      type: 'text',
    };
    render(<SettingFieldRenderer field={field} value="" onChange={onChange} />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'new value' } });
    expect(onChange).toHaveBeenCalledWith('my_text', 'new value');
  });

  it('renders password input', () => {
    const field: SettingField = {
      key: 'api_key',
      label: 'API Key',
      type: 'password',
      placeholder: 'Enter API key',
    };
    render(<SettingFieldRenderer field={field} value="secret" onChange={vi.fn()} />);
    expect(screen.getByText('API Key')).toBeTruthy();
    const input = screen.getByPlaceholderText('Enter API key') as HTMLInputElement;
    expect(input.type).toBe('password');
    expect(input.value).toBe('secret');
  });

  it('renders select dropdown with options', () => {
    const field: SettingField = {
      key: 'provider',
      label: 'Provider',
      type: 'select',
      options: [
        { value: 'gemini', label: 'Google Gemini' },
        { value: 'claude', label: 'Anthropic Claude' },
      ],
    };
    render(<SettingFieldRenderer field={field} value="gemini" onChange={vi.fn()} />);
    expect(screen.getByText('Provider')).toBeTruthy();
    expect(screen.getByText('Google Gemini')).toBeTruthy();
    expect(screen.getByText('Anthropic Claude')).toBeTruthy();
  });

  it('calls onChange for select dropdown', () => {
    const onChange = vi.fn();
    const field: SettingField = {
      key: 'provider',
      label: 'Provider',
      type: 'select',
      options: [
        { value: 'gemini', label: 'Google Gemini' },
        { value: 'claude', label: 'Anthropic Claude' },
      ],
    };
    render(<SettingFieldRenderer field={field} value="gemini" onChange={onChange} />);
    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'claude' } });
    expect(onChange).toHaveBeenCalledWith('provider', 'claude');
  });

  it('renders number input', () => {
    const field: SettingField = {
      key: 'max_retries',
      label: 'Max Retries',
      type: 'number',
      min: 1,
      max: 10,
    };
    render(<SettingFieldRenderer field={field} value={3} onChange={vi.fn()} />);
    expect(screen.getByText('Max Retries')).toBeTruthy();
    const input = screen.getByRole('spinbutton') as HTMLInputElement;
    expect(input.value).toBe('3');
    expect(input.min).toBe('1');
    expect(input.max).toBe('10');
  });

  it('calls onChange with integer for number input', () => {
    const onChange = vi.fn();
    const field: SettingField = {
      key: 'max_retries',
      label: 'Max Retries',
      type: 'number',
    };
    render(<SettingFieldRenderer field={field} value={3} onChange={onChange} />);
    const input = screen.getByRole('spinbutton');
    fireEvent.change(input, { target: { value: '5' } });
    expect(onChange).toHaveBeenCalledWith('max_retries', 5);
  });

  it('calls onChange with null for empty number input', () => {
    const onChange = vi.fn();
    const field: SettingField = {
      key: 'temperature',
      label: 'Temperature',
      type: 'number',
    };
    render(<SettingFieldRenderer field={field} value={1.0} onChange={onChange} />);
    const input = screen.getByRole('spinbutton');
    fireEvent.change(input, { target: { value: '' } });
    expect(onChange).toHaveBeenCalledWith('temperature', null);
  });

  it('calls onChange with float for number input with fractional step', () => {
    const onChange = vi.fn();
    const field: SettingField = {
      key: 'temperature',
      label: 'Temperature',
      type: 'number',
      step: 0.1,
      min: 0,
      max: 2,
    };
    render(<SettingFieldRenderer field={field} value={1.0} onChange={onChange} />);
    const input = screen.getByRole('spinbutton');
    fireEvent.change(input, { target: { value: '0.7' } });
    expect(onChange).toHaveBeenCalledWith('temperature', 0.7);
  });

  it('renders toggle/checkbox', () => {
    const field: SettingField = {
      key: 'enable_search',
      label: 'Enable Search',
      type: 'toggle',
    };
    render(<SettingFieldRenderer field={field} value={true} onChange={vi.fn()} />);
    expect(screen.getByText('Enable Search')).toBeTruthy();
    const checkbox = screen.getByRole('checkbox') as HTMLInputElement;
    expect(checkbox.checked).toBe(true);
  });

  it('calls onChange for toggle', () => {
    const onChange = vi.fn();
    const field: SettingField = {
      key: 'enable_search',
      label: 'Enable Search',
      type: 'toggle',
    };
    render(<SettingFieldRenderer field={field} value={false} onChange={onChange} />);
    const checkbox = screen.getByRole('checkbox');
    fireEvent.click(checkbox);
    expect(onChange).toHaveBeenCalledWith('enable_search', true);
  });

  it('renders help text when provided', () => {
    const field: SettingField = {
      key: 'test',
      label: 'Test',
      type: 'text',
      helpText: 'This is helpful information',
    };
    render(<SettingFieldRenderer field={field} value="" onChange={vi.fn()} />);
    expect(screen.getByText('This is helpful information')).toBeTruthy();
  });

  it('renders help text for toggle type', () => {
    const field: SettingField = {
      key: 'toggle_field',
      label: 'Toggle',
      type: 'toggle',
      helpText: 'Toggle help text',
    };
    render(<SettingFieldRenderer field={field} value={false} onChange={vi.fn()} />);
    expect(screen.getByText('Toggle help text')).toBeTruthy();
  });

  it('renders help text for select type', () => {
    const field: SettingField = {
      key: 'select_field',
      label: 'Select',
      type: 'select',
      options: [{ value: 'a', label: 'A' }],
      helpText: 'Select help text',
    };
    render(<SettingFieldRenderer field={field} value="a" onChange={vi.fn()} />);
    expect(screen.getByText('Select help text')).toBeTruthy();
  });

  it('renders help text for number type', () => {
    const field: SettingField = {
      key: 'num_field',
      label: 'Number',
      type: 'number',
      helpText: 'Number help text',
    };
    render(<SettingFieldRenderer field={field} value={1} onChange={vi.fn()} />);
    expect(screen.getByText('Number help text')).toBeTruthy();
  });

  it('renders url input type', () => {
    const field: SettingField = {
      key: 'linkedin_url',
      label: 'LinkedIn URL',
      type: 'url',
      placeholder: 'https://linkedin.com/in/yourprofile',
    };
    render(<SettingFieldRenderer field={field} value="https://linkedin.com/in/test" onChange={vi.fn()} />);
    expect(screen.getByText('LinkedIn URL')).toBeTruthy();
    const input = screen.getByPlaceholderText('https://linkedin.com/in/yourprofile') as HTMLInputElement;
    expect(input.type).toBe('url');
    expect(input.value).toBe('https://linkedin.com/in/test');
  });

  it('handles null/undefined value gracefully for text input', () => {
    const field: SettingField = {
      key: 'test',
      label: 'Test',
      type: 'text',
    };
    render(<SettingFieldRenderer field={field} value={null} onChange={vi.fn()} />);
    const input = screen.getByRole('textbox') as HTMLInputElement;
    expect(input.value).toBe('');
  });

  it('handles null/undefined value gracefully for number input', () => {
    const field: SettingField = {
      key: 'test',
      label: 'Test',
      type: 'number',
    };
    render(<SettingFieldRenderer field={field} value={null} onChange={vi.fn()} />);
    const input = screen.getByRole('spinbutton') as HTMLInputElement;
    expect(input.value).toBe('');
  });
});
