# 🛠️ Configuration Management Guide

This guide explains how to easily customize your Employee Onboarding Agent using the separate configuration files.

## 📁 Configuration Files Overview

Your agent now uses **4 separate configuration files** for easy customization:

| File | Purpose | What You Can Change |
|------|---------|-------------------|
| `config/email_config.json` | Email settings and templates | Email addresses, HTML templates, subject lines |
| `config/task_config.json` | Task templates and assignments | Onboarding tasks, deadlines, instructions |
| `config/policies_config.json` | Company policies and information | HR policies, company info, FAQs |
| `config/notification_config.json` | Message templates and timing | Slack messages, reminder schedules |

---

## 🚀 Quick Start - 3 Ways to Update

### Method 1: Interactive Configuration Tool (Easiest)
```bash
python update_config.py
```
Follow the menu to update email addresses, company info, and add custom tasks.

### Method 2: Direct File Editing
Open any configuration file in a text editor and make changes. Save and restart the agent.

### Method 3: Command Line Updates
```bash
python update_config.py email    # Update email addresses
python update_config.py company  # Update company info
python update_config.py task     # Add custom task
python update_config.py show     # Show current settings
```

---

## 📧 Email Configuration

### File: `config/email_config.json`

**To change email addresses:**
```json
{
  "email_settings": {
    "sender_email": "hr@yourcompany.com",           // Your HR email
    "manager_escalation_email": "manager@yourcompany.com",  // Manager's email
    "hr_support_email": "support@yourcompany.com"   // Support email
  }
}
```

**To customize email templates:**
- Edit the `html_template` sections for different email types
- Change subject lines in the `subject` fields
- Use variables like `{employee_name}`, `{task_title}`, `{company_name}`

---

## 📋 Task Configuration

### File: `config/task_config.json`

**To add a new task:**
```json
{
  "id": 8,
  "title": "Your New Task",
  "description": "Description of what needs to be done",
  "priority": "high",
  "deadline_days": 3,
  "instructions": "Step-by-step instructions"
}
```

**To modify existing tasks:**
- Change `title`, `description`, `deadline_days`
- Update `priority`: "critical", "high", "medium", "low"
- Modify `instructions` and `success_criteria`

**To add role-specific tasks:**
```json
"role_specific_tasks": {
  "your_role": [
    {
      "title": "Role-Specific Task",
      "description": "Task for specific role",
      "priority": "high",
      "deadline_days": 2
    }
  ]
}
```

---

## 📚 Policies Configuration

### File: `config/policies_config.json`

**To update company information:**
```json
"company_information": {
  "name": "Your Company Name",
  "mission": "Your company mission statement",
  "values": [
    "Your core values here"
  ]
}
```

**To add/modify policies:**
```json
"company_policies": {
  "your_policy": {
    "title": "Policy Title",
    "content": "Policy content here",
    "category": "policy_category",
    "last_updated": "2025-01-20"
  }
}
```

**To add FAQs:**
```json
"faqs": {
  "new_question": {
    "question": "What is...?",
    "answer": "The answer is..."
  }
}
```

---

## 💬 Notification Configuration

### File: `config/notification_config.json`

**To change reminder timing:**
```json
"reminder_settings": {
  "first_reminder_delay_days": 1,    // Days before first reminder
  "second_reminder_delay_days": 3,   // Days before second reminder
  "manager_escalation_delay_days": 7 // Days before manager notification
}
```

**To customize Slack messages:**
```json
"slack_message_templates": {
  "welcome_dm": "👋 Hello {employee_name}! Your custom welcome message...",
  "task_reminder": "⏰ Custom reminder message for {task_title}..."
}
```

---

## 🔄 Applying Changes

After making any changes:

1. **Save the configuration file**
2. **Restart your agent:**
   ```bash
   # Stop current process (Ctrl+C)
   python main.py
   ```

**OR** reload configurations without restart:
```python
from config.config_manager import config_manager
config_manager.reload_all_configs()
```

---

## 🎯 Common Customizations

### Change All Email Addresses
1. Run: `python update_config.py email`
2. Enter new email addresses when prompted

### Update Company Name Everywhere
1. Edit `config/policies_config.json`
2. Change `company_information.name`
3. Restart the agent

### Add Department-Specific Tasks
1. Edit `config/task_config.json`
2. Add tasks under appropriate role in `role_specific_tasks`
3. Restart the agent

### Customize Welcome Messages
1. Edit `config/notification_config.json`
2. Modify `slack_message_templates.welcome_dm`
3. Restart the agent

### Change Reminder Frequency
1. Edit `config/notification_config.json`
2. Modify values in `reminder_settings`
3. Restart the agent

---

## 🔧 Environment Variables

Don't forget to update your `.env` file for:
- SMTP settings (for email sending)
- Slack tokens
- Database connection
- GROQ API key

---

## ✨ Benefits of This Setup

- ✅ **Easy Updates**: Change settings without touching code
- ✅ **No Downtime**: Quick configuration reloads
- ✅ **Backup Friendly**: JSON files are easy to backup and version control
- ✅ **Team Collaboration**: Non-developers can update policies and tasks
- ✅ **Rollback Support**: Easy to revert changes

---

## 🆘 Need Help?

- **View current settings**: `python update_config.py show`
- **Validate JSON**: Use an online JSON validator if you get errors
- **Backup first**: Always backup configuration files before major changes
- **Test changes**: Use a test environment before production updates

---

**Your Employee Onboarding Agent is now fully customizable! 🎉**