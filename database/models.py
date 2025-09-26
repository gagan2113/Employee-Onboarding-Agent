from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database.database import Base

class UserRole(enum.Enum):
    AI_ENGINEER = "ai_engineer"
    HR_ASSOCIATE = "hr_associate"
    SOFTWARE_DEVELOPER = "software_developer"
    PRODUCT_MANAGER = "product_manager"
    DESIGNER = "designer"
    DATA_SCIENTIST = "data_scientist"
    MARKETING = "marketing"
    SALES = "sales"
    OTHER = "other"

class OnboardingStatus(enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAUSED = "paused"
    OVERDUE = "overdue"

class ReminderStatus(enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    ESCALATED = "escalated"

class TaskStatus(enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    SKIPPED = "skipped"

class ProfileCompletionStatus(enum.Enum):
    INCOMPLETE = "incomplete"
    PENDING_REVIEW = "pending_review"
    COMPLETE = "complete"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    slack_user_id = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True)
    full_name = Column(String(255), nullable=False)
    display_name = Column(String(255))
    job_title = Column(String(255))
    phone = Column(String(50))
    profile_image_url = Column(String(500))
    role = Column(Enum(UserRole), nullable=False)
    department = Column(String(100))
    start_date = Column(DateTime(timezone=True))
    onboarding_status = Column(Enum(OnboardingStatus), default=OnboardingStatus.NOT_STARTED)
    # Fields referenced by Slack handler
    manager_email = Column(String(255), default=None)
    onboarding_completed = Column(Boolean, default=False)
    onboarding_completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    interactions = relationship("UserInteraction", back_populates="user")
    progress = relationship("OnboardingProgress", back_populates="user")

class OnboardingProgress(Base):
    __tablename__ = "onboarding_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    current_step = Column(String(100))  # Current onboarding step
    completed_steps = Column(Text)  # JSON array of completed steps
    total_steps = Column(Integer, default=10)
    completion_percentage = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="progress")

class UserInteraction(Base):
    __tablename__ = "user_interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    response = Column(Text)
    interaction_type = Column(String(50))  # "question", "reminder", etc.
    channel_id = Column(String(50))
    thread_ts = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="interactions")

class CompanyPolicy(Base):
    __tablename__ = "company_policies"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50))  # "hr", "security", "code_of_conduct", etc.
    role_specific = Column(String(100))  # Which roles this policy applies to
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class OnboardingTemplate(Base):
    __tablename__ = "onboarding_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    role = Column(Enum(UserRole), nullable=False)
    step_name = Column(String(100), nullable=False)
    step_order = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    resources = Column(Text)  # JSON array of resources/links
    is_mandatory = Column(Boolean, default=True)
    estimated_duration = Column(Integer)  # in minutes
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class OnboardingTask(Base):
    __tablename__ = "onboarding_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_name = Column(String(255), nullable=False)
    task_description = Column(Text)
    task_category = Column(String(100))  # "profile", "training", "setup", etc.
    role_specific = Column(Enum(UserRole))
    priority = Column(Integer, default=1)  # 1=high, 2=medium, 3=low
    due_date = Column(DateTime(timezone=True))
    status = Column(Enum(TaskStatus), default=TaskStatus.NOT_STARTED)
    assigned_date = Column(DateTime(timezone=True), server_default=func.now())
    # Keep existing completed_date for backward compatibility
    completed_date = Column(DateTime(timezone=True))
    # Fields referenced by Slack handler for status timestamps
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    instructions = Column(Text)
    resources = Column(Text)  # JSON array of helpful links/documents
    is_mandatory = Column(Boolean, default=True)
    estimated_minutes = Column(Integer, default=30)
    completion_proof = Column(Text)  # Evidence of completion
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    reminders = relationship("TaskReminder", back_populates="task")

class TaskReminder(Base):
    __tablename__ = "task_reminders"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("onboarding_tasks.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reminder_count = Column(Integer, default=0)
    max_reminders = Column(Integer, default=2)
    last_reminder_sent = Column(DateTime(timezone=True))
    next_reminder_due = Column(DateTime(timezone=True))
    status = Column(Enum(ReminderStatus), default=ReminderStatus.PENDING)
    manager_notified = Column(Boolean, default=False)
    manager_notification_date = Column(DateTime(timezone=True))
    escalation_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    task = relationship("OnboardingTask", back_populates="reminders")
    user = relationship("User")

class UserProfileCheck(Base):
    __tablename__ = "user_profile_checks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    slack_user_id = Column(String(100), nullable=False)
    has_real_name = Column(Boolean, default=False)
    has_display_name = Column(Boolean, default=False)
    has_profile_image = Column(Boolean, default=False)
    has_job_title = Column(Boolean, default=False)
    has_email = Column(Boolean, default=False)  # Added email field
    has_phone = Column(Boolean, default=False)
    has_department = Column(Boolean, default=False)  # Custom field
    has_start_date = Column(Boolean, default=False)  # Custom field
    profile_completion_score = Column(Integer, default=0)  # 0-100%
    missing_fields = Column(Text)  # JSON array of missing fields
    status = Column(Enum(ProfileCompletionStatus), default=ProfileCompletionStatus.INCOMPLETE)
    last_checked = Column(DateTime(timezone=True), server_default=func.now())
    profile_completed_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User")