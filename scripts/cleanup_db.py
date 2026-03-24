import argparse
import datetime as dt
import logging
from pathlib import Path
import sys
from typing import Iterable

from sqlalchemy import create_engine
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

# Allow direct execution via `python scripts/cleanup_db.py`.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.core.logging import setup_logging
from app.models.file import File
from app.models.share import Share


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cleanup expired shares and stale uploads from DB")
    parser.add_argument(
        "--database-url",
        type=str,
        default=settings.database_url,
        help="SQLAlchemy database URL. Defaults to app settings.",
    )
    parser.add_argument("--execute", action="store_true", help="Apply deletions. Default is dry-run.")
    parser.add_argument("--batch-size", type=int, default=500, help="Rows per batch (default: 500)")
    parser.add_argument(
        "--expired-share-grace-hours",
        type=int,
        default=0,
        help="Only delete shares expired before now - grace (default: 0)",
    )
    parser.add_argument(
        "--stale-upload-hours",
        type=int,
        default=24,
        help="Delete files where is_uploaded=false and created_at older than N hours (default: 24)",
    )
    parser.add_argument("--max-batches", type=int, default=0, help="Stop after N batches per task (0 means unlimited)")
    return parser.parse_args()


def _should_stop(batch_no: int, max_batches: int) -> bool:
    return max_batches > 0 and batch_no >= max_batches


def _delete_by_ids(db, model, ids: Iterable, execute: bool) -> int:
    id_list = list(ids)
    if not id_list:
        return 0
    if execute:
        db.execute(delete(model).where(model.id.in_(id_list)))
        db.commit()
    return len(id_list)


def cleanup_expired_shares(
    db,
    execute: bool,
    batch_size: int,
    max_batches: int,
    grace_hours: int,
    logger: logging.Logger,
) -> int:
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=grace_hours)
    total = 0
    batch_no = 0

    while True:
        if _should_stop(batch_no, max_batches):
            logger.info("stop shares cleanup due to max-batches=%s", max_batches)
            break

        ids = list(
            db.scalars(
                select(Share.id)
                .where(Share.expires_at < cutoff)
                .order_by(Share.expires_at)
                .limit(batch_size)
            )
        )
        if not ids:
            break

        batch_no += 1
        deleted = _delete_by_ids(db, Share, ids, execute)
        total += deleted
        logger.info(
            "shares cleanup batch=%s rows=%s execute=%s cutoff=%s",
            batch_no,
            deleted,
            execute,
            cutoff.isoformat(),
        )

    return total


def cleanup_stale_uploads(
    db,
    execute: bool,
    batch_size: int,
    max_batches: int,
    stale_hours: int,
    logger: logging.Logger,
) -> int:
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=stale_hours)
    total = 0
    batch_no = 0

    while True:
        if _should_stop(batch_no, max_batches):
            logger.info("stop stale uploads cleanup due to max-batches=%s", max_batches)
            break

        ids = list(
            db.scalars(
                select(File.id)
                .where(File.is_uploaded.is_(False), File.created_at < cutoff)
                .order_by(File.created_at)
                .limit(batch_size)
            )
        )
        if not ids:
            break

        batch_no += 1
        deleted = _delete_by_ids(db, File, ids, execute)
        total += deleted
        logger.info(
            "stale uploads cleanup batch=%s rows=%s execute=%s cutoff=%s",
            batch_no,
            deleted,
            execute,
            cutoff.isoformat(),
        )

    return total


def main() -> int:
    args = parse_args()
    setup_logging()
    logger = logging.getLogger("cleanup_db")

    mode = "EXECUTE" if args.execute else "DRY-RUN"
    logger.info(
        "start cleanup mode=%s batch_size=%s expired_share_grace_hours=%s stale_upload_hours=%s max_batches=%s",
        mode,
        args.batch_size,
        args.expired_share_grace_hours,
        args.stale_upload_hours,
        args.max_batches,
    )

    engine = create_engine(args.database_url, future=True)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    db = session_local()
    try:
        deleted_shares = cleanup_expired_shares(
            db=db,
            execute=args.execute,
            batch_size=args.batch_size,
            max_batches=args.max_batches,
            grace_hours=args.expired_share_grace_hours,
            logger=logger,
        )
        deleted_files = cleanup_stale_uploads(
            db=db,
            execute=args.execute,
            batch_size=args.batch_size,
            max_batches=args.max_batches,
            stale_hours=args.stale_upload_hours,
            logger=logger,
        )

        logger.info(
            "cleanup completed mode=%s deleted_shares=%s deleted_stale_files=%s",
            mode,
            deleted_shares,
            deleted_files,
        )
        return 0
    except SQLAlchemyError:
        db.rollback()
        logger.exception("cleanup failed due to database error")
        return 1
    except Exception:
        db.rollback()
        logger.exception("cleanup failed due to unexpected error")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
