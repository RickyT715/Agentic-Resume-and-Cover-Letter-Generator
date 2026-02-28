import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QuestionsSection } from '../components/QuestionsSection';
import { useTaskStore } from '../store/taskStore';
import type { ApplicationQuestion } from '../types/task';

function makeQuestion(overrides: Partial<ApplicationQuestion> = {}): ApplicationQuestion {
  return {
    id: 'q-1',
    question: 'Why do you want to work here?',
    word_limit: 150,
    status: 'pending',
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

describe('QuestionsSection', () => {
  beforeEach(() => {
    useTaskStore.setState({ tasks: [], activeTaskId: null, toasts: [], darkMode: false });
    vi.restoreAllMocks();
  });

  it('renders the section header', () => {
    render(<QuestionsSection taskId="t1" questions={[]} jobDescription="Test JD" />);
    expect(screen.getByText('Application Questions')).toBeTruthy();
  });

  it('renders add question form', () => {
    render(<QuestionsSection taskId="t1" questions={[]} jobDescription="Test JD" />);
    expect(screen.getByPlaceholderText(/Enter an application question/)).toBeTruthy();
    expect(screen.getByText('Add')).toBeTruthy();
  });

  it('renders existing questions', () => {
    const questions = [
      makeQuestion({ id: 'q-1', question: 'Why do you want to work here?' }),
      makeQuestion({ id: 'q-2', question: 'What is your greatest strength?' }),
    ];
    render(<QuestionsSection taskId="t1" questions={questions} jobDescription="Test JD" />);
    expect(screen.getByText('Why do you want to work here?')).toBeTruthy();
    expect(screen.getByText('What is your greatest strength?')).toBeTruthy();
  });

  it('shows question count badge', () => {
    const questions = [makeQuestion(), makeQuestion({ id: 'q-2', question: 'Q2' })];
    render(<QuestionsSection taskId="t1" questions={questions} jobDescription="Test JD" />);
    expect(screen.getByText('2')).toBeTruthy();
  });

  it('shows word limit per question', () => {
    const questions = [makeQuestion({ word_limit: 200 })];
    render(<QuestionsSection taskId="t1" questions={questions} jobDescription="Test JD" />);
    expect(screen.getByText('200 words max')).toBeTruthy();
  });

  it('shows answer when present', () => {
    const questions = [makeQuestion({ answer: 'Because the mission aligns with my values.', status: 'completed' })];
    render(<QuestionsSection taskId="t1" questions={questions} jobDescription="Test JD" />);
    expect(screen.getByText('Because the mission aligns with my values.')).toBeTruthy();
  });

  it('shows word count for answers', () => {
    const questions = [makeQuestion({ answer: 'I love this company very much', status: 'completed' })];
    render(<QuestionsSection taskId="t1" questions={questions} jobDescription="Test JD" />);
    expect(screen.getByText('6 words')).toBeTruthy();
  });

  it('shows error message for failed question', () => {
    const questions = [makeQuestion({ status: 'failed', error_message: 'API rate limit exceeded' })];
    render(<QuestionsSection taskId="t1" questions={questions} jobDescription="Test JD" />);
    expect(screen.getByText('API rate limit exceeded')).toBeTruthy();
  });

  it('shows Generate All button when unanswered questions exist', () => {
    const questions = [makeQuestion({ status: 'pending' })];
    render(<QuestionsSection taskId="t1" questions={questions} jobDescription="Test JD" />);
    expect(screen.getByText(/Generate All Answers \(1\)/)).toBeTruthy();
  });

  it('does not show Generate All when all answered', () => {
    const questions = [makeQuestion({ status: 'completed', answer: 'Done' })];
    render(<QuestionsSection taskId="t1" questions={questions} jobDescription="Test JD" />);
    expect(screen.queryByText(/Generate All Answers/)).toBeNull();
  });

  it('shows JD required warning when no job description', () => {
    const questions = [makeQuestion()];
    render(<QuestionsSection taskId="t1" questions={questions} jobDescription="" />);
    expect(screen.getByText('A job description is required to generate answers.')).toBeTruthy();
  });

  it('toggles collapsed/expanded', () => {
    render(<QuestionsSection taskId="t1" questions={[]} jobDescription="Test JD" />);
    const header = screen.getByText('Application Questions');
    fireEvent.click(header);
    // After collapse, form should not be visible
    expect(screen.queryByPlaceholderText(/Enter an application question/)).toBeNull();
    // Click again to expand
    fireEvent.click(header);
    expect(screen.getByPlaceholderText(/Enter an application question/)).toBeTruthy();
  });

  it('calls API when adding a question', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(makeQuestion({ id: 'q-new', question: 'New question' })),
    });
    vi.stubGlobal('fetch', mockFetch);

    render(<QuestionsSection taskId="t1" questions={[]} jobDescription="Test JD" />);
    const textarea = screen.getByPlaceholderText(/Enter an application question/);
    fireEvent.change(textarea, { target: { value: 'New question' } });
    fireEvent.click(screen.getByText('Add'));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/tasks/t1/questions',
        expect.objectContaining({ method: 'POST' })
      );
    });

    vi.unstubAllGlobals();
  });

  it('calls API when deleting a question', async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });
    vi.stubGlobal('fetch', mockFetch);

    const questions = [makeQuestion()];
    render(<QuestionsSection taskId="t1" questions={questions} jobDescription="Test JD" />);

    const deleteBtn = screen.getByTitle('Delete question');
    fireEvent.click(deleteBtn);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/tasks/t1/questions/q-1',
        expect.objectContaining({ method: 'DELETE' })
      );
    });

    vi.unstubAllGlobals();
  });
});
