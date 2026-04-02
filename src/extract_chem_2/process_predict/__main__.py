from __future__ import annotations

from .params import parse_args
from .service import main_async, print_run_summary


def main() -> None:
    print_run_summary(main_async(parse_args()))


if __name__ == "__main__":
    main()
