import os
import requests
from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import base64


app = Flask(__name__)

# Configuring the database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Define the database model
class QRCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(2083), nullable=False)
    qr_code_url = db.Column(db.String(2083), nullable=False)

    def __repr__(self):
        return f'<QRCode {self.url} - {self.qr_code_url}>'

# Initialize the database
with app.app_context():
    db.create_all()

QR_URL = "https://getqrcode.p.rapidapi.com/api/getQR"


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        print("Submitted URL:", url)

        params = {"forQR": url}
        headers = {
            "x-rapidapi-key": 'e978d93128msh9a0d23411ab8a0fp16dfbcjsn9c3c4d21f62b',
            "x-rapidapi-host": "getqrcode.p.rapidapi.com"
        }

        try:
            response = requests.get(QR_URL, headers=headers, params=params)
            print("Response Status Code:", response.status_code)

            if response.status_code == 200 and 'image/png' in response.headers.get('Content-Type'):
                qr_code_base64 = base64.b64encode(response.content).decode('utf-8')
                qr_code_data_url = f"data:image/png;base64,{qr_code_base64}"

                # Save the URL and QR code data URL in the database
                new_qr = QRCode(url=url, qr_code_url=qr_code_data_url)
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


@app.route("/result/<int:qr_id>")
def resultshow(qr_id):
    print("If you're reading this, the QR code was generated.")
    qr_code = QRCode.query.get(qr_id)
    if qr_code:
        return render_template("result.html", url=qr_code.url, qr_code_url=qr_code.qr_code_url)
    else:
        return "QR Code not found", 404


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3001))
    app.run(host='0.0.0.0', port=port, debug=True)
