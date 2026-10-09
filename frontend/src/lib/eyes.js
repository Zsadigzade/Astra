// Where a ghost's pupils (and head) point when it watches the cursor. Pure maths so it is testable.
export const MAX_X = 2.6; // pupil travel inside the eye, in SVG units (the eye is 13 wide)
export const MAX_Y = 3.2;
export const MAX_TILT = 4; // degrees of head turn
export const FULL_AT = 160; // px from the ghost at which the eyes reach full travel

// rect: the ghost's bounding box; pointer: {x, y} in the same (viewport) coordinates.
export function eyeTarget(rect, pointer) {
  const finite = [rect?.left, rect?.top, rect?.width, rect?.height, pointer?.x, pointer?.y].every(Number.isFinite);
  if (!finite) return { x: 0, y: 0, tilt: 0 };
  const cx = rect.left + rect.width / 2;
  const cy = rect.top + rect.height * 0.46; // eyes sit a little above the middle
  const dx = pointer.x - cx;
  const dy = pointer.y - cy;
  const dist = Math.hypot(dx, dy);
  if (dist < 1) return { x: 0, y: 0, tilt: 0 };
  const k = Math.min(1, dist / FULL_AT);
  const round = (n) => Math.round(n * 100) / 100;
  return { x: round((dx / dist) * k * MAX_X), y: round((dy / dist) * k * MAX_Y), tilt: round((dx / dist) * k * MAX_TILT) };
}
