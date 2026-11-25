"""CLI entrypoint for running the OG card service."""

import uvicorn

from og_card_service.config import get_settings


def main() -> None:
    """Run the Uvicorn server using configured host and port."""
    settings = get_settings()
    uvicorn.run(
        "og_card_service.app:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
