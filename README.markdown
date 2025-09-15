# Virtual Receptionist with Face Recognition 🤖  

Clara is an **AI-powered virtual receptionist** with advanced face recognition capabilities for an Info Services company. She acts as the first point of contact for anyone visiting — employees, interview candidates, or walk-in visitors. Clara can recognize employees instantly via face recognition, verify identities, notify the right people, and keep a record of visits.  

---

## ✨ Features  

✅ **Face Recognition Authentication**  
- Instant employee recognition via camera  
- Wake word activation: "Hey Clara"  
- Automatic authentication without OTP for recognized employees  
- Retry face recognition for failed initial attempts  

✅ **Employee Verification**  
- Face recognition (primary method)  
- Fallback: Name + Employee ID + OTP via email  
- Secure login with retry limit  

✅ **Candidate Verification**  
- Provide Interview Code + Name.  
- Clara notifies the assigned interviewer by email.  

✅ **Visitor Registration**  
- Enter Name, Phone Number, Purpose, and Employee to meet.  
- Visitor logged in `visitor_log.csv`.  
- Host employee notified by email.  

✅ **Manager Visit Greeting**  
- Managers listed in `manager_visit.csv` get a **VIP greeting** if visiting today's office.  

✅ **Company Info Access**  
- Clara can answer company-related FAQs (from `company_info.pdf`).  
- Employee details lookup (non-confidential information)  

---

## 🚀 Getting Started  

### 1. Clone the Repository  
```bash
git clone https://github.com/YOUR_USERNAME/virtual-receptionist.git
cd virtual-receptionist
```

### 2. Create Virtual Environment  
```bash
python -m venv venv
# On macOS/Linux
source venv/bin/activate
# On Windows
venv\Scripts\activate
```

### 3. Quick Setup (Recommended)  
```bash
python setup.py
```

This will:
- Install all dependencies
- Create .env file from template
- Check for required data files
- Verify face recognition setup

### 3b. Manual Setup (Alternative)  
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables  
The setup script creates a `.env` file from the template. Edit it with your values:  

```env
# Gmail credentials (for sending OTPs & notifications)
GMAIL_USER=yourcompanyemail@gmail.com
GMAIL_APP_PASSWORD=xxxxxxx   # App-specific password

# Face Recognition Settings
VR_FACE_EMBEDDINGS=face_embeddings.pkl
AUTO_FACE_GREETING=1
VR_CAMERA_INDEX=0
BYPASS_WAKEWORD=0

# Data File Paths (optional - defaults provided)
VR_EMPLOYEE_CSV=dummy-data/employee_details.csv
VR_CANDIDATE_CSV=dummy-data/candidate_interview.csv
VR_COMPANY_INFO_PDF=dummy-data/company_info.pdf
VR_VISITOR_LOG=dummy-data/visitor_log.csv
VR_MANAGER_VISIT_CSV=dummy-data/manager_visit.csv

# Twilio (optional, for SMS support)
TWILIO_SID=xxxxxxx
TWILIO_AUTH=xxxxxxx
TWILIO_FROM=+1234567890
```

> ⚠️ Do **NOT** commit `.env` to GitHub (already ignored in `.gitignore`).  

### 5. Prepare Data Files  
Inside the `dummy-data/` folder, create these CSV files:  

#### 📂 `employee_details.csv`  
```csv
Name,EmployeeID,Email,Phone,Department
Rakesh,E009,rakesh@company.com,+919876543210,Engineering
Rahul Kumar,E010,rahul@company.com,+919876543211,HR
Gokul,E006,gokul@company.com,+919876543212,IT
```

#### 📂 Face Recognition Setup  
1. **Enroll faces**: Run `python Face/Faces/enroll_faces.py` to create face embeddings
2. **Test recognition**: Run `python Face/recognize_live.py` to test face recognition
3. **Verify embeddings**: Ensure `face_embeddings.pkl` is created in project root

#### 📂 `candidate_interview.csv`  
```csv
Candidate Name,Interview Role,HR Coordinator,Interviewer,Interview Time,Interview Code
Manish Patel,Business Analyst,Pooja Menon,Rahul Kumar,2025-09-04 14:30,INT009
```

#### 📂 `visitor_log.csv`  
*(auto-generated, no need to pre-fill)*  
```csv
Visitor Name,Phone,Purpose,Meeting Employee,Timestamp
```

#### 📂 `manager_visit.csv`  
```csv
Manager Name,EmployeeID,Office,Visit Date
Rakesh,E009,Chennai,2025-09-05
```

---

## ▶️ Running the Project  

### Test Setup First  
```bash
python test_setup.py
```

### Start Clara with Face Recognition:  
```bash
# Set environment variables and start
$env:VR_FACE_EMBEDDINGS="face_embeddings.pkl"; $env:AUTO_FACE_GREETING="1"; $env:VR_CAMERA_INDEX="0"; python agent.py console
```

### Start Clara without Face Recognition (Manual Mode):  
```bash
python agent.py console
```

Clara will now handle interactions with face recognition capabilities and your defined tools.  

---

## 📂 Project Structure  

```
virtual-receptionist/
├── agent.py                # Main agent logic
├── tools.py                # Employee, Candidate, Visitor tools
├── prompts.py              # Agent instructions
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
├── dummy-data/             # Local data files (ignored in Git)
│   ├── employee_details.csv
│   ├── candidate_interview.csv
│   ├── visitor_log.csv
│   └── manager_visit.csv
└── .gitignore
```

---

## ⚡ Example Flows  

### Face Recognition Employee Flow  
```
User: "Hey Clara"
Clara: "🎉 Welcome back, Gokul! It's wonderful to see you again! You are now authenticated and have full access to all services."
User: "What's my email?"
Clara: "Your email is gokul@company.com. You work in the IT department."
```

### Manual Employee Flow (Fallback)  
```
User: "I am Rakesh, employee ID E009."
Clara: "Thanks Rakesh. Checking your record… I've sent an OTP to your email. Please tell me the OTP now."
User: "123456"
Clara: "✅ OTP verified. Welcome Rakesh!"
```

### Candidate Flow  
```
User: "I am Manish Patel, here for interview code INT009."
Clara: "Thanks Manish. Checking your record… ✅ Please wait, Rahul Kumar will meet you shortly."
```

### Visitor Flow  
```
User: "I'm Anil Kumar, here to meet Rakesh."
Clara: "Thanks Anil. Please provide your contact number."
User: "+91 9876543210"
Clara: "What is the purpose of your visit?"
User: "Partnership discussion."
Clara: "✅ I've logged your visit and informed Rakesh. Please wait at the reception."
```

### Retry Face Recognition Flow  
```
User: "Hey Clara"
Clara: "I don't recognize you. Are you a candidate or a visitor?"
User: "I'm an employee"
Clara: "Let me try face recognition again... 🎉 Great! I recognize you now, Gokul! Welcome!"
```

### Manager Visit (VIP Greeting)  
```
User: "Hey Clara"
Clara: "🎉 Welcome back, Rakesh! Hope you had a smooth journey. It was wonderful having you at our Chennai office! You have full access to all tools."
```

---

## 🛠 Troubleshooting  

### Face Recognition Issues
- **❌ Camera not opening** → Check `VR_CAMERA_INDEX` (try 0, 1, 2)
- **❌ Face not recognized** → Ensure face embeddings are created and up-to-date
- **❌ Wake word not working** → Check microphone permissions and try "Hey Clara" clearly
- **❌ Models not loading** → Ensure all dependencies are installed correctly

### General Issues
- **❌ Email not sending** → Check Gmail App Password & `.env` setup.  
- **❌ Employee/Candidate not found** → Ensure CSV files are correctly formatted.  
- **❌ OTP incorrect** → OTPs are session-based; ask Clara to resend.  
- **FileNotFoundError** → Make sure CSV files exist in `dummy-data/`.
- **❌ Google API timeout** → Check internet connection and API availability  

---

## 🤝 Contributing  

1. Fork this repo  
2. Create a feature branch (`feature-new`)  
3. Commit changes  
4. Push to branch  
5. Open a Pull Request  

---

## 📜 License  
This project is licensed under the MIT License.  
