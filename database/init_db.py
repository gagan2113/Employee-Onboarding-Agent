from database.database import Base, engine
from database.models import *

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def migrate_sqlite_columns():
    """SQLite-safe one-off ALTERs to add newly referenced columns if missing."""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            # users.manager_email
            conn.execute(text("ALTER TABLE users ADD COLUMN manager_email VARCHAR(255) DEFAULT ''"))
        except Exception:
            pass
        try:
            # users.onboarding_completed
            conn.execute(text("ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN DEFAULT 0"))
        except Exception:
            pass
        try:
            # users.onboarding_completed_at
            conn.execute(text("ALTER TABLE users ADD COLUMN onboarding_completed_at DATETIME"))
        except Exception:
            pass
        try:
            # onboarding_tasks.started_at
            conn.execute(text("ALTER TABLE onboarding_tasks ADD COLUMN started_at DATETIME"))
        except Exception:
            pass
        try:
            # onboarding_tasks.completed_at
            conn.execute(text("ALTER TABLE onboarding_tasks ADD COLUMN completed_at DATETIME"))
        except Exception:
            pass
        conn.commit()

if __name__ == "__main__":
    create_tables()
    migrate_sqlite_columns()
    print("Database tables created successfully!")
