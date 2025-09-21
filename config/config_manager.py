"""
Configuration Manager for Employee Onboarding Agent
Centralizes loading and management of all configuration files
"""

import json
import os
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigurationManager:
    """Manages all configuration files for the onboarding agent"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._email_config = None
        self._policies_config = None
        self._notification_config = None
        
        # Ensure config directory exists
        self.config_dir.mkdir(exist_ok=True)
        
    def _load_json_config(self, filename: str) -> Dict[str, Any]:
        """Load a JSON configuration file"""
        try:
            config_path = self.config_dir / filename
            if not config_path.exists():
                logger.warning(f"Configuration file {filename} not found at {config_path}")
                return {}
                
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading configuration file {filename}: {str(e)}")
            return {}
    
    def reload_all_configs(self):
        """Reload all configuration files"""
        self._email_config = None
        self._policies_config = None
        self._notification_config = None
        logger.info("All configurations reloaded")
    
    # Email Configuration
    @property
    def email_config(self) -> Dict[str, Any]:
        """Get email configuration"""
        if self._email_config is None:
            self._email_config = self._load_json_config("email_config.json")
        return self._email_config
    
    def get_email_settings(self) -> Dict[str, str]:
        """Get email settings"""
        return self.email_config.get("email_settings", {})
    
    def get_email_template(self, template_name: str) -> Dict[str, str]:
        """Get specific email template"""
        templates = self.email_config.get("email_templates", {})
        return templates.get(template_name, {})
    
    def get_sender_email(self) -> str:
        """Get sender email address"""
        return self.get_email_settings().get("sender_email", "noreply@company.com")
    
    def get_manager_email(self) -> str:
        """Get manager escalation email"""
        return self.get_email_settings().get("manager_escalation_email", "manager@company.com")
    
    # Policies Configuration
    @property
    def policies_config(self) -> Dict[str, Any]:
        """Get policies configuration"""
        if self._policies_config is None:
            self._policies_config = self._load_json_config("policies_config.json")
        return self._policies_config
    
    def get_company_policies(self) -> Dict[str, Any]:
        """Get all company policies"""
        return self.policies_config.get("company_policies", {})
    
    def get_policy(self, policy_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific policy"""
        policies = self.get_company_policies()
        return policies.get(policy_name)
    
    def get_company_info(self) -> Dict[str, Any]:
        """Get company information"""
        return self.policies_config.get("company_information", {})
    
    def get_faqs(self) -> Dict[str, Any]:
        """Get frequently asked questions"""
        return self.policies_config.get("faqs", {})
    
    def search_policies(self, query: str) -> List[Dict[str, Any]]:
        """Search policies by keyword"""
        query_lower = query.lower()
        matching_policies = []
        
        for policy_name, policy_data in self.get_company_policies().items():
            if (query_lower in policy_name.lower() or 
                query_lower in policy_data.get("title", "").lower() or
                query_lower in policy_data.get("content", "").lower()):
                matching_policies.append({
                    "name": policy_name,
                    **policy_data
                })
        
        return matching_policies
    
    # Notification Configuration
    @property
    def notification_config(self) -> Dict[str, Any]:
        """Get notification configuration"""
        if self._notification_config is None:
            self._notification_config = self._load_json_config("notification_config.json")
        return self._notification_config
    
    def get_reminder_settings(self) -> Dict[str, int]:
        """Get reminder timing settings"""
        return self.notification_config.get("reminder_settings", {})
    
    def get_escalation_rules(self) -> Dict[str, Any]:
        """Get escalation rules by priority"""
        return self.notification_config.get("escalation_rules", {})
    
    def get_slack_template(self, template_name: str) -> str:
        """Get Slack message template"""
        templates = self.notification_config.get("slack_message_templates", {})
        return templates.get(template_name, "")
    
    def get_ai_response_template(self, template_name: str) -> str:
        """Get AI response template"""
        templates = self.notification_config.get("ai_response_templates", {})
        return templates.get(template_name, "")
    
    # Utility Methods
    def update_email_setting(self, key: str, value: str):
        """Update a specific email setting"""
        if "email_settings" not in self.email_config:
            self.email_config["email_settings"] = {}
        
        self.email_config["email_settings"][key] = value
        self._save_email_config()
    
    def _save_email_config(self):
        """Save email configuration back to file"""
        try:
            config_path = self.config_dir / "email_config.json"
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.email_config, f, indent=2, ensure_ascii=False)
            logger.info("Email configuration saved")
        except Exception as e:
            logger.error(f"Error saving email configuration: {str(e)}")
    
    def add_custom_task(self, task_data: Dict[str, Any]):
        """Add a custom task template"""
        tasks = self.get_default_tasks()
        
        # Generate new ID
        max_id = max([task.get("id", 0) for task in tasks], default=0)
        task_data["id"] = max_id + 1
        
        tasks.append(task_data)
        self._save_task_config()
    
    def _save_task_config(self):
        """Save task configuration back to file"""
        try:
            config_path = self.config_dir / "task_config.json"
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.task_config, f, indent=2, ensure_ascii=False)
            logger.info("Task configuration saved")
        except Exception as e:
            logger.error(f"Error saving task configuration: {str(e)}")
    
    def update_company_info(self, key: str, value: Any):
        """Update company information"""
        if "company_information" not in self.policies_config:
            self.policies_config["company_information"] = {}
        
        self.policies_config["company_information"][key] = value
        self._save_policies_config()
    
    def _save_policies_config(self):
        """Save policies configuration back to file"""
        try:
            config_path = self.config_dir / "policies_config.json"
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.policies_config, f, indent=2, ensure_ascii=False)
            logger.info("Policies configuration saved")
        except Exception as e:
            logger.error(f"Error saving policies configuration: {str(e)}")

# Global configuration manager instance
config_manager = ConfigurationManager()

# Convenience functions for easy access
def get_email_settings():
    """Get email settings"""
    return config_manager.get_email_settings()

def get_company_policies():
    """Get all company policies"""
    return config_manager.get_company_policies()

def get_slack_template(template_name: str):
    """Get Slack message template"""
    return config_manager.get_slack_template(template_name)

def reload_configs():
    """Reload all configuration files"""
    config_manager.reload_all_configs()