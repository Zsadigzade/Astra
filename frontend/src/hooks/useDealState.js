import { useMemo } from "react";
import { deriveDealState } from "../lib/eventReducer.js";

export default function useDealState(events, dealId = null) {
  return useMemo(() => deriveDealState(events, dealId), [events, dealId]);
}
