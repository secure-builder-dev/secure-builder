import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import Menu from '../src/Menu';

afterEach(cleanup);

describe('Menu Component', () => {
  it('renders a Menu button with correct label, icon, and initial aria-expanded state', () => {
    render(<Menu onDirections={vi.fn()} />);
    const button = screen.getByRole('button', { name: /menu/i });
    expect(button).toHaveTextContent('☰');
    expect(button).toHaveAttribute('aria-expanded', 'false');
  });

  it('toggles the Main menu and aria-expanded state when the Menu button is clicked', () => {
    render(<Menu onDirections={vi.fn()} />);
    const button = screen.getByRole('button', { name: /menu/i });

    // Open
    fireEvent.click(button);
    expect(button).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('navigation', { name: /main menu/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /directions/i })).toBeInTheDocument();

    // Close
    fireEvent.click(button);
    expect(button).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByRole('navigation', { name: /main menu/i })).not.toBeInTheDocument();
  });

  it('calls onDirections and closes the menu when Directions button is clicked', () => {
    const onDirections = vi.fn();
    render(<Menu onDirections={onDirections} />);
    const menuButton = screen.getByRole('button', { name: /menu/i });

    // Open menu
    fireEvent.click(menuButton);
    const directionsButton = screen.getByRole('button', { name: /directions/i });

    // Click Directions
    fireEvent.click(directionsButton);
    expect(onDirections).toHaveBeenCalledTimes(1);
    expect(menuButton).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByRole('navigation', { name: /main menu/i })).not.toBeInTheDocument();
  });
});