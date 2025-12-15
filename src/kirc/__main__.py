"""Entry point for K-IRC application."""

from kirc.app import KircApp


def main() -> None:
    """Run the K-IRC application."""
    app = KircApp()
    app.run()


if __name__ == "__main__":
    main()
