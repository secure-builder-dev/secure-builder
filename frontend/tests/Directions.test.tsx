import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, afterEach, vi } from 'vitest';
import '@testing-library/jest-dom/vitest';
import Directions from '../src/Directions';

afterEach(cleanup);

describe('Directions Component', () => {
  it('renders a section headed Directions', () => {
    render(<Directions onClose={() => {}} />);
    expect(screen.getByRole('heading', { name: /directions/i })).toBeInTheDocument();
  });

  it('renders an ordered list with exactly five specific steps in the correct order and ending with full stops', () => {
    render(<Directions onClose={() => {}} />);
    const list = screen.getByRole('list');
    expect(list.tagName).toBe('OL');
    
    const items = screen.getAllByRole('listitem');
    expect(items).toHaveLength(5);

    const expectedSteps = [
      'Paste your token into the Token field and press Load.',
      'To ask your partner for something, fill in New ticket and press File ticket: it lands in their To Do column.',
      'Work the tickets filed for you: Acknowledge, then Start, then Done.',
      'When your partner marks your ticket Done, Close it, or Reopen it if it is not finished.',
      'The Household board shows every ticket for both of you, and hovering a title shows its details.'
    ];

    items.forEach((item, index) => {
      expect(item.textContent).toBe(expectedSteps[index]);
    });
  });

  it('renders a Close button that calls onClose once when clicked', () => {
    const onClose = vi.fn();
    render(<Directions onClose={onClose} />);
    
    const closeButton = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeButton);
    
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});