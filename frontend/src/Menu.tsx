import React, { useState } from 'react';

export default function Menu({ onDirections }: { onDirections: () => void }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        className="menu-button"
        aria-label="Menu"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        ☰
      </button>
      {open && (
        <nav className="menu" aria-label="Main menu">
          <button onClick={() => {
            onDirections();
            setOpen(false);
          }}>
            Directions
          </button>
        </nav>
      )}
    </>
  );
}