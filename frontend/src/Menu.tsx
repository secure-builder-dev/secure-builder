import React, { useState } from 'react';

interface MenuProps {
  onDirections: () => void;
}

export default function Menu({ onDirections }: MenuProps) {
  const [isOpen, setIsOpen] = useState(false);

  const toggleMenu = () => {
    setIsOpen((prev) => !prev);
  };

  const handleDirections = () => {
    onDirections();
    setIsOpen(false);
  };

  return (
    <>
      <button
        aria-label="Menu"
        aria-expanded={isOpen}
        onClick={toggleMenu}
      >
        ☰ Menu
      </button>
      {isOpen && (
        <nav aria-label="Main menu">
          <button onClick={handleDirections}>Directions</button>
        </nav>
      )}
    </>
  );
}