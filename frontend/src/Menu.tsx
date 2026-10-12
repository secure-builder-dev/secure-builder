import { useState } from "react";

interface MenuProps {
  onDirections: () => void;
}

export default function Menu({ onDirections }: MenuProps) {
  const [open, setOpen] = useState(false);

  const toggleMenu = () => setOpen((prev) => !prev);

  const handleDirections = () => {
    setOpen(false);
    onDirections();
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
}
