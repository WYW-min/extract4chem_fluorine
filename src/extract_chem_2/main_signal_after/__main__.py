from __future__ import annotations

from .params import parse_args
from .service import print_run_summary, run_main_signal_after


def main() -> None:
    print_run_summary(run_main_signal_after(parse_args()))


if __name__ == '__main__':
    main()
