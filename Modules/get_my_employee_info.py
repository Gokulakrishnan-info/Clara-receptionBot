import re
import pandas as pd
from livekit.agents import function_tool, RunContext

from . import config
from .state import employee_access


# Fields that should be considered confidential and not returned
CONFIDENTIAL_FIELDS = {
    'salary', 'wage', 'pay', 'compensation', 'income', 'bonus', 'incentive',
    'ssn', 'social_security', 'tax_id', 'bank_account', 'account_number',
    'password', 'pin', 'secret', 'private', 'confidential', 'personal_id',
    'medical', 'health', 'insurance_id', 'policy_number'
}


def is_confidential_field(field_name: str) -> bool:
    """Check if a field name contains confidential information."""
    field_lower = field_name.lower().strip()
    return any(conf_field in field_lower for conf_field in CONFIDENTIAL_FIELDS)


@function_tool()
async def get_my_employee_info(context: RunContext, employee_id: str = None) -> str:
    """
    Get employee information for authenticated employees.
    Returns non-confidential details like name, department, email, etc.
    Requires employee to be authenticated via face recognition or OTP.
    """
    try:
        # Use current employee ID if not provided
        if not employee_id or employee_id == "unknown":
            from .state import current_employee_id
            if current_employee_id:
                employee_id = current_employee_id
                print(f"DEBUG: Using current_employee_id: {employee_id}")
            else:
                return "❌ No employee ID provided and no current employee authenticated."
        
        # Check if employee is authenticated
        empid_norm = re.sub(r"\s+", "", employee_id).strip().upper()
        if not employee_access.get(empid_norm, {}).get("granted", False):
            return "❌ You need to be authenticated first. Please use face recognition or OTP verification."
        
        # Load employee data
        df = pd.read_csv(config.EMPLOYEE_CSV)
        df["EmployeeID_norm"] = df["EmployeeID"].astype(str).str.strip().str.upper()
        
        # Find employee record
        emp_match = df[df["EmployeeID_norm"] == empid_norm]
        if emp_match.empty:
            return "❌ Employee record not found."
        
        record = emp_match.iloc[0]
        
        # Build response with non-confidential fields
        info_parts = []
        for column in df.columns:
            if not is_confidential_field(column):
                value = str(record[column]).strip()
                if value and value.lower() not in ['nan', 'none', '']:
                    # Format field name nicely
                    field_name = column.replace('_', ' ').title()
                    info_parts.append(f"**{field_name}**: {value}")
        
        if not info_parts:
            return "❌ No accessible information found for this employee."
        
        # Add authentication source info
        auth_source = employee_access[empid_norm].get("source", "unknown")
        source_text = "face recognition" if auth_source == "face" else "OTP verification"
        
        response = f"✅ Here are your employee details (authenticated via {source_text}):\n\n"
        response += "\n".join(info_parts)
        
        return response
        
    except FileNotFoundError:
        return "❌ Employee database file is missing."
    except Exception as e:
        return f"❌ Error retrieving employee information: {str(e)}"


@function_tool()
async def get_employee_field(context: RunContext, name: str, field: str) -> str:
    """
    Get a specific field for an employee by name (for authenticated employees only).
    Returns only the requested field value.
    """
    try:
        # Check if the current user is authenticated
        from .state import current_employee_id
        if not current_employee_id:
            return "❌ You need to be authenticated first. Please use face recognition or OTP verification."
        
        current_empid_norm = re.sub(r"\s+", "", current_employee_id).strip().upper()
        is_current_user_authenticated = employee_access.get(current_empid_norm, {}).get("granted", False)
        
        if not is_current_user_authenticated:
            return "❌ You need to be authenticated first. Please use face recognition or OTP verification."
        
        # Load employee data
        df = pd.read_csv(config.EMPLOYEE_CSV)
        df["Name_norm"] = df["Name"].astype(str).str.strip().str.lower()
        
        name_norm = re.sub(r"\s+", " ", name).strip().lower()
        emp_matches = df[df["Name_norm"].str.contains(name_norm, na=False)]
        
        if emp_matches.empty:
            return f"❌ No employee found with name containing '{name}'."
        
        if len(emp_matches) > 1:
            # Multiple matches - return list of names and IDs
            results = []
            for _, emp in emp_matches.iterrows():
                emp_id = str(emp["EmployeeID"]).strip()
                emp_name = str(emp["Name"]).strip()
                results.append(f"• {emp_name} (ID: {emp_id})")
            
            return f"Found {len(emp_matches)} employees matching '{name}':\n\n" + "\n".join(results) + "\n\nPlease be more specific with the name."
        
        # Single match - return specific field
        record = emp_matches.iloc[0]
        emp_name = str(record["Name"]).strip()
        
        # Check if field exists and is not confidential
        field_lower = field.lower().strip()
        if is_confidential_field(field):
            return f"❌ Sorry, {field} information is confidential and cannot be shared."
        
        # Map common field names to actual column names
        field_mapping = {
            'email': 'Email',
            'department': 'Department', 
            'role': 'Role',
            'location': 'Location',
            'employee id': 'EmployeeID',
            'id': 'EmployeeID',
            'join date': 'JoinDate',
            'status': 'Status',
            'experience': 'YearsOfExperience',
            'years': 'YearsOfExperience'
        }
        
        # Find the actual column name
        actual_field = None
        for key, value in field_mapping.items():
            if key in field_lower:
                actual_field = value
                break
        
        if not actual_field:
            # Try direct match with column names
            for col in df.columns:
                if col.lower() == field_lower:
                    actual_field = col
                    break
        
        if not actual_field:
            available_fields = [f for f in df.columns if not is_confidential_field(f)]
            return f"❌ Field '{field}' not found. Available fields: {', '.join(available_fields)}"
        
        # Get the field value
        field_value = str(record[actual_field]).strip()
        if not field_value or field_value.lower() in ['nan', 'none', '']:
            return f"❌ {field} information is not available for {emp_name}."
        
        # Format the response based on the field
        if actual_field == 'Email':
            return f"Email of {emp_name} is {field_value}"
        elif actual_field == 'Department':
            return f"{emp_name} works in the {field_value} department"
        elif actual_field == 'Role':
            return f"{emp_name} is a {field_value}"
        elif actual_field == 'Location':
            return f"{emp_name} is located in {field_value}"
        elif actual_field == 'EmployeeID':
            return f"Employee ID of {emp_name} is {field_value}"
        elif actual_field == 'JoinDate':
            return f"{emp_name} joined on {field_value}"
        elif actual_field == 'Status':
            return f"{emp_name} status is {field_value}"
        elif actual_field == 'YearsOfExperience':
            return f"{emp_name} has {field_value} years of experience"
        else:
            return f"{field} of {emp_name} is {field_value}"
        
    except FileNotFoundError:
        return "❌ Employee database file is missing."
    except Exception as e:
        return f"❌ Error retrieving employee information: {str(e)}"


@function_tool()
async def get_employee_by_name(context: RunContext, name: str) -> str:
    """
    Search for employee information by name (for authenticated employees only).
    Returns basic non-confidential details.
    """
    try:
        # Load employee data
        df = pd.read_csv(config.EMPLOYEE_CSV)
        df["Name_norm"] = df["Name"].astype(str).str.strip().str.lower()
        
        name_norm = re.sub(r"\s+", " ", name).strip().lower()
        emp_matches = df[df["Name_norm"].str.contains(name_norm, na=False)]
        
        if emp_matches.empty:
            return f"❌ No employee found with name containing '{name}'."
        
        if len(emp_matches) > 1:
            # Multiple matches - return list of names and IDs
            results = []
            for _, emp in emp_matches.iterrows():
                emp_id = str(emp["EmployeeID"]).strip()
                emp_name = str(emp["Name"]).strip()
                results.append(f"• {emp_name} (ID: {emp_id})")
            
            return f"Found {len(emp_matches)} employees matching '{name}':\n\n" + "\n".join(results)
        
        # Single match - return details
        record = emp_matches.iloc[0]
        emp_id = str(record["EmployeeID"]).strip()
        
        # Check if the CURRENT USER (not the searched employee) is authenticated
        from .state import current_employee_id
        if not current_employee_id:
            return "❌ You need to be authenticated first. Please use face recognition or OTP verification."
        
        current_empid_norm = re.sub(r"\s+", "", current_employee_id).strip().upper()
        is_current_user_authenticated = employee_access.get(current_empid_norm, {}).get("granted", False)
        
        if not is_current_user_authenticated:
            return "❌ You need to be authenticated first. Please use face recognition or OTP verification."
        
        # Build response with non-confidential fields
        info_parts = []
        for column in df.columns:
            if not is_confidential_field(column):
                value = str(record[column]).strip()
                if value and value.lower() not in ['nan', 'none', '']:
                    field_name = column.replace('_', ' ').title()
                    info_parts.append(f"**{field_name}**: {value}")
        
        if not info_parts:
            return "❌ No accessible information found for this employee."
        
        # Add authentication source info for current user
        auth_source = employee_access[current_empid_norm].get("source", "unknown")
        source_text = "face recognition" if auth_source == "face" else "OTP verification"
        
        response = f"✅ Employee details for {record['Name']} (searched by authenticated user via {source_text}):\n\n"
        response += "\n".join(info_parts)
        
        return response
        
    except FileNotFoundError:
        return "❌ Employee database file is missing."
    except Exception as e:
        return f"❌ Error searching employee information: {str(e)}"
