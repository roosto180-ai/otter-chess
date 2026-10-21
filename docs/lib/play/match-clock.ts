/** Monotonic elapsed-time clock; state changes are synchronous, React only displays snapshots. */
export class MatchClock {
  player = 600;
  otter = 600;
  side: 'player' | 'otter' = 'player';
  running = false;
  increment = 0;
  last = 0;
  start(base: number, increment: number, side: 'player' | 'otter', now: number) {
    this.player = this.otter = base;
    this.increment = increment;
    this.side = side;
    this.last = now;
    this.running = true;
  }
  settle(now: number): 'player' | 'otter' | null {
    if (!this.running) return null;
    this[this.side] = Math.max(0, this[this.side] - Math.max(0, now - this.last) / 1000);
    this.last = now;
    if (this[this.side] === 0) {
      this.running = false;
      return this.side;
    }
    return null;
  }
  move(next: 'player' | 'otter', now: number, ignoreFlag = false) {
    const flagged = this.settle(now);
    if (flagged && !ignoreFlag) return flagged;
    if (this.running) this[this.side] += this.increment;
    this.side = next;
    this.last = now;
    return null;
  }
  edit(side: 'player' | 'otter', seconds: number, now: number) {
    if (!Number.isFinite(seconds) || seconds < 0 || seconds > 86400) throw new Error('Time must be between 0 and 86400 seconds');
    const flagged = this.settle(now);
    this[side] = seconds;
    this.last = now;
    return flagged;
  }
}

export function customTimeControl(minutes: number, increment: number): string {
  if (!Number.isFinite(minutes) || minutes < 0.1 || minutes > 1440 || !Number.isInteger(increment) || increment < 0 || increment > 600) {
    throw new Error('Minutes: 0.1–1440; increment: integer 0–600 seconds');
  }
  return `${Math.round(minutes * 60)}+${increment}`;
}
