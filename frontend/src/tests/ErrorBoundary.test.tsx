import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ErrorBoundary } from '../components/ErrorBoundary';

function GoodChild() {
  return <div>All is well</div>;
}

function BadChild(): never {
  throw new Error('Test error message');
}

describe('ErrorBoundary', () => {
  beforeEach(() => {
    // Suppress React error boundary console.error output in test output
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  it('renders children normally when no error', () => {
    render(
      <ErrorBoundary>
        <GoodChild />
      </ErrorBoundary>,
    );
    expect(screen.getByText('All is well')).toBeTruthy();
  });

  it('catches render errors and shows fallback UI', () => {
    render(
      <ErrorBoundary>
        <BadChild />
      </ErrorBoundary>,
    );
    expect(screen.getByText('Something went wrong')).toBeTruthy();
    expect(screen.getByText('Test error message')).toBeTruthy();
  });

  it('shows reload button in error state', () => {
    render(
      <ErrorBoundary>
        <BadChild />
      </ErrorBoundary>,
    );
    expect(screen.getByText('Reload')).toBeTruthy();
  });

  it('shows default message when error has no message', () => {
    function EmptyErrorChild(): never {
      throw new Error();
    }

    render(
      <ErrorBoundary>
        <EmptyErrorChild />
      </ErrorBoundary>,
    );
    expect(screen.getByText('Something went wrong')).toBeTruthy();
  });

  it('does not show error UI when children render successfully', () => {
    render(
      <ErrorBoundary>
        <GoodChild />
      </ErrorBoundary>,
    );
    expect(screen.queryByText('Something went wrong')).toBeNull();
    expect(screen.queryByText('Reload')).toBeNull();
  });
});
