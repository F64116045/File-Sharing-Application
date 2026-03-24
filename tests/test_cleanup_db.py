import logging

from scripts.cleanup_db import _delete_by_ids, cleanup_expired_shares, cleanup_stale_uploads
from app.models.share import Share


class FakeDB:
    def __init__(self, scalar_batches):
        self.scalar_batches = list(scalar_batches)
        self.execute_calls = 0
        self.commit_calls = 0

    def scalars(self, _stmt):
        if not self.scalar_batches:
            return []
        return self.scalar_batches.pop(0)

    def execute(self, _stmt):
        self.execute_calls += 1

    def commit(self):
        self.commit_calls += 1


def test_delete_by_ids_dry_run_does_not_execute_or_commit():
    db = FakeDB([])

    deleted = _delete_by_ids(db, Share, [1, 2, 3], execute=False)

    assert deleted == 3
    assert db.execute_calls == 0
    assert db.commit_calls == 0


def test_cleanup_expired_shares_dry_run_counts_rows_only():
    db = FakeDB([["s1", "s2"], []])
    logger = logging.getLogger("test_cleanup")

    deleted = cleanup_expired_shares(
        db=db,
        execute=False,
        batch_size=500,
        max_batches=0,
        grace_hours=0,
        logger=logger,
    )

    assert deleted == 2
    assert db.execute_calls == 0
    assert db.commit_calls == 0


def test_cleanup_stale_uploads_execute_respects_max_batches():
    db = FakeDB([["f1"], ["f2"], []])
    logger = logging.getLogger("test_cleanup")

    deleted = cleanup_stale_uploads(
        db=db,
        execute=True,
        batch_size=500,
        max_batches=1,
        stale_hours=24,
        logger=logger,
    )

    assert deleted == 1
    assert db.execute_calls == 1
    assert db.commit_calls == 1
