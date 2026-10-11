import React, { useState } from 'react';

export default function Menu({ onDirections }: { onDirections: () => void }) {
  const [isOpen, setIsOpen] = useState(false);

  const toggleMenu = () => {
    setIsOpen(!isOpen);
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
        ☰
      </button>
      {isOpen && (
        <nav aria-label="Main menu">
          <button onClick={handleDirections}>Directions</button>
        </nav>
      )}
    </>
  );
}
