#!/usr/bin/env python3
"""
Migration script: JWT to API Key Authentication
This script helps migrate from the old JWT system to the new API key system.
"""

import os
import json
import shutil
from datetime import datetime

def backup_old_files():
    """Create backup of old authentication files"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backup_jwt_{timestamp}"
    
    print(f"📦 Creating backup directory: {backup_dir}")
    os.makedirs(backup_dir, exist_ok=True)
    
    # Files to backup
    files_to_backup = [
        "frontend/src/services/unifiedClient.js",
        "backend/simple_server.py"
    ]
    
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            backup_path = os.path.join(backup_dir, file_path)
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            shutil.copy2(file_path, backup_path)
            print(f"   ✅ Backed up: {file_path}")
        else:
            print(f"   ⚠️  File not found: {file_path}")
    
    return backup_dir

def clear_old_jwt_data():
    """Clear old JWT data from localStorage (frontend)"""
    print("\n🧹 Clearing old JWT data...")
    
    # Create a simple HTML file to clear localStorage
    clear_script = """
<!DOCTYPE html>
<html>
<head>
    <title>Clear JWT Data</title>
</head>
<body>
    <h2>Clearing Old JWT Data</h2>
    <div id="status">Processing...</div>
    
    <script>
        try {
            // Clear old JWT token
            if (localStorage.getItem('pi-monitor-token')) {
                localStorage.removeItem('pi-monitor-token');
                console.log('Old JWT token removed');
            }
            
            // Set default API key
            localStorage.setItem('pi-monitor-api-key', 'pi-monitor-api-key-2024');
            console.log('Default API key set');
            
            document.getElementById('status').innerHTML = 
                '✅ Successfully cleared old JWT data and set default API key!<br>' +
                'You can now close this tab and use your Pi Monitor with API key authentication.';
        } catch (error) {
            document.getElementById('status').innerHTML = 
                '❌ Error: ' + error.message;
        }
    </script>
</body>
</html>
"""
    
    with open("clear_jwt_data.html", "w") as f:
        f.write(clear_script)
    
    print("   ✅ Created clear_jwt_data.html")
    print("   📋 Open this file in your browser to clear old JWT data")

def generate_new_api_key():
    """Generate a new secure API key"""
    print("\n🔑 Generating new secure API key...")
    
    try:
        import secrets
        new_api_key = secrets.token_urlsafe(64)
        
        print(f"   ✅ New API key generated: {new_api_key}")
        
        # Save to file
        with open("new_api_key.txt", "w") as f:
            f.write(f"# New Pi Monitor API Key\n")
            f.write(f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Keep this secure and don't commit to version control!\n\n")
            f.write(f"PI_MONITOR_API_KEY={new_api_key}\n")
        
        print("   📄 API key saved to new_api_key.txt")
        
        return new_api_key
        
    except ImportError:
        print("   ❌ secrets module not available, using fallback method")
        import random
        import string
        
        chars = string.ascii_letters + string.digits + '-_'
        new_api_key = ''.join(random.choice(chars) for _ in range(64))
        
        print(f"   ✅ New API key generated: {new_api_key}")
        
        with open("new_api_key.txt", "w") as f:
            f.write(f"# New Pi Monitor API Key\n")
            f.write(f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Keep this secure and don't commit to version control!\n\n")
            f.write(f"PI_MONITOR_API_KEY={new_api_key}\n")
        
        print("   📄 API key saved to new_api_key.txt")
        return new_api_key

def create_env_file(api_key):
    """Create .env file with the new API key"""
    print("\n📝 Creating .env file...")
    
    env_content = f"""# Pi Monitor Backend Configuration
# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# API Key for authentication (change this in production!)
PI_MONITOR_API_KEY={api_key}

# Server Configuration
BACKEND_PORT=5001
FRONTEND_PORT=80

# Logging
LOG_LEVEL=INFO
LOG_FILE=pi_monitor.log

# Security
MAX_CONNECTIONS=100
REQUEST_TIMEOUT=30
"""
    
    with open("backend/.env", "w") as f:
        f.write(env_content)
    
    print("   ✅ Created backend/.env file")

def show_migration_steps():
    """Show the steps to complete migration"""
    print("\n📋 Migration Steps Completed:")
    print("   1. ✅ Backed up old JWT files")
    print("   2. ✅ Generated new secure API key")
    print("   3. ✅ Created .env file")
    print("   4. ✅ Created JWT data clearing script")
    
    print("\n🚀 Next Steps:")
    print("   1. Set your new API key as environment variable:")
    print("      export PI_MONITOR_API_KEY='your-new-api-key'")
    print("   2. Restart your backend server")
    print("   3. Open clear_jwt_data.html in your browser to clear old data")
    print("   4. Test the new authentication system")
    
    print("\n🔒 Security Notes:")
    print("   - Keep your API key secret")
    print("   - Don't commit .env files to version control")
    print("   - Change the default API key in production")

def main():
    """Run the migration process"""
    print("🔄 Pi Monitor: JWT to API Key Migration")
    print("=" * 50)
    
    try:
        # Create backup
        backup_dir = backup_old_files()
        
        # Generate new API key
        new_api_key = generate_new_api_key()
        
        # Create .env file
        create_env_file(new_api_key)
        
        # Create JWT clearing script
        clear_old_jwt_data()
        
        # Show next steps
        show_migration_steps()
        
        print(f"\n🎉 Migration completed successfully!")
        print(f"📁 Backup files saved in: {backup_dir}")
        
    except Exception as e:
        print(f"\n💥 Migration failed: {e}")
        print("Please check the error and try again")

if __name__ == "__main__":
    main()
