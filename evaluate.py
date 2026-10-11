"""AegisBench entry point. Default: frozen sources, no network/model/database."""
from evaluation.bench.runner import main

if __name__ == "__main__":
    raise SystemExit(main())
