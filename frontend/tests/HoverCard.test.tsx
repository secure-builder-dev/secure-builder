import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import HoverCard from '../src/HoverCard';

afterEach(cleanup);

const mockTicket = {
  details: 'Fix the leaky faucet',
  filed_by: 'her',
  assigned_to: 'him',
  created_at: '2023-10-27T10:00:00Z',
};

const mockTicketEmptyDetails = {
  details: '',
  filed_by: 'him',
  assigned_to: 'her',
  created_at: '2023-10-28T12:00:00Z',
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
    const target = screen.getByText('Target Text');
    
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
    
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
        <span>Target Text</span>
      </HoverCard>
    );
    const target = screen.getByText('Target Text').closest('span');
    
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
    
    fireEvent.focus(target);
    expect(screen.getByRole('tooltip')).toBeInTheDocument();
    
    fireEvent.blur(target);
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('displays ticket details and metadata correctly', () => {
    render(
      <HoverCard ticket={mockTicket}>
        <span>Target Text</span>
      </HoverCard>
    );
    fireEvent.mouseEnter(screen.getByText('Target Text'));
    
    const tooltip = screen.getByRole('tooltip');
    expect(tooltip).toHaveTextContent('Fix the leaky faucet');
    expect(tooltip).toHaveTextContent('Filed by her');
    expect(tooltip).toHaveTextContent('Assigned to him');
    expect(tooltip).toHaveTextContent('Created 2023-10-27');
  });

  it('displays "No details" when details are empty', () => {
    render(
      <HoverCard ticket={mockTicketEmptyDetails}>
        <span>Target Text</span>
      </HoverCard>
    );
    fireEvent.mouseEnter(screen.getByText('Target Text'));
    
    const tooltip = screen.getByRole('tooltip');
    expect(tooltip).toHaveTextContent('No details');
    expect(tooltip).toHaveTextContent('Filed by him');
    expect(tooltip).toHaveTextContent('Assigned to her');
    expect(tooltip).toHaveTextContent('Created 2023-10-28');
  });
});