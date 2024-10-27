import os
import requests
import base64
from flask import Flask, request, render_template, redirect, url_for, flash
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_bcrypt import Bcrypt
from forms import RegistrationForm, LoginForm # imports the forms from forms.py
from models import db, User, QRCode # imports the models

app = Flask(__name__)

# Configurations
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Initialize extensions
db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Initialize the database
with app.app_context():
    db.create_all()

QR_URL = "https://getqrcode.p.rapidapi.com/api/getQR"

# User loader callback for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')  # Use Flask-Bcrypt
        new_user = User(username=form.username.data, password=hashed_password)

        # Add the new user to the database
        db.session.add(new_user)
        db.session.commit()

        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/my_qrs')
@login_required
def my_qrs():
    user_qrcodes = QRCode.query.filter_by(user_id=current_user.id).all()
    return render_template('my_qrs.html', qrcodes=user_qrcodes)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Login failed. Please check your username and password.', 'danger')
    
    return render_template('login.html', form=form)



# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Home page for QR code generation
@app.route('/', methods=['GET', 'POST'])
def index():        
    if request.method == 'POST':
        if not current_user.is_authenticated:
            return render_template('index.html', error="You must be logged in to generate QR codes.")
        
        url = request.form['url']
        print("Submitted URL:", url)

        params = {"forQR": url}
        headers = {
            "x-rapidapi-key": os.environ.get('RAPIDAPI_KEY'),
            "x-rapidapi-host": "getqrcode.p.rapidapi.com"
        }

        try:
            response = requests.get(QR_URL, headers=headers, params=params)
            print("Response Status Code:", response.status_code)

            if response.status_code == 200 and 'image/png' in response.headers.get('Content-Type'):
                qr_code_base64 = base64.b64encode(response.content).decode('utf-8')
                qr_code_data_url = f"data:image/png;base64,{qr_code_base64}"

                # Save the URL, QR code data URL, and the logged-in user's ID in the database
                new_qr = QRCode(url=url, qr_code_url=qr_code_data_url, user_id=current_user.id)
                db.session.add(new_qr)
                db.session.commit()

                print("QR Code saved with ID:", new_qr.id)  # Debugging line
                return redirect(url_for('resultshow', qr_id=new_qr.id))
            else:
                return render_template('index.html', error="Unexpected response format or status code")

        except Exception as e:
            print(f"Error: {e}")
            return render_template('index.html', error="An error occurred while generating the QR code")

    return render_template('index.html')

@app.route('/delete_qr_code/<int:qr_code_id>', methods=['POST'])
@login_required
def delete_qr_code(qr_code_id):
    qr_code = QRCode.query.get(qr_code_id)
    if qr_code:
        db.session.delete(qr_code)
        db.session.commit()
        flash('QR code deleted successfully!', 'success')
    else:
        flash('QR code not found.', 'danger')
    return redirect(url_for('my_qrs'))  # Redirect to the index or wherever you want


# Route to show generated QR code
@app.route("/result/<int:qr_id>")
def resultshow(qr_id):
    qr_code = QRCode.query.get(qr_id)
    if qr_code:
        return render_template("result.html", url=qr_code.url, qr_code_url=qr_code.qr_code_url)
    else:
        return "QR Code not found", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3001))
    app.run(host='0.0.0.0', port=port, debug=True)
