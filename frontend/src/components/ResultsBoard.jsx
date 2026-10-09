import { isLive } from "../lib/pacing.js";
import DeliveryPanel from "./DeliveryPanel.jsx";
import OfferLadder from "./OfferLadder.jsx";

// The main board: the offers as they are made, then the listings Viktor delivers appearing one by one and being
// marked accepted by Max. The listings wait until the conversation has finished, so the story reads in order.
export default function ResultsBoard({ view, paced, live }) {
  const delivered = view.delivery?.result?.flats?.length > 0;
  // Fresh = delivered after this page loaded; a reload or an older deal shows the table at once.
  const fresh = live && delivered && isLive(view.delivery.ts ?? 0, Date.now() / 1000, paced.loadedAt);
  return (
    <div className="board">
      <section className="board-offers" aria-label="Negotiation offers">
        <OfferLadder chat={paced.chat} agreed={view.agreed} caughtUp={paced.caughtUp} />
      </section>
      <section className="board-results" aria-label="Delivered listings">
        {delivered && !paced.caughtUp
          ? <p className="tab-empty">Viktor is still talking...</p>
          : <DeliveryPanel view={view} animate={fresh} />}
      </section>
    </div>
  );
}
