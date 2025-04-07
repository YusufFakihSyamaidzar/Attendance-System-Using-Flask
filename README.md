# 📋 Attendance Management System (Flask + SQLite)

This is a simple web-based Attendance Management System built with **Flask** and **SQLite**. It supports admin login, student registration via CSV upload, attendance marking, modification, and reporting.<br>  
**_Note: This project was created as an academic assignment._**


---

## 🚀 Features

- Admin login system
- Upload CSV to register students
- Take and store daily attendance
- View individual student reports
- Edit or delete attendance by date
- Attendance summary with statistics
- Simple browser auto-launch on start

---

## 🛠 Technologies Used

- Python 3
- Flask
- SQLite
- HTML/CSS (Jinja templates)
- Bootstrap (optional for UI styling)
- Werkzeug (for password hashing)

---

## 📁 Folder Structure
```
 project/ 
 │ 
 ├── app.py # Main Flask application 
 ├── uploads/ # Uploaded CSV files
 ├── main.db # SQLite database (auto-created)
 └──templates/ # HTML templates 
          │ 
          ├── index.html
          ├── login.html
          ├── class_details.html
          ├── take_attendance.html
          ├── attendance_report.html 
          ├── upload.html
          ├── attendance_dates.html 
          └──  modify_attendance.html 
```

## 🛠 Requirements:
 [requirements.txt](./requirements.txt)
