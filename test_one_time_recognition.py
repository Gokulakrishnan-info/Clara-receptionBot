#!/usr/bin/env python3
"""
Test the one-time face recognition flow
"""
import os
import sys
from face_integration import _first_decision, load_employee_db

def test_one_time_recognition():
    """Test one-time face recognition without LiveKit"""
    print("🧪 Testing One-Time Face Recognition")
    print("=" * 50)
    
    # Set up environment
    os.environ["VR_FACE_EMBEDDINGS"] = "face_embeddings.pkl"
    os.environ["VR_CAMERA_INDEX"] = "0"
    
    # Test face recognition decision (one-time, 8 seconds)
    print("🎯 Starting one-time face recognition...")
    print("   - Camera will open for 8 seconds")
    print("   - Look at the camera")
    print("   - Press 'q' in the camera window to quit early")
    print("   - Camera will close automatically after 8 seconds")
    
    try:
        result = _first_decision(
            embeddings_path="face_embeddings.pkl",
            employee_csv="dummy-data/employee_details.csv",
            cam_index=0,
            threshold=0.65,
            min_stable_frames=3,
            timeout_s=8
        )
        
        print(f"\n📝 Result: {result}")
        
        if "Welcome back" in result:
            print("✅ SUCCESS - Employee recognized!")
            return True
        elif "I don't recognize you" in result:
            print("✅ SUCCESS - Unknown user detected!")
            return True
        else:
            print("❌ Unexpected result")
            return False
            
    except Exception as e:
        print(f"❌ Face recognition failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing One-Time Face Recognition Flow")
    print("This will open the camera for 8 seconds, then close it.")
    print()
    
    success = test_one_time_recognition()
    
    if success:
        print("\n🎉 One-time face recognition is working correctly!")
        print("\nFlow:")
        print("1. User says 'Hey Clara'")
        print("2. Camera opens for 8 seconds")
        print("3. Face recognition runs")
        print("4. Camera closes")
        print("5. Clara speaks the result")
    else:
        print("\n❌ Test failed. Please check the errors above.")
        sys.exit(1)
