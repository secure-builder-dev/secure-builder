import React from "react";

interface DirectionsProps {
  onClose: () => void;
}

const Directions: React.FC<DirectionsProps> = ({ onClose }) => {
  const steps = [
    "Paste your token into the Token field and press Load.",
    "To ask your partner for something, fill in New ticket and press File ticket: it lands in their To Do column.",
    "Work the tickets filed for you: Acknowledge, then Start, then Done.",
    "When your partner marks your ticket Done, Close it, or Reopen it if it is not finished.",
    "The Household board shows every ticket for both of you, and hovering a title shows its details.",
  ];

  return (
    <section className="panel directions" aria-label="Directions">
      <h2>Directions</h2>
      <ol>
        {steps.map((s, i) => (
          <li key={i}>{s}</li>
        ))}
      </ol>
      <button type="button" onClick={onClose}>Close</button>
    </section>
  );
};

export default Directions;
