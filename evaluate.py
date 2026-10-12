"""AegisBench entry point. Default: frozen sources, no network/model/database."""
import sys
from evaluation.bench.runner import main as legacy_main


def main(argv=None):
    arguments=list(sys.argv[1:] if argv is None else argv)
    if '--mode' in arguments or any(x.startswith('--mode=') for x in arguments):
        from evaluation.bench.e2e import main as e2e_main
        return e2e_main(arguments)
    return legacy_main(arguments)

if __name__ == "__main__":
    raise SystemExit(main())
