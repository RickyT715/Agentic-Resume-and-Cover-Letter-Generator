import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProgressDisplay } from '../components/ProgressDisplay';
import type { Task, StepProgress } from '../types/task';

function makeStep(overrides: Partial<StepProgress> = {}): StepProgress {
  return {
    step: 'generate_resume',
    status: 'pending',
    message: '',
    attempt: 0,
    ...overrides,
  };
}

function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 'test-1',
    task_number: 1,
    job_description: 'Test JD',
    status: 'running',
    generate_cover_letter: true,
    template_id: 'classic',
    steps: [
      makeStep({ step: 'generate_resume' }),
      makeStep({ step: 'compile_latex' }),
      makeStep({ step: 'extract_text' }),
      makeStep({ step: 'generate_cover_letter' }),
      makeStep({ step: 'create_cover_pdf' }),
    ],
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

describe('ProgressDisplay', () => {
  it('renders all step labels', () => {
    render(<ProgressDisplay task={makeTask()} />);
    expect(screen.getByText(/Generating Resume with AI/)).toBeTruthy();
    expect(screen.getByText(/Compiling LaTeX to PDF/)).toBeTruthy();
    expect(screen.getByText(/Extracting Text from PDF/)).toBeTruthy();
    expect(screen.getByText(/Generating Cover Letter with AI/)).toBeTruthy();
    expect(screen.getByText(/Creating Cover Letter PDF/)).toBeTruthy();
  });

  it('renders progress header with step count', () => {
    render(<ProgressDisplay task={makeTask()} />);
    expect(screen.getByText('Progress')).toBeTruthy();
    expect(screen.getByText(/0 of 5 steps/)).toBeTruthy();
  });

  it('shows correct completed count', () => {
    const task = makeTask({
      steps: [
        makeStep({ step: 'generate_resume', status: 'completed' }),
        makeStep({ step: 'compile_latex', status: 'completed' }),
        makeStep({ step: 'extract_text', status: 'pending' }),
        makeStep({ step: 'generate_cover_letter', status: 'pending' }),
        makeStep({ step: 'create_cover_pdf', status: 'pending' }),
      ],
    });
    render(<ProgressDisplay task={task} />);
    expect(screen.getByText(/2 of 5 steps \(40%\)/)).toBeTruthy();
  });

  it('shows 100% when all steps completed', () => {
    const task = makeTask({
      status: 'completed',
      steps: [
        makeStep({ step: 'generate_resume', status: 'completed' }),
        makeStep({ step: 'compile_latex', status: 'completed' }),
        makeStep({ step: 'extract_text', status: 'completed' }),
        makeStep({ step: 'generate_cover_letter', status: 'completed' }),
        makeStep({ step: 'create_cover_pdf', status: 'completed' }),
      ],
    });
    render(<ProgressDisplay task={task} />);
    expect(screen.getByText(/5 of 5 steps \(100%\)/)).toBeTruthy();
  });

  it('shows step message when present', () => {
    const task = makeTask({
      steps: [
        makeStep({ step: 'generate_resume', status: 'running', message: 'Generating tailored resume...' }),
        makeStep({ step: 'compile_latex' }),
        makeStep({ step: 'extract_text' }),
        makeStep({ step: 'generate_cover_letter' }),
        makeStep({ step: 'create_cover_pdf' }),
      ],
    });
    render(<ProgressDisplay task={task} />);
    expect(screen.getByText('Generating tailored resume...')).toBeTruthy();
  });

  it('shows error message for failed step', () => {
    const task = makeTask({
      status: 'failed',
      steps: [
        makeStep({ step: 'generate_resume', status: 'completed' }),
        makeStep({ step: 'compile_latex', status: 'failed', message: 'LaTeX compilation error' }),
        makeStep({ step: 'extract_text' }),
        makeStep({ step: 'generate_cover_letter' }),
        makeStep({ step: 'create_cover_pdf' }),
      ],
    });
    render(<ProgressDisplay task={task} />);
    expect(screen.getByText('LaTeX compilation error')).toBeTruthy();
  });

  it('shows attempt badge for compile_latex retries', () => {
    const task = makeTask({
      steps: [
        makeStep({ step: 'generate_resume', status: 'completed' }),
        makeStep({ step: 'compile_latex', status: 'running', attempt: 2 }),
        makeStep({ step: 'extract_text' }),
        makeStep({ step: 'generate_cover_letter' }),
        makeStep({ step: 'create_cover_pdf' }),
      ],
    });
    render(<ProgressDisplay task={task} />);
    expect(screen.getByText(/Attempt 2\/3/)).toBeTruthy();
  });

  it('shows step descriptions', () => {
    render(<ProgressDisplay task={makeTask()} />);
    expect(screen.getByText('Using AI to create a tailored LaTeX resume')).toBeTruthy();
    expect(screen.getByText('Converting LaTeX code to PDF format')).toBeTruthy();
  });
});
