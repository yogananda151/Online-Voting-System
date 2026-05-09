# 🗳️ Online Voting System - Secure Digital Elections with Biometric Authentication

## Streamline Your Elections with a Modern, Secure, and User-Friendly Voting Platform

---

## Introduction

The **Online Voting System** is a comprehensive Flask-based web application designed to facilitate secure, transparent, and efficient elections in the digital age. Whether you're running a school election, corporate governance vote, or community decision-making process, this system provides a complete solution for voter registration, election management, and result publishing—all with integrated biometric face verification for enhanced security.

Voters can register with a simple account and face capture, login securely with face verification, browse active elections, and cast votes with confidence. Administrators have a dedicated dashboard to create elections, manage candidates, upload voter lists in bulk, monitor voting progress, and publish results with full transparency.

**Key Value Proposition:** Fast setup, secure voting, biometric authentication, and complete election lifecycle management in one platform.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ONLINE VOTING SYSTEM                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐              ┌──────────────┐             │
│  │   VOTER      │              │    ADMIN     │             │
│  │   PORTAL     │              │   DASHBOARD  │             │
│  └──────┬───────┘              └──────┬───────┘             │
│         │                             │                      │
│    ┌────▼──────────────────────────────┴─────┐              │
│    │                                          │              │
│    │   FLASK WEB APPLICATION                 │              │
│    │  ┌─────────────────────────────────┐   │              │
│    │  │ Routes & Authentication         │   │              │
│    │  │ Face Verification (OpenCV)      │   │              │
│    │  │ Vote Processing & Tracking      │   │              │
│    │  └─────────────────────────────────┘   │              │
│    │                                          │              │
│    └────┬───────────────────────────────┬────┘              │
│         │                               │                    │
│    ┌────▼──────┐              ┌────────▼────┐              │
│    │  MYSQL    │              │  FILE SYSTEM│              │
│    │ DATABASE  │              │  (Uploads)  │              │
│    └───────────┘              └─────────────┘              │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ OpenCV Face Capture & HOG Feature Matching          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## ✨ Key Features

- **🔐 Biometric Authentication** - Voter registration with face capture and login with face verification using OpenCV
- **🗳️ Complete Election Lifecycle** - Create elections, manage candidates, control voting windows, and publish results
- **👥 Voter Management** - Register voters individually or upload in bulk via CSV/Excel
- **📊 Results & Analytics** - View vote counts, publish results, and archive voters after elections
- **🛡️ Security** - Password hashing with Werkzeug, duplicate-vote prevention, session management
- **⚡ Admin Dashboard** - Intuitive controls for elections, candidates, voters, and results

---

## 🧠 Technology Stack

| Component       | Technology          |
|-----------------|---------------------|
| Backend         | Flask (Python 3)    |
| Database        | MySQL / MariaDB     |
| Face Detection  | OpenCV (cv2)        |
| Data Processing | pandas, NumPy       |
| Security        | Werkzeug            |
| Frontend        | HTML, CSS, Jinja2   |

---

## 📁 Project Structure

```
online-voting-system/
├── app.py                          # Main Flask application
├── config.py                       # Configuration settings
├── voting_system.sql               # Database schema
├── static/
│   ├── css/
│   │   └── style.css              # Styling
│   └── uploads/                   # User file uploads
├── templates/
│   ├── base.html                  # Base template
│   ├── admin/                     # Admin interface pages
│   │   ├── dashboard.html
│   │   ├── elections.html
│   │   ├── candidates.html
│   │   ├── voters.html
│   │   ├── results.html
│   │   └── ...
│   └── voter/                     # Voter interface pages
│       ├── dashboard.html
│       ├── elections.html
│       ├── candidates.html
│       ├── login.html
│       ├── register.html
│       └── results.html
└── README.md                      # This file
```

---

# 👤 For End-Users: Installation & Usage

## Prerequisites

- Python 3.8 or higher
- MySQL or MariaDB server (local or remote)
- Webcam for face capture
- Windows, macOS, or Linux operating system

## Quick Start

### 1. Download the Project

Clone or download the project files to your machine:

```bash
git clone https://github.com/yogananda151/Online-Voting-System.git
cd Online-Voting-System
```

### 2. Set Up Python Environment

Create and activate a virtual environment:

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install flask mysqlclient opencv-python numpy pandas werkzeug
```

> **Note for Windows users:** If `mysqlclient` installation fails, install [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/) or use a prebuilt wheel file.

### 4. Configure Database

Edit `config.py` and update MySQL credentials:

```python
MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'your_password'
MYSQL_DB = 'voting_system'
```

### 5. Initialize Database

Run the SQL schema file to create tables:

```bash
mysql -u root -p < voting_system.sql
```

This creates all necessary tables and seeds a default admin account.

### 6. Create Upload Directory

Ensure the uploads folder exists:

```bash
mkdir -p static/uploads
```

### 7. Run the Application

Start the Flask development server:

```bash
python app.py
```

The app will launch at `http://127.0.0.1:5000/`.

## 🔐 Default Admin Credentials

- **Username:** `admin`
- **Password:** `admin@123`

⚠️ **Important:** Change the admin password immediately after first login.

## Using the System

### For Voters

1. **Register:** Visit the voter registration page, provide details, and capture your face
2. **Login:** Enter email/password and verify with face recognition
3. **Vote:** Browse active elections, select candidates, and submit your vote
4. **View Results:** Check published results on the results page

### For Administrators

1. **Login:** Use admin credentials on the admin login page
2. **Create Elections:** Set election name, area, start time, and end time
3. **Add Candidates:** Add candidates to each election with party affiliation
4. **Manage Voters:** Upload bulk voters via CSV/Excel or add manually
5. **Monitor Progress:** View live vote counts in the admin dashboard
6. **Publish Results:** Publish results when voting closes
7. **Archive:** Archive voters after election completion

---

# 🛠️ For Contributors: Development Setup

## Getting Started

### 1. Fork & Clone

Fork the repository on GitHub and clone it locally:

```bash
git clone https://github.com/your-username/Online-Voting-System.git
cd Online-Voting-System
```

### 2. Create a Feature Branch

Always create a new branch for your work:

```bash
git checkout -b feature/your-feature-name
```

### 3. Set Up Development Environment

Follow the installation steps above, but also install development tools:

```bash
pip install flask mysqlclient opencv-python numpy pandas werkzeug pytest pytest-flask
```

### 4. Understand the Codebase

- **`app.py`** - All Flask routes and business logic
- **`config.py`** - Configuration for Flask and database
- **`voting_system.sql`** - Database schema reference
- **`templates/`** - Jinja2 HTML templates for rendering pages

### 5. Make Your Changes

- Keep code clean and well-commented
- Follow PEP 8 style guidelines
- Test your changes locally before committing

### 6. Testing

Run tests to ensure your changes don't break existing functionality:

```bash
pytest
```

### 7. Commit & Push

Commit with clear, descriptive messages:

```bash
git add .
git commit -m "Add feature: brief description of changes"
git push origin feature/your-feature-name
```

### 8. Create a Pull Request

Submit a pull request on GitHub with:
- Clear title describing the change
- Description of what you changed and why
- Reference to any related issues
- Screenshots if UI changes

---

## 🤝 Contributor Guidelines

### Before You Start

- Check open [issues](https://github.com/yogananda151/Online-Voting-System/issues) to see what needs work
- Read existing code to understand the structure
- Ask questions in issues if something is unclear

### Code Standards

- **Python:** Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- **Commits:** Use clear, descriptive messages (e.g., "Fix face verification timeout" not "Fix bug")
- **Comments:** Add docstrings to functions and comments for complex logic
- **Testing:** Write tests for new features

### Submission Process

1. **Create an Issue** (optional but encouraged) - Describe what you want to do
2. **Fork & Branch** - Create a feature branch from `main`
3. **Develop & Test** - Implement your feature and test thoroughly
4. **Submit Pull Request** - Include description, screenshots, and testing notes
5. **Code Review** - Address feedback from reviewers
6. **Merge** - Your code is merged after approval

### Pull Request Checklist

- [ ] Code follows PEP 8 style guidelines
- [ ] Tests pass locally
- [ ] New features have unit tests
- [ ] Documentation is updated
- [ ] Commit messages are clear and descriptive
- [ ] No hardcoded credentials or secrets in code
- [ ] Changes are focused on a single feature/fix

---

## 📋 Areas for Contribution

We welcome contributions in these areas:

- **UI/UX Improvements** - Enhance the web interface design
- **Security Enhancements** - Add 2FA, improved encryption, input validation
- **Features** - Add email notifications, vote recounts, audit logs
- **Documentation** - Improve README, add API docs, create tutorials
- **Bug Fixes** - Fix issues found in the tracker
- **Testing** - Add unit tests and integration tests
- **Performance** - Optimize database queries, add caching

---

## 🐛 Reporting Bugs

Found a bug? Please report it by:

1. Creating a new issue on GitHub
2. Include a clear title and description
3. Provide steps to reproduce
4. Mention your OS and Python version
5. Attach error logs if available

Example:
```
Title: Face verification fails with webcam on Windows
Description: When using an external USB webcam on Windows 10, 
face verification times out...
Steps: 1. Register voter, 2. Enable USB webcam, 3. Try login
Error: [error log here]
```

---

## 📌 Configuration Reference

### `config.py` Settings

| Setting | Purpose | Default |
|---------|---------|---------|
| `SECRET_KEY` | Flask session encryption | `'your_secret_key'` |
| `MYSQL_HOST` | Database server | `'localhost'` |
| `MYSQL_USER` | Database username | `'root'` |
| `MYSQL_PASSWORD` | Database password | `'Yoga@151'` |
| `MYSQL_DB` | Database name | `'voting_system'` |
| `UPLOAD_FOLDER` | File upload location | `'static/uploads'` |
| `ALLOWED_EXTENSIONS` | Allowed file types | `{'png','jpg','xlsx','xls'}` |

---

## 🧰 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'MySQLdb'"
**Solution:** Install `mysqlclient`: `pip install mysqlclient`

### Issue: Face verification is inaccurate
**Solution:** Ensure good lighting, clear frontal face view, and camera is properly focused

### Issue: Database connection refused
**Solution:** Verify MySQL is running, check credentials in `config.py`

### Issue: Port 5000 already in use
**Solution:** Change port in `app.py`: `app.run(debug=True, port=5001)`

---

## 📄 License

This project is provided as-is for learning and demonstration purposes. See LICENSE file for details.

---

## 🙏 Acknowledgments

- Flask documentation and community
- OpenCV for computer vision capabilities
- MySQL for reliable data storage
- All contributors who help improve this project

---

## 📞 Support & Contact

- **Issues:** Report bugs and request features on [GitHub Issues](https://github.com/yogananda151/Online-Voting-System/issues)
- **Discussions:** Ask questions in [GitHub Discussions](https://github.com/yogananda151/Online-Voting-System/discussions)

---

**Happy voting! 🗳️**


