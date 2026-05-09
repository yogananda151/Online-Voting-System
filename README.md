# Online Voting System

A Flask-based online voting platform with voter face verification, election management, candidate selection, and results publishing.

## 🚀 Project Overview

This project implements a secure online voting system using Flask and MySQL. Voters can register, login, browse active elections, choose candidates, and cast votes. Administrators can manage elections, candidates, voters, upload voter lists, and publish election results.

A biometric layer is included using OpenCV for face capture and HOG-based feature matching during voter registration and login.

## ✨ Key Features

- Voter registration with biometric face feature capture
- Voter login with face verification
- Browse active elections and candidates
- Vote casting with duplicate-vote prevention
- Admin dashboard for elections, candidates, and voters
- Upload voters from CSV / Excel files using `pandas`
- Publish election results and archive voters
- MySQL database-backed persistence

## 🧠 Technology Stack

- Python 3
- Flask
- MySQL / MariaDB
- OpenCV (`cv2`)
- NumPy
- pandas
- Werkzeug

## 📁 Project Structure

- `app.py` - Main Flask application and route definitions
- `config.py` - App configuration and upload settings
- `voting_system.sql` - Database schema and seed data script
- `static/` - CSS and uploaded file storage
- `templates/` - HTML views for admin and voter pages
- `path_to_upload_folder/` - file upload helper path

## ✅ Available User Flows

### Voter

- Register with name, voter ID, email, password, and face capture
- Login with email/password and realtime face verification
- View active elections and election candidates
- Cast votes for candidates
- View results when published or after election end

### Admin

- Login to admin dashboard
- Add and manage elections
- Add, edit, and delete candidates
- See all voters and assign voters to elections
- Upload bulk voters via Excel/CSV
- Publish results and view election summaries
- Archive voters after election completion

## ⚙️ Prerequisites

- Python 3.8+ installed
- MySQL or MariaDB server
- Webcam for voter face capture
- `pip` package manager
- On Windows: Visual Studio Build Tools for `mysqlclient` (optional if using alternatives)

## 🛠️ Installation

1. Create a Python virtual environment (recommended):

```bash
python -m venv venv
venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install flask mysqlclient opencv-python numpy pandas werkzeug
```

3. Configure database credentials in `config.py` if needed:

```python
MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'your_password'
MYSQL_DB = 'voting_system'
```

4. Create the database and tables:

```bash
mysql -u root -p < voting_system.sql
```

5. Make sure upload directories exist:

```bash
mkdir static\uploads
```

## ▶️ Running the App

Start the Flask web server:

```bash
python app.py
```

Open the browser and visit:

```text
http://127.0.0.1:5000/
```

## 🔐 Default Admin Login

If the database does not already contain an admin user, the seed script adds one:

- Username: `admin`
- Password: `admin@123`

## 📌 Configuration

The `config.py` file contains application settings:

- `SECRET_KEY` for Flask sessions
- MySQL connection details
- `UPLOAD_FOLDER` for user files
- `ALLOWED_EXTENSIONS` for uploads

## 🧾 Database Schema

The SQL file creates the following tables:

- `admins`
- `admin_settings`
- `elections`
- `voters`
- `candidates`
- `votes`
- `election_voters`
- `archive_voters`

## 🧰 Notes & Troubleshooting

- The app requires a working camera for voter face registration and login.
- On Windows, `mysqlclient` may need Microsoft Visual C++ build tools. If installation fails, use a compatible MySQL driver.
- Restart the Flask server after changing `config.py`.
- If face verification fails, ensure the camera has good lighting and a clear frontal face image.

## 📌 Suggested Improvements

- Add a `requirements.txt` file for easier dependency installation
- Add screenshots or demo images to the README
- Add environment variable support for database credentials
- Add tests for route and authentication logic

## 🧑‍💻 Contribution

Contributions are welcome. Feel free to add new features, improve the UI, or enhance security.

## 📄 License

This project is provided as-is for learning and demonstration purposes.

