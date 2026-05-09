# Online Voting System

A Flask-based online voting platform with voter face verification, election management, candidate selection, and results publishing.

## 🚀 Project Overview

This project implements a secure online voting system using Flask and MySQL. Voters can register, login, browse active elections, choose candidates, and cast votes. Administrators can manage elections, candidates, voters, upload voter lists, and publish election results.

The application also includes a biometric verification layer using OpenCV face capture and HOG-based face feature matching.

## ✨ Key Features

- Voter registration with biometric face feature capture
- Voter login with face verification
- Active election list for voters with candidate selection
- Secure vote casting and vote tracking
- Admin dashboard with election, candidate, and voter management
- CSV/Excel voter upload support via `pandas`
- Results publication and archived voter support
- MySQL database integration

## 🧠 Technology Stack

- Python 3
- Flask
- MySQL / MariaDB
- OpenCV (`cv2`)
- NumPy
- pandas
- Werkzeug security utilities

## 📁 Project Structure

- `app.py` - Main Flask application and route definitions
- `config.py` - Configuration settings for Flask and database
- `voting_system.sql` - Database schema and default admin seed script
- `static/` - CSS and uploaded files
- `templates/` - HTML views for admin and voter interfaces

## ⚙️ Requirements

Install Python packages required by the project.

Recommended packages:

- Flask
- mysqlclient or MySQLdb-compatible driver
- opencv-python
- numpy
- pandas
- Werkzeug

Example install command:

```bash
pip install flask mysqlclient opencv-python numpy pandas werkzeug
```

> Note: On Windows, `mysqlclient` may require Visual Studio build tools or prebuilt wheels.

## 🛠️ Setup

1. Clone the repository or copy the project files.
2. Create the MySQL database and tables using `voting_system.sql`.
3. Update database credentials in `config.py` if needed:

```python
MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'your_password'
MYSQL_DB = 'voting_system'
```

4. Ensure the `static/uploads` folder exists and is writable.
5. Install dependencies.
6. Run the app:

```bash
python app.py
```

7. Open `http://127.0.0.1:5000/` in your browser.

## 🔐 Default Admin Login

The database seed script creates a default administrator account if it does not already exist.

- Username: `admin`
- Password: `admin@123`

## 🧾 Database

Run the SQL schema script to prepare the database:

```bash
mysql -u root -p < voting_system.sql
```

This script creates tables for:

- `admins`
- `admin_settings`
- `elections`
- `voters`
- `candidates`
- `votes`
- `election_voters`
- `archive_voters`

## 💡 Notes

- The app uses webcam face capture during voter registration and login. Make sure your development machine has a functioning camera.
- The face verification uses OpenCV Haar cascades and HOG descriptors stored in the database.
- If you change configuration or database credentials, restart the Flask app.

## 📌 License

This project is provided as-is for learning and demonstration purposes.

