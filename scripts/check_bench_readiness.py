"""Entry point for offline human-gold readiness, not an experiment runner."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from evaluation.bench.readiness import main

if __name__=='__main__':
    raise SystemExit(main())
