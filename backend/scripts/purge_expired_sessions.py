import argparse
import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.scheme_data.models import ConversationSession


def purge_expired_sessions(retention_days: int | None = None, dry_run: bool = False) -> int:
    days = retention_days if retention_days is not None else settings.SESSION_RETENTION_DAYS
    cutoff = datetime.utcnow() - timedelta(days=days)
    db = SessionLocal()
    try:
        query = db.query(ConversationSession).filter(ConversationSession.updated_at < cutoff)
        count = query.count()
        if not dry_run and count > 0:
            query.delete(synchronize_session=False)
            db.commit()
        return count
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Purge expired anonymous citizen conversation sessions.")
    parser.add_argument("--days", type=int, default=None, help="Override retention window in days.")
    parser.add_argument("--dry-run", action="store_true", help="Report matching rows without deleting.")
    args = parser.parse_args()

    removed = purge_expired_sessions(retention_days=args.days, dry_run=args.dry_run)
    prefix = "[DRY RUN] Would delete" if args.dry_run else "Deleted"
    print(f"{prefix} {removed} expired conversation session(s).")
