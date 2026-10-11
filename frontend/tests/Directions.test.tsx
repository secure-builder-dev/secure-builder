import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import Directions from '../src/Directions';

afterEach(() => {
  cleanup();
});

describe('Directions Component', () => {
  it('renders the correct heading and exactly five steps in the correct order', () => {
    render(<Directions onClose={vi.fn()} />);
    
    expect(screen.getByRole('heading', { name: /Directions/i })).toBeInTheDocument();
    
    const steps = screen.getAllByRole('listitem');
    expect(steps).toHaveLength(5);
    
    const expectedTexts = [
      'Paste your token into the Token field and press Load.',
      'To ask your partner for something, fill in New ticket and press File ticket: it lands in their To Do column.',
      'Work the tickets filed for you: Acknowledge, then Start, then Done.',
      'When your partner marks your ticket Done, Close it, or Reopen it if it is not finished.',
      'The Household board shows every ticket for both of you, and hovering a title shows its details.'
    ];
    
    steps.forEach((step, index) => {
      expect(step.textContent).toBe(expectedTexts[index]);
    });
  });

  it('calls onClose once when the Close button is clicked', () => {
    const onClose = vi.fn();
    render(<Directions onClose={onClose} />);
    
    const closeButton = screen.getByRole('button', { name: /Close/i });
    fireEvent.click(closeButton);
    
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});