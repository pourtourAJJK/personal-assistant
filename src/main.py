"""main.py — Program entry point (AD-1, FR-7).

Contract (ARCHITECTURE-SPINE.md Rev-2 / Interface Contracts):
    main() -> None    # calls cli.run() and nothing else

This module contains no business logic, no initialization, and imports
nothing from this project except cli (AD-1: main.py imports cli.py only).
First-run directory creation is handled lazily by storage on first save;
exit is a plain return from the menu loop (FR-8, AD-4 guarantees nothing
unsaved).
"""

import cli


def main() -> None:
    cli.run()


if __name__ == "__main__":
    main()
