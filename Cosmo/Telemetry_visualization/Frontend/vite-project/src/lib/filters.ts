export class EMAFilter {
  private last: number | null = null;
  private readonly alpha: number;

  constructor(alpha: number = 0.3) {
    this.alpha = alpha;
  }

  process(value: number): number {
    if (this.last === null) {
      this.last = value;
      return value;
    }
    this.last = this.alpha * value + (1 - this.alpha) * this.last;
    return this.last;
  }

  reset() {
    this.last = null;
  }
}
