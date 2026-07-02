/**
 * Shared statistical computations for data visualization and analysis.
 */

export function mean(arr: number[]): number {
    if (arr.length === 0) return 0;
    return arr.reduce((a, b) => a + b, 0) / arr.length;
}

export function standardDeviation(arr: number[], avg?: number): number {
    if (arr.length === 0) return 0;
    const m = avg !== undefined ? avg : mean(arr);
    const variance = arr.reduce((a, b) => a + (b - m) ** 2, 0) / arr.length;
    return Math.sqrt(variance);
}

export function median(arr: number[]): number {
    if (arr.length === 0) return 0;
    const sorted = [...arr].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    if (sorted.length % 2 === 0) {
        return (sorted[mid - 1] + sorted[mid]) / 2;
    }
    return sorted[mid];
}

export function pearsonCorrelation(xs: number[], ys: number[]): number {
    if (xs.length === 0 || xs.length !== ys.length) return 0;
    const n = xs.length;
    const mx = mean(xs);
    const my = mean(ys);

    let num = 0;
    let dx2 = 0;
    let dy2 = 0;

    for (let i = 0; i < n; i++) {
        const dx = xs[i] - mx;
        const dy = ys[i] - my;
        num += dx * dy;
        dx2 += dx * dx;
        dy2 += dy * dy;
    }

    const denom = Math.sqrt(dx2 * dy2);
    if (denom === 0) return 0;
    return num / denom;
}
