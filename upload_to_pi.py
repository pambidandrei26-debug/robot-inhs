#!/usr/bin/env python3
"""
Simple script to upload web_remote_control.py to Raspberry Pi
Requires: pip install paramiko
"""

import paramiko
import os

# Configuration
PI_HOST = "192.168.168.111"
PI_USER = "pi"
PI_PASSWORD = input("Enter Pi password: ")

LOCAL_FILE = "raspberry_pi/web_remote_control.py"
REMOTE_PATH = "/home/pi/crack_detector/web_remote_control.py"

print(f"\n📤 Uploading {LOCAL_FILE} to Pi...")

try:
    # Create SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"🔌 Connecting to {PI_HOST}...")
    ssh.connect(PI_HOST, username=PI_USER, password=PI_PASSWORD)
    
    # Create SFTP session
    sftp = ssh.open_sftp()
    
    # Backup existing file first
    print("💾 Creating backup...")
    try:
        stdin, stdout, stderr = ssh.exec_command(
            f"cp {REMOTE_PATH} {REMOTE_PATH}.backup"
        )
        stdout.channel.recv_exit_status()
    except:
        print("   (no existing file to backup)")
    
    # Upload file
    print(f"⬆️  Uploading file...")
    sftp.put(LOCAL_FILE, REMOTE_PATH)
    
    # Set permissions
    print("🔐 Setting permissions...")
    sftp.chmod(REMOTE_PATH, 0o755)
    
    sftp.close()
    ssh.close()
    
    print("\n✅ Upload successful!")
    print(f"\nTo test, SSH to Pi and run:")
    print(f"  ssh pi@{PI_HOST}")
    print(f"  cd ~/crack_detector")
    print(f"  python3 web_remote_control.py")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nAlternatives:")
    print("1. Use WinSCP (https://winscp.net)")
    print("2. Manual copy-paste via nano (see WEB_CONTROLLER_FIXES.md)")
