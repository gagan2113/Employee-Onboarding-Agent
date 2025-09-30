import os
from datetime import datetime, timedelta
from pathlib import Path

import sys
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest

# Ensure the application uses a throwaway SQLite database for tests
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_onboarding.db")
os.environ.setdefault("SLACK_BOT_TOKEN", "")
os.environ.setdefault("SLACK_SIGNING_SECRET", "")
os.environ.setdefault("SLACK_APP_TOKEN", "")

from database.database import Base, engine, SessionLocal  # noqa: E402
from database import models  # noqa: E402
from slack_bot_handler import SlackBotHandler  # noqa: E402


@pytest.fixture(autouse=True)
def reset_database():
    """Reset the SQLite database before and after each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield

    Base.metadata.drop_all(bind=engine)


def _seed_user_with_legacy_task(session):
    user = models.User(
        slack_user_id="U_TEST",
        email="user@example.com",
        full_name="Test User",
        role=models.UserRole.SOFTWARE_DEVELOPER,
        job_title="Software Engineer",
        onboarding_status=models.OnboardingStatus.IN_PROGRESS,
    )
    session.add(user)
    session.commit()

    legacy_task = models.OnboardingTask(
        user_id=user.id,
        task_name="Legacy Task",
        task_description="Old task that should be replaced",
        task_category="legacy",
        role_specific=models.UserRole.SOFTWARE_DEVELOPER,
        priority=1,
        due_date=datetime.utcnow() + timedelta(days=3),
        status=models.TaskStatus.NOT_STARTED,
    )
    session.add(legacy_task)
    session.commit()

    reminder = models.TaskReminder(
        task_id=legacy_task.id,
        user_id=user.id,
        reminder_count=1,
        status=models.ReminderStatus.PENDING,
    )
    session.add(reminder)
    session.commit()

    return user.id, user.slack_user_id


def test_assign_role_based_tasks_removes_legacy_reminders():
    handler = SlackBotHandler()

    with SessionLocal() as session:
        user_id, slack_user_id = _seed_user_with_legacy_task(session)

    # Should succeed without raising IntegrityError
    assert handler._assign_role_based_tasks(slack_user_id, "Software Engineer")

    with SessionLocal() as session:
        legacy_tasks = (
            session.query(models.OnboardingTask)
            .filter(models.OnboardingTask.task_name == "Legacy Task")
            .count()
        )
        assert legacy_tasks == 0

        tasks = session.query(models.OnboardingTask).filter_by(user_id=user_id).all()
        task_ids = {task.id for task in tasks}
        assert len(tasks) > 0

        reminders = session.query(models.TaskReminder).filter_by(user_id=user_id).all()
        assert len(reminders) == len(tasks)
        assert {rem.task_id for rem in reminders} == task_ids


def test_raw_sql_assignment_handles_reminders():
    handler = SlackBotHandler()
    tasks_payload = handler._get_role_specific_tasks(models.UserRole.SOFTWARE_DEVELOPER)

    with SessionLocal() as session:
        user_id, _ = _seed_user_with_legacy_task(session)

        # Run the raw SQL fallback directly
        handler._assign_tasks_raw_sql(
            user_id=user_id,
            tasks=tasks_payload,
            role=models.UserRole.SOFTWARE_DEVELOPER,
            db=session,
        )

        session.expire_all()
        remaining_tasks = (
            session.query(models.OnboardingTask)
            .filter_by(user_id=user_id)
            .order_by(models.OnboardingTask.priority)
            .all()
        )
        assert len(remaining_tasks) == len(tasks_payload)
        assert all(task.task_name != "Legacy Task" for task in remaining_tasks)

    with SessionLocal() as verify_session:
        remaining_reminders = (
            verify_session.query(models.TaskReminder)
            .filter_by(user_id=user_id)
            .count()
        )
        assert remaining_reminders == 0