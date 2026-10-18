/** Timestamp matching only: no timers, interpolation, or incident mutations. */
export type MetadataTimestamp = {pts_ns: number};
export type ReplaySyncOptions = {
  /** Maximum permitted distance from an actual metadata timestamp. */
  toleranceNs: number;
  /** Verified metadata PTS minus video media time. null means unverified. */
  ptsOffsetNs: number | null;
};

/** Validate once when loading a timeline; keep it immutable thereafter. */
export function validMetadataTimeline(frames: readonly MetadataTimestamp[]): boolean {
  let previous = -Infinity;
  return frames.every(frame => {
    const current = frame.pts_ns;
    const valid = Number.isFinite(current) && current >= 0 && current > previous;
    previous = current;
    return valid;
  });
}

/**
 * O(log n) lookup in a validated, strictly increasing immutable PTS timeline.
 * Offset must come from verified media/container timing, never first metadata PTS.
 * Exact midpoint ties choose the earlier actual observation. Out-of-tolerance
 * playback is unmatched, including missing frames and unobserved clip boundaries.
 */
export function nearestMetadataFrame<T extends MetadataTimestamp>(
  frames: readonly T[], videoTimeSeconds: number, options: ReplaySyncOptions,
): T | null {
  const {toleranceNs, ptsOffsetNs} = options;
  if (ptsOffsetNs === null || !Number.isFinite(ptsOffsetNs) ||
      !Number.isFinite(videoTimeSeconds) || videoTimeSeconds < 0 ||
      !Number.isFinite(toleranceNs) || toleranceNs < 0 || !frames.length) return null;
  const target = videoTimeSeconds * 1e9 + ptsOffsetNs;
  if (!Number.isFinite(target) || target < 0) return null;
  let low = 0;
  let high = frames.length;
  while (low < high) {
    const middle = low + Math.floor((high - low) / 2);
    const pts = frames[middle].pts_ns;
    if (!Number.isFinite(pts) || pts < 0) return null;
    if (pts < target) low = middle + 1;
    else high = middle;
  }
  const before = low > 0 ? frames[low - 1] : undefined;
  const after = frames[low];
  const candidate = !before ? after : !after ? before :
    target - before.pts_ns <= after.pts_ns - target ? before : after;
  if (!candidate || !Number.isFinite(candidate.pts_ns) || candidate.pts_ns < 0) return null;
  return Math.abs(candidate.pts_ns - target) <= toleranceNs ? candidate : null;
}
