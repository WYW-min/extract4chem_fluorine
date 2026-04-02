from __future__ import annotations

from .params import parse_args
from .service import print_run_summary, run_process_before


def main() -> None:
    print_run_summary(run_process_before(parse_args()))


if __name__ == "__main__":
    main()
