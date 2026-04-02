from __future__ import annotations

from .params import parse_args
from .service import print_run_summary, run_doc_split


def main() -> None:
    print_run_summary(run_doc_split(parse_args()))


if __name__ == "__main__":
    main()

