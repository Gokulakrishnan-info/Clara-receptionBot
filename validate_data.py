#!/usr/bin/env python3
"""
Data validation script for Virtual Receptionist
Validates CSV files and face embeddings
"""

import os
import pandas as pd
import pickle
from pathlib import Path

def validate_employee_csv(csv_path: str) -> tuple[bool, str]:
    """Validate employee CSV file structure."""
    try:
        df = pd.read_csv(csv_path)
        required_columns = ["EmployeeID", "Name", "Email"]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return False, f"Missing required columns: {missing_columns}"
        
        if df.empty:
            return False, "CSV file is empty"
        
        # Check for duplicate EmployeeIDs
        if df["EmployeeID"].duplicated().any():
            return False, "Duplicate EmployeeIDs found"
        
        return True, "Employee CSV is valid"
        
    except Exception as e:
        return False, f"Error reading CSV: {e}"

def validate_candidate_csv(csv_path: str) -> tuple[bool, str]:
    """Validate candidate CSV file structure."""
    try:
        df = pd.read_csv(csv_path)
        required_columns = ["Interview Code", "Candidate Name", "Interviewer"]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return False, f"Missing required columns: {missing_columns}"
        
        if df.empty:
            return False, "CSV file is empty"
        
        return True, "Candidate CSV is valid"
        
    except Exception as e:
        return False, f"Error reading CSV: {e}"

def validate_face_embeddings(embeddings_path: str) -> tuple[bool, str]:
    """Validate face embeddings file."""
    try:
        if not os.path.exists(embeddings_path):
            return False, "Face embeddings file not found"
        
        with open(embeddings_path, "rb") as f:
            data = pickle.load(f)
        
        if not isinstance(data, dict):
            return False, "Face embeddings should be a dictionary"
        
        if not data:
            return False, "Face embeddings dictionary is empty"
        
        # Check if embeddings are valid (numpy arrays or lists that can be converted)
        for emp_id, embedding in data.items():
            if not (hasattr(embedding, 'shape') or isinstance(embedding, (list, tuple))):
                return False, f"Invalid embedding for {emp_id}"
        
        return True, f"Face embeddings valid with {len(data)} employees"
        
    except Exception as e:
        return False, f"Error reading face embeddings: {e}"

def validate_all_data():
    """Validate all data files."""
    print("🔍 Validating Virtual Receptionist Data Files")
    print("=" * 50)
    
    # Check employee CSV
    employee_csv = "dummy-data/employee_details.csv"
    if os.path.exists(employee_csv):
        valid, message = validate_employee_csv(employee_csv)
        print(f"Employee CSV: {'✅' if valid else '❌'} {message}")
    else:
        print("❌ Employee CSV not found")
    
    # Check candidate CSV
    candidate_csv = "dummy-data/candidate_interview.csv"
    if os.path.exists(candidate_csv):
        valid, message = validate_candidate_csv(candidate_csv)
        print(f"Candidate CSV: {'✅' if valid else '❌'} {message}")
    else:
        print("❌ Candidate CSV not found")
    
    # Check face embeddings
    embeddings_file = "face_embeddings.pkl"
    valid, message = validate_face_embeddings(embeddings_file)
    print(f"Face Embeddings: {'✅' if valid else '❌'} {message}")
    
    # Check other required files
    required_files = [
        "dummy-data/company_info.pdf",
        "dummy-data/manager_visit.csv"
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} not found")
    
    print("=" * 50)

if __name__ == "__main__":
    validate_all_data()
