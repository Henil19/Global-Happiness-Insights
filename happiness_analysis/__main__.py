from pathlib import Path

from .analysis import run_analysis

if __name__ == "__main__":
    result = run_analysis(Path(__file__).resolve().parents[1])
    print(f"Analysis complete: {result['outdir']}")
    print(f"Countries={len(result['ranked'])}; score gap={result['score_gap']:.3f}")
