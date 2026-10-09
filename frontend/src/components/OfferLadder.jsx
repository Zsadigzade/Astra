import { tada } from "../lib/formatters.js";

// The negotiation as a row of price points that appear one by one, in step with the chat. New chips fade in
// (they are new DOM nodes); the final chip says what was agreed once the conversation has finished.
export default function OfferLadder({ chat, agreed, caughtUp }) {
  const offers = chat.filter((e) => e.data.price > 0 && e.data.action !== "walk");
  const settled = caughtUp && agreed != null;
  if (offers.length === 0 && !settled) return <p className="ladder-empty">Offers appear here as they are made.</p>;
  return (
    <ol className="ladder" aria-label="Offers so far">
      {offers.map((e) => (
        <li key={e.id} className={`chip-offer chip-${e.data.speaker}`}>
          <span className="chip-who">{e.data.speaker === "max" ? "Max" : "Viktor"}</span>
          <b className="num">{tada(e.data.price, 1)}</b>
        </li>
      ))}
      {settled && (
        <li className="chip-offer chip-agreed" role="status">
          <span className="chip-who">Agreed</span>
          <b className="num">{tada(agreed, 1)}</b>
        </li>
      )}
    </ol>
  );
}
