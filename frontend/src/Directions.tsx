import React from 'react';

export default function Directions({ onClose }: { onClose: () => void }) {
  return (
    <section className="panel directions" aria-label="Directions">
      <h2>Directions</h2>
      <ol>
        <li>Paste your token into the Token field and press Load.</li>
        <li>To ask your partner for something, fill in New ticket and press File ticket: it lands in their To Do column.</li>
        <li>Work the tickets filed for you: Acknowledge, then Start, then Done.</li>
        <li>When your partner marks your ticket Done, Close it, or Reopen it if it is not finished.</li>
        <li>The Household board shows every ticket for both of you, and hovering a title shows its details.</li>
      </ol>
      <button onClick={onClose}>Close</button>
    </section>
  );
}
