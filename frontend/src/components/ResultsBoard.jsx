import { isLive } from "../lib/pacing.js";
import AnswerPanel from "./AnswerPanel.jsx";
import DeliveryPanel from "./DeliveryPanel.jsx";

// The listings Viktor delivers appear one by one and are marked accepted by Max. They wait until the conversation
// above has finished, so the story reads in order. (The offers themselves build up in the stage band.)
export default function ResultsBoard({ view, paced, live }) {
  const isAnswer = view.delivery?.result?.kind === "general";
  const delivered = isAnswer ? !!view.delivery?.result?.answer : view.delivery?.result?.flats?.length > 0;
  // Fresh = delivered after this page loaded; a reload or an older deal shows the table at once.
  const fresh = live && delivered && isLive(view.delivery.ts ?? 0, Date.now() / 1000, paced.loadedAt);
  return (
    <div className="board">
      <section className="board-results" aria-label="Delivered listings">
        {delivered && !paced.caughtUp
          ? <p className="tab-empty">Viktor is still talking...</p>
          : isAnswer ? <AnswerPanel view={view} animate={fresh} /> : <DeliveryPanel view={view} animate={fresh} />}
      </section>
    </div>
  );
}
