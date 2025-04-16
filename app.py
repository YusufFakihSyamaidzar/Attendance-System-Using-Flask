import sqlite3
import os
import time
from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import date
import csv
import platform
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import webbrowser
import subprocess
import threading
import logging


# Create Flask app with explicit instance path
app = Flask(__name__, instance_relative_config=True)
# Use a very simple secret key
app.secret_key = 'dev_key_123'  # Simple key without special characters
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'csv'}
db = 'main.db'


os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def allowed_file(filename):
    """Check if the file has a valid extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def get_db():
    """Establish and return a database connection."""
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database with tables."""
    conn = get_db()
    cursor = conn.cursor()

    # Teacher/Admin Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    );
    ''')

    # Student Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS student (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Reg_no TEXT UNIQUE NOT NULL
    );
    ''')

    # Attendance Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Reg_no TEXT NOT NULL,
        date TEXT NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY(Reg_no) REFERENCES student(Reg_no)
    );
    ''')

    # Insert default admin user
    cursor.execute('SELECT * FROM admin WHERE username=?', ('admin',))
    if not cursor.fetchone():
        hashed_password = generate_password_hash('3713', method='pbkdf2:sha256')
        cursor.execute('INSERT INTO admin (username, password) VALUES (?, ?)', ('admin', hashed_password))

    conn.commit()
    conn.close()


def import_csv(filepath):
    """Read CSV and insert data into the student table."""
    conn = get_db()
    cursor = conn.cursor()

    with open(filepath, 'r') as file:
        csv_reader = csv.reader(file)
        next(csv_reader)  # Skip header row

        for row in csv_reader:
            reg_no = row[0]  # Assuming CSV contains only Reg_no column
            cursor.execute("INSERT OR IGNORE INTO student (Reg_no) VALUES (?)", (reg_no,))

    conn.commit()
    conn.close()

def login_required(f):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM admin WHERE username=?', (username,))
        admin = cursor.fetchone()
        conn.close()

        if admin and check_password_hash(admin['password'], password):
            session['user_id'] = admin['id']
            flash('You were logged in', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM student')
    students = cursor.fetchall()
    conn.close()
    return render_template('class_details.html',students=students)

@app.route('/take_attendance', methods=['GET','POST'])
@login_required
def take_attendance():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM student')
    students = cursor.fetchall()
    attendance_date = date.today().isoformat()

    if request.method == 'POST':
        for student in students:
            status = request.form.get(f'attendance_{student["Reg_no"]}', 'Absent')
            cursor.execute('''
                        INSERT INTO attendance (Reg_no, date, status) 
                        VALUES (?, ?, ?)
                    ''', (student['Reg_no'], attendance_date, status))

        conn.commit()
        conn.close()

        flash("Attendance recorded successfully", "success")
        return redirect(url_for('dashboard'))

    return render_template('take_attendance.html', students=students)


@app.route('/attendance_report/<string:reg_no>')
@login_required
def attendance_report(reg_no):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM attendance WHERE Reg_no=?', (reg_no,))
    student = cursor.fetchone()

    if not student:
        flash('Student Not Found', 'error')
        return redirect(url_for('dashboard'))

    # Get attendance records
    cursor.execute('SELECT * FROM attendance WHERE Reg_no = ? ORDER BY date DESC', (reg_no,))
    attendances = cursor.fetchall()

    # Attendance statistics
    total_days = len(attendances)
    present_days = len([a for a in attendances if a['status'] == 'Present'])
    late_days = len([a for a in attendances if a['status'] == 'Late'])
    absent_days = len([a for a in attendances if a['status'] == 'Absent'])

    attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0

    conn.close()

    return render_template('attendance_report.html',
                           student=student,
                           attendances=attendances,
                           total_days=total_days,
                           present_days=present_days,
                           late_days=late_days,
                           absent_days=absent_days,
                           attendance_percentage=round(attendance_percentage, 2))


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_csv():
    """Handle CSV file upload and import."""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            import_csv(filepath)  # Process CSV after saving
            flash('CSV file successfully uploaded and imported!', 'success')
            return redirect(url_for('upload_csv'))

    return render_template('upload.html')

@app.route('/modify_attendance_date/<string:attendance_date>', methods=['GET', 'POST'])
@login_required
def modify_attendance_date(attendance_date):
    """Modify attendance for a specific date."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get all students
    cursor.execute('SELECT * FROM student')
    students = cursor.fetchall()
    
    # Get existing attendance for this date
    student_attendance = {}
    cursor.execute('SELECT Reg_no, status FROM attendance WHERE date = ?', (attendance_date,))
    existing_attendance = cursor.fetchall()
    
    for record in existing_attendance:
        student_attendance[record['Reg_no']] = record['status']
    
    if request.method == 'POST':
        # Delete existing attendance for this date
        cursor.execute('DELETE FROM attendance WHERE date = ?', (attendance_date,))
        
        # Insert updated attendance
        for student in students:
            status = request.form.get(f'attendance_{student["Reg_no"]}', 'Absent')
            cursor.execute('''
                INSERT INTO attendance (Reg_no, date, status) 
                VALUES (?, ?, ?)
            ''', (student['Reg_no'], attendance_date, status))
        
        conn.commit()
        conn.close()
        
        flash(f"Attendance for {attendance_date} updated successfully", "success")
        return redirect(url_for('attendance_dates'))
    
    conn.close()
    
    return render_template('modify_attendance.html', 
                           students=students, 
                           attendance_date=attendance_date,
                           student_attendance=student_attendance)

@app.route('/attendance_dates')
@login_required
def attendance_dates():
    """Show all dates for which attendance was recorded."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get distinct dates with attendance records
    cursor.execute('SELECT DISTINCT date FROM attendance ORDER BY date DESC')
    dates = cursor.fetchall()
    
    conn.close()
    
    return render_template('attendance_dates.html', dates=dates)

@app.route('/delete_attendance_date/<string:attendance_date>', methods=['POST'])
@login_required
def delete_attendance_date(attendance_date):
    """Delete attendance for a specific date."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM attendance WHERE date = ?', (attendance_date,))
    conn.commit()
    conn.close()
    
    flash(f"Attendance for {attendance_date} deleted successfully", "success")
    return redirect(url_for('attendance_dates'))

if __name__ == "__main__":
    # Create a logger with a simpler configuration
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Initialize the database
    init_db()

    port = 8080
    url = f"http://localhost:{port}"

    def open_browser():
        time.sleep(2)  # Give server time to start

        try:
            system = platform.system()
            release = platform.uname().release

            # If inside WSL, use powershell.exe to open the browser on Windows side
            if "microsoft" in release.lower():
                subprocess.run(["powershell.exe", "Start-Process", url])
            else:
                webbrowser.open(url)
        except Exception as e:
            logger.warning(f"Could not open browser: {e}")

    threading.Thread(target=open_browser).start()

    # Run the Flask app
    app.run(debug=True, port=port)
