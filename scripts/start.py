"""Production startup script.

Runs Alembic migrations then hands the process over to fastapi run via os.execvp,
so fastapi run becomes PID 1 and receives OS signals (SIGTERM, etc.) correctly.

Uses sys.executable instead of bare command names so PATH is never consulted —
this works reliably in minimal/distroless images that strip the environment.
"""

import logging
import os
import subprocess
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Starting database migrations...")
    try:
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            check=True,
        )
        logger.info("Database migrations completed successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Database migrations failed with exit code {e.returncode}.")
        sys.exit(e.returncode)
    except Exception:
        logger.exception("An unexpected error occurred during database migrations.")
        sys.exit(1)

    # Determine the command to run after migrations.
    # If arguments were passed to this script, use them. Otherwise
    # default to production fastapi run.
    args = sys.argv[1:]
    if not args:
        args = [sys.executable, "-m", "fastapi", "run", "--port", "8000"]

    logger.info(f"Starting application: {' '.join(args)}")

    # Flush all standard streams before replacing the process
    # so that our logs actually make it to the Docker console!
    sys.stdout.flush()
    sys.stderr.flush()
    logging.shutdown()

    # os.execvp replaces the current process (PID 1) with the target process.
    # This ensures the application receives OS signals correctly.
    os.execvp(args[0], args)


if __name__ == "__main__":
    main()
