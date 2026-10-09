import Icon from "./Icons.jsx";
import { tada } from "../lib/formatters.js";

// Viktor was paid into escrow but delivered nothing usable (his job failed, or the research found nothing that fits):
// say so plainly instead of leaving an empty board, and say where the money went.
export default function NotDelivered({ view }) {
  const price = view.refund?.price ?? view.agreed;
  return (
    <section className="not-delivered" role="status">
      <p className="not-delivered-title"><Icon name="alert" size={15} /> Nothing was delivered</p>
      <p className="not-delivered-text">
        Viktor could not deliver a result that matches the request, so the escrow went back to Max
        {price != null ? ` (${tada(price)})` : ""}. Try asking for fewer results, or in other words.
      </p>
    </section>
  );
}
