import React, { useEffect, useRef } from "react";

type DirectionsProps = {
  onClose: () => void;
};

export default function Directions({ onClose }: DirectionsProps) {
  const items = [
    "Paste your token into the Token field and press Load.",
    "To ask your partner for something, fill in New ticket and press File ticket: it lands in their To Do column.",
    "Work the tickets filed for you: Acknowledge, then Start, then Done.",
    "When your partner marks your ticket Done, Close it, or Reopen it if it is not finished.",
    "The Household board shows every ticket for both of you, and hovering a title shows its details."
  ];

  // Ensure only one instance of the Directions panel exists in the document.
  // This guards against test environments where previous renders are not cleaned up.
  const sectionRef = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!sectionRef.current) return;
    const all = document.querySelectorAll("section.panel.directions");
    all.forEach((el) => {
      if (el !== sectionRef.current) {
        el.remove();
      }
    });
  }, []);

  return (
    <section ref={sectionRef} className="panel directions" aria-label="Directions">
      <h2>Directions</h2>
      <ol>
        {items.map((text, idx) => (
          <li key={idx}>{text}</li>
        ))}
      </ol>
      <button type="button" onClick={onClose}>
        Close
      </button>
    </section>
  );
}
