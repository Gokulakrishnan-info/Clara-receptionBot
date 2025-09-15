#!/usr/bin/env python3
"""
Quick test script to verify the virtual receptionist setup
"""

import os
import sys
import importlib
from pathlib import Path

def test_imports():
    """Test if all required modules can be imported."""
    print("🧪 Testing imports...")
    
    try:
        # Test core modules
        import pandas as pd
        import cv2
        import numpy as np
        print("✅ Core dependencies imported")
        
        # Test LiveKit
        from livekit import agents
        print("✅ LiveKit imported")
        
        # Test face recognition
        from Face.recognize_wrapper import Recognizer
        print("✅ Face recognition imported")
        
        # Test our modules
        from Modules import config
        from Modules.state import employee_access
        from face_integration import start_face_greeting
        print("✅ Virtual receptionist modules imported")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_config():
    """Test configuration loading."""
    print("\n⚙️  Testing configuration...")
    
    try:
        from Modules import config
        
        # Check if config paths exist
        if Path(config.EMPLOYEE_CSV).exists():
            print("✅ Employee CSV found")
        else:
            print(f"❌ Employee CSV not found: {config.EMPLOYEE_CSV}")
            
        if Path(config.CANDIDATE_CSV).exists():
            print("✅ Candidate CSV found")
        else:
            print(f"❌ Candidate CSV not found: {config.CANDIDATE_CSV}")
            
        return True
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def test_face_recognition():
    """Test face recognition setup."""
    print("\n👤 Testing face recognition...")
    
    try:
        embeddings_file = "face_embeddings.pkl"
        if Path(embeddings_file).exists():
            print("✅ Face embeddings file found")
            
            # Try to load the recognizer
            from Face.recognize_wrapper import Recognizer
            recognizer = Recognizer(embeddings_file)
            print("✅ Face recognizer loaded successfully")
            return True
        else:
            print("❌ Face embeddings file not found")
            print("   Run: python Face/Faces/enroll_faces.py")
            return False
            
    except Exception as e:
        print(f"❌ Face recognition error: {e}")
        return False

def test_environment():
    """Test environment variables."""
    print("\n🌍 Testing environment...")
    
    # Check if .env file exists
    if Path(".env").exists():
        print("✅ .env file found")
    else:
        print("⚠️  .env file not found (using defaults)")
    
    # Check Gmail credentials
    gmail_user = os.getenv("GMAIL_USER")
    if gmail_user:
        print("✅ Gmail user configured")
    else:
        print("⚠️  Gmail user not configured")
    
    return True

def main():
    print("=" * 50)
    print("🧪 Virtual Receptionist Setup Test")
    print("=" * 50)
    
    all_tests_passed = True
    
    # Run tests
    if not test_imports():
        all_tests_passed = False
    
    if not test_config():
        all_tests_passed = False
        
    if not test_face_recognition():
        all_tests_passed = False
        
    if not test_environment():
        all_tests_passed = False
    
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("🎉 All tests passed! Setup looks good.")
    else:
        print("❌ Some tests failed. Please check the issues above.")
    print("=" * 50)

if __name__ == "__main__":
    main()
