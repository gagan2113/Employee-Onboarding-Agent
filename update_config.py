"""
Configuration Update Utility
Easy-to-use script for updating onboarding agent configurations
"""

import json
import sys
from pathlib import Path
from config.config_manager import config_manager

class ConfigUpdater:
    """Simple utility to update configuration files"""
    
    def __init__(self):
        self.config_manager = config_manager
    
    def update_email_addresses(self):
        """Interactive update of email addresses"""
        print("📧 Update Email Addresses")
        print("=" * 40)
        
        current_settings = self.config_manager.get_email_settings()
        
        # Update sender email
        current_sender = current_settings.get("sender_email", "")
        new_sender = input(f"Sender Email [{current_sender}]: ").strip()
        if new_sender:
            self.config_manager.update_email_setting("sender_email", new_sender)
        
        # Update manager email
        current_manager = current_settings.get("manager_escalation_email", "")
        new_manager = input(f"Manager Email [{current_manager}]: ").strip()
        if new_manager:
            self.config_manager.update_email_setting("manager_escalation_email", new_manager)
        
        # Update HR support email
        current_hr = current_settings.get("hr_support_email", "")
        new_hr = input(f"HR Support Email [{current_hr}]: ").strip()
        if new_hr:
            self.config_manager.update_email_setting("hr_support_email", new_hr)
        
        print("✅ Email addresses updated successfully!")
    
    def update_company_info(self):
        """Interactive update of company information"""
        print("🏢 Update Company Information")
        print("=" * 40)
        
        current_info = self.config_manager.get_company_info()
        
        # Update company name
        current_name = current_info.get("name", "")
        new_name = input(f"Company Name [{current_name}]: ").strip()
        if new_name:
            self.config_manager.update_company_info("name", new_name)
        
        # Update mission
        current_mission = current_info.get("mission", "")
        print(f"Current Mission: {current_mission}")
        new_mission = input("New Mission (press Enter to skip): ").strip()
        if new_mission:
            self.config_manager.update_company_info("mission", new_mission)
        
        print("✅ Company information updated successfully!")
    
    def show_current_config(self):
        """Display current configuration summary"""
        print("📊 Current Configuration Summary")
        print("=" * 50)
        
        # Email settings
        email_settings = self.config_manager.get_email_settings()
        print(f"📧 Sender Email: {email_settings.get('sender_email', 'Not set')}")
        print(f"📧 Manager Email: {email_settings.get('manager_escalation_email', 'Not set')}")
        print(f"📧 HR Email: {email_settings.get('hr_support_email', 'Not set')}")
        
        # Company info
        company_info = self.config_manager.get_company_info()
        print(f"🏢 Company: {company_info.get('name', 'Not set')}")
        
        # Policy count
        policies = self.config_manager.get_company_policies()
        print(f"📚 Total Policies: {len(policies)}")
        
        print("=" * 50)
    
    def main_menu(self):
        """Main interactive menu"""
        while True:
            print("\n🤖 Onboarding Agent Configuration Updater")
            print("=" * 50)
            print("1. Update Email Addresses")
            print("2. Update Company Information")
            print("3. Show Current Configuration")
            print("4. Reload All Configurations")
            print("5. Exit")
            print("=" * 50)
            
            choice = input("Select an option (1-5): ").strip()
            
            if choice == "1":
                self.update_email_addresses()
            elif choice == "2":
                self.update_company_info()
            elif choice == "3":
                self.show_current_config()
            elif choice == "4":
                self.config_manager.reload_all_configs()
                print("✅ All configurations reloaded!")
            elif choice == "5":
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid option. Please choose 1-6.")

def main():
    """Main function"""
    try:
        updater = ConfigUpdater()
        
        if len(sys.argv) > 1:
            # Command line mode
            command = sys.argv[1]
            if command == "show":
                updater.show_current_config()
            elif command == "email":
                updater.update_email_addresses()
            elif command == "company":
                updater.update_company_info()
            else:
                print("Available commands: show, email, company")
        else:
            # Interactive mode
            updater.main_menu()
            
    except KeyboardInterrupt:
        print("\n👋 Configuration update cancelled.")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()