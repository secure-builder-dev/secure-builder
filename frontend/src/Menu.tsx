import React, { useState } from 'react';

export default function Menu({ onDirections }) {
  const [isOpen, setIsOpen] = useState(false);

  const toggleMenu = () => {
    setIsOpen(!isOpen);
  };

  return (
    <>
      <button
        aria-label='Menu'
        aria-expanded={isOpen}
        onClick={toggleMenu}
      >
        ☰
      </button>
      {isOpen && (
        <nav aria-label='Main menu'>
          <button onClick={() => { onDirections(); toggleMenu(); }}>Directions</button>
        </nav>
      )}
    </>
  );
}