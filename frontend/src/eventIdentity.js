// Ledger IDs restart after a demo reset; timestamps and deal IDs distinguish runs.
export const eventKey = (event) => JSON.stringify([event.id, event.ts, event.deal_id]);

export function appendEvent(events, incoming) {
  const key = eventKey(incoming);
  return events.some((event) => eventKey(event) === key) ? events : [...events, incoming];
}
