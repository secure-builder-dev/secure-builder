import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import HoverCard from '../src/HoverCard';

afterEach(cleanup);

const mockTicket = {
  details: 'Fix the leaky faucet',
  filed_by: 'her',
  assigned_to: 'him',
  created_at: '2026-01-01T12:00:00Z',
};

const mockTicketEmptyDetails = {
  details: '',
  filed_by: 'him',
  assigned_to: 'her',
  created_at: '2026-01-02T12:00:00Z',
};

describe('HoverCard', () => {
  it('renders children inside a span with class hover-target', () => {
    render(
      <HoverCard ticket={mockTicket}>
        <span>Target Text</span>
      </HoverCard>
    );
    const target = screen.getByText('Target Text').closest('span');
    expect(target).toHaveClass('hover-target');
  });

  it('shows tooltip on mouseenter and hides on mouseleave', () => {
    render(
      <HoverCard ticket={mockTicket}>
        <span>Target Text</span>
      </HoverCard>
    );
    
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
    
    const target = screen.getByText('Target Text');
    fireEvent.mouseEnter(target);
    
    const tooltip = screen.getByRole('tooltip');
    expect(tooltip).toBeInTheDocument();
    expect(tooltip).toHaveClass('hover-card');
    
    fireEvent.mouseLeave(target);
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('shows tooltip on focus and hides on blur', () => {
    render(
      <HoverCard ticket={mockTicket}>
        <button>Target Button</button>
      </HoverCard>
    );
    
    const target = screen.getByText('Target Button');
    fireEvent.focus(target);
    expect(screen.getByRole('tooltip')).toBeInTheDocument();
    
    fireEvent.blur(target);
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('displays ticket details and metadata correctly', () => {
    render(
      <HoverCard ticket={mockTicket}>
        <span>Target</span>
      </HoverCard>
    );
    
    fireEvent.mouseEnter(screen.getByText('Target'));
    
    expect(screen.getByText('Fix the leaky faucet')).toBeInTheDocument();
    expect(screen.getByText('Filed by her')).toBeInTheDocument();
    expect(screen.getByText('Assigned to him')).toBeInTheDocument();
    expect(screen.getByText('Created 2026-01-01')).toBeInTheDocument();
  });

  it('displays "No details" when details are empty', () => {
    render(
      <HoverCard ticket={mockTicketEmptyDetails}>
        <span>Target</span>
      </HoverCard>
    );
    
    fireEvent.mouseEnter(screen.getByText('Target'));
    
    expect(screen.getByText('No details')).toBeInTheDocument();
    expect(screen.getByText('Filed by him')).toBeInTheDocument();
    expect(screen.getByText('Assigned to her')).toBeInTheDocument();
    expect(screen.getByText('Created 2026-01-02')).toBeInTheDocument();
  });
});