// Menu component
// Renders a toggleable menu button that opens a navigation with a Directions button.
// Clicking the Directions button calls the provided onDirections callback and closes the menu.

import React, { useState } from "react";

interface MenuProps {
  onDirections: () => void;
}

const Menu: React.FC<MenuProps> = ({ onDirections }) => {
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
        aria-expanded={open}
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
};

export default Menu;
