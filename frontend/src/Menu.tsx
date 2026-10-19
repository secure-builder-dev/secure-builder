import React, { useState } from "react";

type MenuProps = {
  onDirections: () => void;
};

export default function Menu({ onDirections }: MenuProps) {
  const [open, setOpen] = useState(false);

  const toggleMenu = () => setOpen((prev) => !prev);
  const handleDirections = () => {
    onDirections();
    setOpen(false);
  };

  return (
    <>
      <button
        className="menu-button"
        aria-label="Menu"
        aria-expanded={open ? "true" : "false"}
        onClick={toggleMenu}
      >
        ☰
      </button>
      {open && (
        <nav className="menu" aria-label="Main menu">
          <button onClick={handleDirections}>Directions</button>
        </nav>
      )}
    </>
  );
}
