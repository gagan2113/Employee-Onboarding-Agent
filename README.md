# Employee Onboarding Agent 🚀

A comprehensive 3-phase Slack-based employee onboarding system built with FastAPI, LangGraph, LangChain, and PostgreSQL.

## 🎯 Project Overview

This Employee Onboarding Agent provides an intelligent, automated onboarding experience through Slack. The system features a **3-phase onboarding workflow** that adapts to each employee's role and ensures complete profile setup, personalized task assignment, and progress monitoring until completion.

## 🏗️ Tech Stack

- **FastAPI**: Backend server and API endpoints
- **LangGraph**: Workflow orchestration and state management  
- **LangChain**: Natural language processing and AI reasoning
- **PostgreSQL**: Database for storing user data and progress
- **Slack Bot API**: Primary interface for user interaction
- **GROQ AI**: LLM integration for intelligent responses
- **SQLAlchemy**: ORM for database operations
- **Python 3.8+**: Core programming language

## ✨ Key Features

### 🎯 3-Phase Onboarding System
**Phase 1: Profile Completeness Check**
- Automatically analyzes Slack profile completeness (0-100% score)
- Identifies missing information (photo, job title, department, etc.)
- Provides step-by-step guidance for profile completion

**Phase 2: Role-Based Task Assignment**  
- Intelligent role detection from job titles
- Personalized task lists for 9+ different roles
- Role-specific setup, training, and meeting tasks
- Estimated time and priority levels for each task

**Phase 3: Progress Monitoring & Completion**
- Real-time task status tracking ("started task 1", "completed task 2")
- Automated reminders with manager escalation
- Comprehensive completion celebration and next steps

### 🤖 Intelligent Assistant Capabilities
- Natural language Q&A for company policies
- Context-aware responses using knowledge base
- Interactive task help with detailed instructions
- Proactive guidance and encouragement

### � Comprehensive Task Management
- 6 task categories: Profile, Training, Setup, Meetings, Compliance
- Priority-based organization with due dates
- Progress visualization and status updates
- Detailed help system with resources and instructions

### 🔧 Advanced Integration Features
- Database-backed user and task persistence
- Background job scheduling for reminders
- Email notifications for managers
- RESTful API for external integrations
- Comprehensive error handling and fallbacks

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- PostgreSQL database
- Slack workspace with bot permissions
- Slack workspace with bot permissions
- Groq API key (from console.groq.com)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd "Employee Onboarding Agent"
python setup.py
```

### 2. Configure Environment

Copy `.env.example` to `.env` and update the following variables:

```env
# Database
DATABASE_URL=postgresql://username:password@localhost:5432/onboarding_db

# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_APP_TOKEN=xapp-your-app-token

# Groq Configuration
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=llama-3.1-70b-versatile


# Security
SECRET_KEY=your-secret-key
```

### 3. Set Up Slack App

1. Create a new Slack app at https://api.slack.com/apps
2. Enable the following bot token scopes:
   - `chat:write`
   - `app_mentions:read`
   - `im:read`
   - `im:write`
   - `users:read`
   - `users.profile:read` (required for profile analysis)
   - `channels:read`
3. Install the app to your workspace
4. Copy the Bot User OAuth Token to `SLACK_BOT_TOKEN`
5. Copy the Signing Secret to `SLACK_SIGNING_SECRET`

### 4. Run the Application

Start the application:
```bash
python main.py
```

The bot will be ready to handle onboarding workflows in your Slack workspace!

## 🎯 3-Phase Onboarding System

### How It Works

1. **New employee says "hello"** to the bot
2. **Phase 1: Profile Check** - Bot analyzes Slack profile completeness
3. **Phase 2: Task Assignment** - Assigns role-specific onboarding tasks  
4. **Phase 3: Progress Monitoring** - Tracks completion until fully onboarded

### Example User Journey

```
👤 New Employee: "Hello"

🤖 Bot: "Hi Sarah! I'm analyzing your profile...
        Your profile is 70% complete. Please add:
        • Profile photo
        • Job title
        • Department
        
        Once updated, say 'profile updated'!"

👤 Sarah: [Updates profile] "profile updated"

🤖 Bot: "Perfect! I've created 6 tasks for your role: AI Engineer
        
        1. Complete Profile Setup 🔴 📝
        2. Read Employee Handbook 🔴 📝  
        3. Development Environment Setup 🔴 📝
        4. AI Tools Training 🟡 📝
        5. Meet with Tech Lead 🔴 📝
        6. Complete Security Training 🔴 📝
        
        Say 'started task 1' to begin!"

👤 Sarah: "started task 1"

🤖 Bot: "🚀 Great! Task 1 is now in progress. You've got this!"

👤 Sarah: "completed task 1"

🤖 Bot: "✅ Excellent! Task 1 marked as completed. Great progress!"

👤 Sarah: [Completes all tasks]

🤖 Bot: "🎉 CONGRATULATIONS! You've completed your onboarding!
        ✅ All mandatory tasks finished
        🚀 You're ready to make an impact!"
```

### Supported Commands

- `"hello"` - Start onboarding process
- `"profile updated"` - Re-check profile after updates
- `"started task X"` - Mark task as in progress
- `"completed task X"` - Mark task as completed
- `"help with task X"` - Get detailed task instructions
- `"show my tasks"` - Display current task list

### Role-Specific Tasks

The system automatically assigns tasks based on job titles:

- **👨‍💻 Software Developer** - Dev environment, code reviews, tech meetings
- **🤖 AI Engineer** - AI tools, ML frameworks, model training
- **👥 HR Associate** - HRIS training, compliance, legal guidelines
- **📊 Product Manager** - Product tools, stakeholder meetings  
- **🎨 Designer** - Design tools, brand guidelines, design system
- **📈 Data Scientist** - Analytics tools, data access, reporting
- **📢 Marketing** - Marketing platforms, brand assets, content tools
- **💼 Sales** - CRM setup, product knowledge, sales training
- **� Other** - General onboarding tasks

## 🔄 Legacy Workflow Documentation

The system guides new employees through a structured onboarding process:

### 1. Welcome & Introduction
- Automatic welcome message when user joins Slack
- Introduction to the onboarding process
- Setting expectations

### 2. Information Collection
- Personal details (name, role, department, location)
- Role-specific requirements
- Manager and buddy assignment

### 3. Policy & Compliance
- Company policies and guidelines
- Role-specific compliance training
- Security protocols

### 4. Tool Setup & Access
- Account provisioning
- Software installation guides
- System access verification

### 5. Culture & Values
- Company mission and values
- Team introductions
- Cultural resources

### 6. Role-Specific Tasks
- Department-specific onboarding
- First-week project assignments
- Learning resources

### 7. Mentor Assignment
- Buddy system setup
- Introduction facilitation
- Ongoing support structure

### 8. Progress Tracking
- Daily check-ins
- Weekly progress reviews
- Milestone celebrations

### 9. Feedback Collection
- Experience evaluation
- Process improvement suggestions
- Satisfaction surveys

### 10. Completion & Celebration
- Onboarding completion certificate
- Transition to regular operations
- 30-day follow-up scheduling

## 🛠️ API Endpoints

### Core Onboarding
- `POST /api/onboarding/start` - Start onboarding for a user
- `GET /api/onboarding/status/{user_id}` - Get onboarding status
- `POST /api/onboarding/message` - Process user messages

### Task Management
- `GET /api/users/{user_id}/tasks` - Get user tasks
- `POST /api/tasks/complete` - Mark task as completed

### Communication
- `POST /api/reminders/send` - Send reminder to user
- `POST /slack/events` - Slack event webhook

### Analytics
- `GET /api/analytics/overview` - Get onboarding analytics

## 🗃️ Database Schema

### Core Models
- **User**: Employee information and onboarding status
- **OnboardingTask**: Individual tasks and assignments
- **OnboardingProgress**: Progress tracking and metrics
- **UserInteraction**: Conversation history and context

### Configuration Models
- **OnboardingTemplate**: Role-specific onboarding templates
- **CompanyPolicy**: Policies and compliance requirements

## 🧪 Testing

Run the test suite:

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

## 🔧 Development

### Project Structure
```
Employee Onboarding Agent/
├── database/
│   ├── models.py          # SQLAlchemy models
│   ├── database.py        # Database configuration
│   └── init_db.py         # Database initialization
├── workflows/
│   ├── state.py           # LangGraph state management
│   ├── nodes.py           # Workflow node implementations
│   └── workflow.py        # Workflow orchestration
├── langchain_components/
│   ├── agent.py           # Main LangChain agent
│   └── tools.py           # Custom tools and utilities
├── slack_integration/
│   └── bot.py             # Slack bot implementation
├── services/
│   ├── background_jobs.py # Background jobs (schedule/threading)
│   ├── tasks.py           # Background tasks
│   └── seed_data.py       # Database seeding
├── tests/
│   ├── test_api.py        # API endpoint tests
│   └── test_workflow.py   # Workflow tests
├── main.py                # FastAPI application
├── config.py              # Configuration management
└── requirements.txt       # Python dependencies
```

### Adding New Features

1. **New Onboarding Steps**: Add to `OnboardingStep` enum and implement in `OnboardingNodes`
2. **Custom Tools**: Extend `langchain_components/tools.py`
3. **Background Tasks**: Add to `services/tasks.py`
4. **API Endpoints**: Extend `main.py`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📈 Monitoring & Analytics

The system provides comprehensive analytics:

- **Completion Rates**: Track onboarding success rates
- **Time Metrics**: Average time to complete onboarding
- **User Feedback**: Satisfaction scores and suggestions
- **Bottleneck Analysis**: Identify common stopping points
- **Resource Utilization**: Track which resources are most helpful

## 🔒 Security Considerations

- All Slack communications are encrypted in transit
- Database credentials are stored securely
- User data is handled according to privacy policies
- API endpoints require proper authentication
- Regular security audits and updates

## 📞 Support

For technical support or questions:

1. Check the documentation and FAQ
2. Review GitHub issues for similar problems
3. Create a new issue with detailed information
4. Contact the development team

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🎉 Acknowledgments

- LangChain community for AI integration patterns
- Slack for excellent API documentation
- FastAPI for the robust web framework
- All contributors who helped improve this system
