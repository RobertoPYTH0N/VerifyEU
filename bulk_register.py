#!/usr/bin/env python3
"""
Bulk registration script - registers all images from to_register directory
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, '/home/flipman/Documents/Personal_Projects/AI_Policy_Hackathon')

from dotenv import load_dotenv
load_dotenv('/home/flipman/Documents/Personal_Projects/AI_Policy_Hackathon/.env')

import main

def bulk_register():
    """Register all images from to_register directory"""
    
    # Set up a test user for registration
    print("\n" + "="*100)
    print("BULK REGISTRATION - Registering images with image data storage")
    print("="*100)
    
    # Create a test user if needed
    username = "bulk_uploader"
    password = "BulkUpload123"
    
    # Try to create user
    result = main.register_user(username, password)
    if result["status"] == "error" and "already exists" in result["message"]:
        print(f"✓ User '{username}' already exists")
        # Login
        login_result = main.login(username, password)
        if login_result["status"] == "success":
            main.current_user = {
                "user_id": login_result["user_id"],
                "username": login_result["username"]
            }
            print(f"✓ Logged in as {username}")
        else:
            print(f"✗ Login failed: {login_result['message']}")
            return
    elif result["status"] == "success":
        print(f"✓ Created user '{username}'")
        # Login right away
        login_result = main.login(username, password)
        main.current_user = {
            "user_id": login_result["user_id"],
            "username": login_result["username"]
        }
        print(f"✓ Logged in as {username}")
    else:
        print(f"✗ Error: {result['message']}")
        return
    
    # Register all images
    directory = "/home/flipman/Documents/Personal_Projects/AI_Policy_Hackathon/to_register"
    
    if not os.path.isdir(directory):
        print(f"✗ Directory not found: {directory}")
        return
    
    stats = main.register_all_from_directory(directory)
    
    print(f"\n{'='*100}")
    print("REGISTRATION COMPLETE")
    print(f"  Total registered: {stats['registered']}")
    print(f"  Duplicates skipped: {stats['duplicates']}")
    print(f"  Errors: {stats['errors']}")
    print(f"{'='*100}\n")

if __name__ == "__main__":
    bulk_register()
