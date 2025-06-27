from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
import datetime

app = Flask(__name__)
app.secret_key = 'medtrack_secret'

# Database Config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///medtrack.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ---------------- Models ---------------- #
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(10))  # 'doctor' or 'patient'
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    license = db.Column(db.String(50))  # Only for doctors
    specialization = db.Column(db.String(50))  # Only for doctors
    age = db.Column(db.Integer)  # Only for patients
    gender = db.Column(db.String(10))  # Only for patients

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_email = db.Column(db.String(100))
    specialist = db.Column(db.String(100))
    date = db.Column(db.String(20))
    time = db.Column(db.String(20))
    reason = db.Column(db.String(200))

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    subject = db.Column(db.String(200))
    message = db.Column(db.Text)

# ---------------- Routes ---------------- #

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        message = ContactMessage(
            name=request.form['name'],
            email=request.form['email'],
            subject=request.form['subject'],
            message=request.form['message']
        )
        db.session.add(message)
        db.session.commit()
        flash('Your message has been sent successfully!', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        role = request.form.get('role')
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('signup'))

        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('signup'))

        user = User(role=role, name=name, email=email, password=password)

        if role == 'doctor':
            user.license = request.form.get('license')
            user.specialization = request.form.get('specialization')
        elif role == 'patient':
            user.age = request.form.get('age')
            user.gender = request.form.get('gender')

        db.session.add(user)
        db.session.commit()
        flash(f'{role.capitalize()} signup successful!', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form['role']
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email, role=role, password=password).first()

        if user:
            session['user'] = {'email': email, 'role': role, 'name': user.name}
            return redirect(url_for(f'{role}_dashboard'))
        flash('Invalid credentials!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/doctor/dashboard')
def doctor_dashboard():
    user = session.get('user')
    if not user or user['role'] != 'doctor':
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    doctor = User.query.filter_by(email=user['email']).first()
    appointments = Appointment.query.filter_by(specialist=doctor.specialization).all()
    patients = User.query.filter_by(role='patient').all()
    return render_template('doctor_dashboard.html', doctor=doctor, appointments=appointments, patients=patients)

@app.route('/patient/dashboard')
def patient_dashboard():
    user = session.get('user')
    if not user or user['role'] != 'patient':
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    appointments = Appointment.query.filter_by(patient_email=user['email']).all()
    doctors = User.query.filter_by(role='doctor').all()
    return render_template('patient_dashboard.html', user=user['name'], appointments=appointments, doctors=doctors)

@app.route('/doctor/details')
def doctor_details():
    doctors = User.query.filter_by(role='doctor').all()
    return render_template('doctor_details.html', doctors=doctors)

@app.route('/patient/details')
def patient_details():
    patients = User.query.filter_by(role='patient').all()
    return render_template('patient_details.html', patients=patients)

@app.route('/patient/appointment', methods=['GET', 'POST'])
def appointment():
    if 'user' not in session or session['user']['role'] != 'patient':
        flash('Please log in as a patient.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        appt = Appointment(
            patient_email=session['user']['email'],
            specialist=request.form['specialist'],
            date=request.form['date'],
            time=request.form['time'],
            reason=request.form['reason']
        )
        db.session.add(appt)
        db.session.commit()
        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('appointment'))

    return render_template('appointment.html', user=session['user'])

# ---------------- Main ---------------- #
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
