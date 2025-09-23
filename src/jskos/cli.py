"""Command line interface for :mod:`jskos`."""

import click

__all__ = [
    "main",
]


@click.command()
def main() -> None:
    """CLI for JSKOS."""


if __name__ == "__main__":
    main()
