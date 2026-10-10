import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import Directions from '../src/Directions';

afterEach(() => {
  cleanup();
});

describe('Directions Component', () => {
  const expectedSteps = [
    'Paste your token into the Token field and press Load.',
    'To ask your partner for something, fill in New ticket and press File ticket: it lands in their To Do column.',
    'Work the tickets filed for you: Acknowledge, then Start, then Done.',
    'When your partner marks your ticket Done, Close it, or Reopen it if it is not finished.',
    'The Household board shows every ticket for both of you, and hovering a title shows its details.',
  ];

  it('renders the Directions header and the five specific steps in an ordered list', () => {
    render(<Directions onClose={vi.fn()} />);
    
    expect(screen.getByText('Directions')).toBeInTheDocument();
    
    const listItems = screen.getAllByRole('listitem');
    expect(listItems).toHaveLength(5);
    
    expectedSteps.forEach((step, index) => {
      expect(listItems[index]).toHaveTextContent(step);
    });
  });

  it('calls onClose once when the Close button is clicked', () => {
    const onCloseMock = vi.fn();
    render(<Directions onClose={onCloseMock} />);
    
    const closeButton = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeButton);
    
    expect(onCloseMock).toHaveBeenCalledTimes(1);
  });
});