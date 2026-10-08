import { useMemo } from "react";
import { deriveDealState } from "../lib/eventReducer.js";

export default function useDealState(events) {
  return useMemo(() => deriveDealState(events), [events]);
}
