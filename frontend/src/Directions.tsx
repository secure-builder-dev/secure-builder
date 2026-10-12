import React from "react";

interface DirectionsProps {
  onClose: () => void;
}

const STEPS = [
  "Paste your token into the Token field and press Load.",
  "To ask your partner for something, fill in New ticket and press File ticket: it lands in their To Do column.",
  "Work the tickets filed for you: Acknowledge, then Start, then Done.",
  "When your partner marks your ticket Done, Close it, or Reopen it if it is not finished.",
  "The Household board shows every ticket for both of you, and hovering a title shows its details.",
];

export default function Directions({ onClose }: DirectionsProps) {
  return (
    <section className="panel directions" aria-label="Directions">
      <h2>Directions</h2>
      <ol>
        {STEPS.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      <button type="button" onClick={onClose}>Close</button>
    </section>
  );
}
