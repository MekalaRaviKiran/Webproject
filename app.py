from flask import Flask, render_template, request, redirect, url_for, session, flash
import boto3
import uuid
from botocore.exceptions import ClientError

app = Flask(_name_)
app.secret_key = 'medtrack_secret'

# AWS Setup
dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
sns_client = boto3.client('sns', region_name='ap-south-1')
TOPIC_ARN = 'arn:aws:sns:ap-south-1:123456789012:YourTopicName'  # Replace with your real ARN

# DynamoDB Tables
users_table = dynamodb.Table('Users')
appointments_table = dynamodb.Table('Appointments')


def send_sns_notification(message, subject='MedTrack Alert'):
    try:
        sns_client.publish(
            TopicArn=TOPIC_ARN,
            Message=message,
            Subject=subject
        )
    except ClientError as e:
        print("SNS Error:", e.response['Error']['Message'])


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        role = request.form['role']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm_password']

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('signup'))

        try:
            # Check if user already exists
            if 'Item' in users_table.get_item(Key={'email': email}):
                flash('Email already exists.', 'danger')
                return redirect(url_for('signup'))

            user = {
                'email': email,
                'password': password,
                'role': role,
                'name': request.form['name']
            }

            if role == 'doctor':
                user['license'] = request.form['license']
                user['specialization'] = request.form['specialization']
            else:
                user['age'] = request.form['age']
                user['gender'] = request.form['gender']

            users_table.put_item(Item=user)
            flash(f'{role.capitalize()} registered successfully!', 'success')
            return redirect(url_for('login'))
        except ClientError as e:
            flash("Error: " + e.response['Error']['Message'], 'danger')

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        try:
            user = users_table.get_item(Key={'email': email}).get('Item')
            if user and user['password'] == password and user['role'] == role:
                session['user'] = {'email': email, 'role': role, 'name': user['name']}
                return redirect(url_for(f'{role}_dashboard'))
            flash('Invalid credentials.', 'danger')
        except:
            flash('Login failed.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/doctor/dashboard')
def doctor_dashboard():
    user = session.get('user')
    if not user or user['role'] != 'doctor':
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    doctor_email = user['email']
    doctor = users_table.get_item(Key={'email': doctor_email}).get('Item')
    spec = doctor.get('specialization')

    all_appts = appointments_table.scan().get('Items', [])
    appointments = [a for a in all_appts if a['specialist'] == spec]

    patients = [u for u in users_table.scan().get('Items', []) if u['role'] == 'patient']

    return render_template('doctor_dashboard.html', doctor=doctor, appointments=appointments, patients=patients)


@app.route('/patient/dashboard')
def patient_dashboard():
    user = session.get('user')
    if not user or user['role'] != 'patient':
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))

    all_appts = appointments_table.scan().get('Items', [])
    appointments = [a for a in all_appts if a['patient_email'] == user['email']]

    doctors = [u for u in users_table.scan().get('Items', []) if u['role'] == 'doctor']

    return render_template('patient_dashboard.html', user=user['name'], appointments=appointments, doctors=doctors)


@app.route('/patient/appointment', methods=['GET', 'POST'])
def appointment():
    if 'user' not in session or session['user']['role'] != 'patient':
        flash('Login as a patient.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        appt = {
            'appointment_id': str(uuid.uuid4()),
            'patient_email': session['user']['email'],
            'specialist': request.form['specialist'],
            'date': request.form['date'],
            'time': request.form['time'],
            'reason': request.form['reason']
        }
        appointments_table.put_item(Item=appt)

        msg = f"New appointment for {appt['patient_email']} with {appt['specialist']} on {appt['date']} at {appt['time']}"
        send_sns_notification(msg)

        flash('Appointment booked successfully.', 'success')
        return redirect(url_for('appointment'))

    return render_template('appointment.html', user=session['user'])


@app.route('/patient/details')
def patient_details():
    patients = [u for u in users_table.scan().get('Items', []) if u['role'] == 'patient']
    return render_template('patient_details.html', patients=patients)


@app.route('/doctor/details')
def doctor_details():
    doctors = [u for u in users_table.scan().get('Items', []) if u['role'] == 'doctor']
    return render_template('doctor_details.html', doctors=doctors)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        flash('We received your message!', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')


if _name_ == '_main_':
    app.run(debug=True)
