#!/usr/bin/env python3
"""
Virtual Receptionist Setup Script
This script helps set up the virtual receptionist with face recognition.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_header():
    print("=" * 60)
    print("🤖 Virtual Receptionist with Face Recognition Setup")
    print("=" * 60)
    print()

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required.")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def install_dependencies():
    """Install required dependencies."""
    print("\n📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def create_env_file():
    """Create .env file from template if it doesn't exist."""
    env_file = Path(".env")
    env_example = Path("env.example")
    
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    if env_example.exists():
        shutil.copy(env_example, env_file)
        print("✅ Created .env file from template")
        print("   Please edit .env file with your actual values")
        return True
    else:
        print("❌ env.example file not found")
        return False

def check_data_files():
    """Check if required data files exist and validate them."""
    print("\n📁 Checking data files...")
    
    required_files = [
        "data/employee_details.csv",
        "data/candidate_interview.csv", 
        "data/company_info.pdf",
        "data/manager_visit.csv"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
        else:
            print(f"✅ {file_path}")
    
    if missing_files:
        print("\n❌ Missing required files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        print("\n   Please create these files before running the bot.")
        return False
    
    # Validate data files
    print("\n🔍 Validating data files...")
    try:
        import sys
        sys.path.append('scripts')
        import validate_data
        validate_data.validate_all_data()
    except Exception as e:
        print(f"⚠️  Could not validate data files: {e}")
    
    return True

def check_face_embeddings():
    """Check if face embeddings exist."""
    embeddings_file = Path("face_embeddings.pkl")
    if embeddings_file.exists():
        print("✅ Face embeddings found")
        return True
    else:
        print("⚠️  Face embeddings not found")
        print("   Run 'python face_recognition/enroll_faces.py' to create face embeddings")
        return False

def main():
    print_header()
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Create .env file
    if not create_env_file():
        return False
    
    # Check data files
    if not check_data_files():
        return False
    
    # Check face embeddings
    check_face_embeddings()
    
    print("\n" + "=" * 60)
    print("🎉 Setup completed!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Edit .env file with your Gmail credentials")
    print("2. Create face embeddings: python face_recognition/enroll_faces.py")
    print("3. Run the bot: python agent.py console")
    print("\nFor face recognition mode:")
    print("   $env:VR_FACE_EMBEDDINGS=\"face_embeddings.pkl\"; $env:AUTO_FACE_GREETING=\"1\"; python agent.py console")
    print()

if __name__ == "__main__":
    main()
