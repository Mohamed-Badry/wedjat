import sys
from alembic.config import Config
from alembic import command
import alembic.util.exc
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("safe_migrate")

def main():
    alembic_cfg = Config("alembic.ini")
    try:
        command.upgrade(alembic_cfg, "head")
        logger.info("Successfully ran database migrations.")
    except alembic.util.exc.CommandError as e:
        if "Can't locate revision identified by" in str(e):
            print(
                f"\n--- SAFE MIGRATE WARNING ---\n"
                f"Database is ahead of current branch's migrations.\n"
                f"Ignoring missing revision error: {e}\n"
                f"----------------------------\n"
            )
        else:
            print(f"Alembic upgrade failed: {e}")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
