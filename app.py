from flask import Flask, render_template, request, jsonify, session, redirect
import pickle
import sqlite3
import bcrypt
import os
import json
import logging
import pickle
import pandas as pd


# OCR
from PIL import Image
import pytesseract
from pdf2image import convert_from_bytes


# ---------------- CONFIG ----------------

app = Flask(__name__)
app.secret_key = "super_secret_key"

logging.basicConfig(level=logging.INFO)




UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

last_report_data = {}

# ---------------- DATABASE ----------------

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT
    )
    ''')

    conn.commit()
    conn.close()

init_db()


# ---------------- ROUTES ----------------

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    return render_template('dashboard.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---------------- SIGNUP ----------------

@app.route('/signup-user', methods=['POST'])
def signup_user():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        conn = sqlite3.connect('users.db')
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE email=?", (email,))
        if c.fetchone():
            return jsonify({"success": False, "message": "User exists"})

        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        c.execute("INSERT INTO users VALUES (NULL, ?, ?)", (email, hashed))
        conn.commit()
        conn.close()

    
        return jsonify({"success": True})

    except Exception as e:
        print("SIGNUP ERROR:", e)
        return jsonify({"success": False})

# ---------------- LOGIN ----------------

@app.route('/login-user', methods=['POST'])
def login_user():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        conn = sqlite3.connect('users.db')
        c = conn.cursor()

        c.execute("SELECT password FROM users WHERE email=?", (email,))
        user = c.fetchone()
        conn.close()

        if not user:
            return jsonify({"success": False, "message": "User not found"})

        if bcrypt.checkpw(password.encode(), user[0].encode()):
            session['user'] = email
            return jsonify({"success": True})

        return jsonify({"success": False, "message": "Wrong password"})

    except Exception as e:
        print("LOGIN ERROR:", e)
        return jsonify({"success": False})



# ---------------- GOOGLE LOGIN ----------------

@app.route('/google-login', methods=['POST'])
def google_login():
    email = request.json.get("email")

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE email=?", (email,))
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (NULL, ?, ?)", (email, "google"))

    conn.commit()
    conn.close()

    session['user'] = email
    return jsonify({"success": True})



diabetes_model = pickle.load(open("model/diabetes.pkl","rb"))
heart_model = pickle.load(open("model/heart.pkl","rb"))
# BP LOGIC (GLOBAL)
def bp_risk_score(bp, age, bmi):
    score = 0

    # Blood Pressure contribution
    if bp < 120:
        score += 0
    elif bp < 130:
        score += 10
    elif bp < 140:
        score += 25
    else:
        score += 40

    # Age contribution
    if age > 45:
        score += 10
    if age > 60:
        score += 10

    # BMI contribution
    if bmi > 25:
        score += 10
    if bmi > 30:
        score += 10

    return min(score, 100)

def health_score(diabetes, heart, bp_score):
    score = 100

    if diabetes == 1:
        score -= 30

    if heart == 1:
        score -= 30

    # BP contribution (scaled)
    score -= int(bp_score * 0.3)

    return max(score, 0)


# dashboard route
@app.route('/multi-predict', methods=['POST'])
def multi_predict():

    data = request.json

    import pandas as pd

    # DIABETES
    d_input = pd.DataFrame([{
    "age": data.get('age', 0),
    "hypertension": data.get('hypertension', 0),
    "bmi": data.get('bmi', 0),

    # 🔥 MATCH TRAINING NAMES EXACTLY
    "HbA1c_level": data.get('hba1c', 0),
    "blood_glucose_level": data.get('glucose', 0)
}])

    diabetes = diabetes_model.predict(d_input)[0]

    # HEART
    h_input = pd.DataFrame([{
    "Age": data.get('age', 0),
    "RestingBP": data.get('bp', 0),
    "Cholesterol": data.get('cholesterol', 0),
    "MaxHR": data.get('maxhr', 0)
}])

    heart = heart_model.predict(h_input)[0]

    # BP SCORE
    bp_score = bp_risk_score(
        data.get('bp', 0),
        data.get('age', 0),
        data.get('bmi', 0)
    )

    # FINAL HEALTH SCORE
    final_score = health_score(diabetes, heart, bp_score)

    return jsonify({
        "diabetes": int(diabetes),
        "heart": int(heart),
        "bp_score": int(bp_score),
        "health_score": int(final_score)
    })



@app.route('/upload-report', methods=['POST'])
def upload_report():

    file = request.files['file']
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    extracted = {}
    records = []

    # ---------- CSV ----------
    if file.filename.endswith('.csv'):
        df = pd.read_csv(filepath)

       
        df.columns = df.columns.str.lower().str.replace(" ", "").str.replace("_", "")

        def find_value(row, keywords):
            for col in row.keys():
                for key in keywords:
                    if key in col:
                        try:
                            return float(row[col])
                        except:
                            return 0
            return 0

        
        row = df.iloc[0]

        extracted = {
            "age": find_value(row, ["age"]),
            "bmi": find_value(row, ["bmi"]),
            "glucose": find_value(row, ["glucose"]),
            "hba1c": find_value(row, ["hba1c", "hb"]),
            "bp": find_value(row, ["bp", "pressure"]),
            "cholesterol": find_value(row, ["cholesterol"]),
            "maxhr": find_value(row, ["maxhr", "heartrate"]),
            "hypertension": find_value(row, ["hypertension"])
        }

        
        records = df.to_dict(orient="records")

    return jsonify({
        "first": extracted,  
        "data": records       
    })
    return data




import time

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_msg = data.get("message")

        time.sleep(2)  # avoid rate spam

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=user_msg
        )

        return jsonify({"reply": response.text})

    except Exception as e:
        print("Chat Error:", e)
        return jsonify({"reply": "AI busy, try again in few seconds"})
    



from flask import send_from_directory


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)
from reportlab.platypus import PageBreak

from datetime import datetime
import os
from reportlab.platypus import ListFlowable, ListItem
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

@app.route('/download-report', methods=['POST'])
def download_report():

    data = request.json or {}

    filename = f"health_report_{datetime.now().strftime('%H%M%S')}.pdf"
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    doc = SimpleDocTemplate(file_path)
    styles = getSampleStyleSheet()
    content = []

    # ================= HEADER =================
    def header(canvas, doc):
        canvas.saveState()

        canvas.setFillColor(colors.darkblue)
        canvas.rect(0, 800, 600, 50, fill=1)

        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 14)
        canvas.drawString(200, 820, "HealthAI Hospital Report")

        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(200, 20, "Confidential Medical Report")

        canvas.restoreState()

    # ================= PAGE 1 =================
    patient_id = f"PID-{datetime.now().strftime('%H%M%S')}"
    report_date = datetime.now().strftime("%d %B %Y")

    content.append(Spacer(1, 60))

    content.append(Paragraph("<b>Patient Information</b>", styles['Heading2']))
    content.append(Paragraph(f"Patient ID: {patient_id}", styles['Normal']))
    content.append(Paragraph(f"Date: {report_date}", styles['Normal']))
    content.append(Spacer(1, 20))

    # TABLE
    table_data = [
        ["Parameter", "Value"],
        ["Age", data.get('age')],
        ["BMI", data.get('bmi')],
        ["Glucose", data.get('glucose')],
        ["HbA1c", data.get('hba1c')],
        ["BP", data.get('bp')],
        ["Cholesterol", data.get('cholesterol')],
        ["Max HR", data.get('maxhr')],
    ]

    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('GRID',(0,0),(-1,-1),1,colors.grey),
    ]))

    content.append(table)
    content.append(Spacer(1, 20))

    # RISK BADGES
    content.append(Paragraph("<b>Risk Summary</b>", styles['Heading2']))

    def badge(text, color):
        return Paragraph(
            f'<para backColor="{color}"><font color="white">{text}</font></para>',
            styles['Normal']
        )

    content.append(badge(f"Diabetes: {data.get('diabetes')}", "#ff4d4d"))
    content.append(Spacer(1,5))
    content.append(badge(f"Heart: {data.get('heart')}", "#ffcc00"))
    content.append(Spacer(1,5))
    content.append(badge(f"BP Score: {data.get('bpRisk')}", "#00c6ff"))
    content.append(Spacer(1,5))
    content.append(badge(f"Health Score: {data.get('healthScore')}", "#00ff99"))

    content.append(PageBreak())

    # ================= PAGE 2 =================
    content.append(Paragraph("<b>Health Analysis</b>", styles['Heading2']))

    # CHART
    chart_path = os.path.join(UPLOAD_FOLDER, "chart.png")

    try:
        values = [
            100 if "High" in str(data.get('diabetes')) else 0,
            100 if "High" in str(data.get('heart')) else 0,
            int(''.join(filter(str.isdigit, str(data.get('bpRisk', 0))))) if data.get('bpRisk') else 0
        ]

        labels = ["Diabetes", "Heart", "BP"]

        plt.figure(figsize=(4,3))
        plt.bar(labels, values, color=['#ff4d4d','#ffcc00','#00c6ff'])
        plt.title("Health Risk Chart")
        plt.savefig(chart_path)
        plt.close()

        content.append(Image(chart_path, width=4*inch, height=3*inch))

    except Exception as e:
        print("Chart error:", e)

    content.append(Spacer(1, 20))

    # ================= AI EXPLANATION (FIXED) =================
    content.append(Paragraph("<b>AI Medical Explanation</b>", styles['Heading2']))
    content.append(Spacer(1, 10))

    # Risk
    risk_text = "High Risk" if "High" in str(data.get('diabetes')) or "High" in str(data.get('heart')) else "Moderate Risk"
    content.append(Paragraph(f"<b>Risk Level:</b> {risk_text}", styles['Normal']))
    content.append(Spacer(1, 8))

    # Key Factors
    content.append(Paragraph("<b>Key Factors</b>", styles['Normal']))

    key_factors = []

    if float(data.get("glucose", 0)) > 150:
        key_factors.append("High glucose / HbA1c")

    if "High" in str(data.get("heart")):
        key_factors.append("Heart risk")

    if float(data.get("bp", 0)) > 140:
        key_factors.append("Blood pressure risk")

    if not key_factors:
        key_factors.append("No major risk detected")

    content.append(ListFlowable(
        [ListItem(Paragraph(i, styles['Normal'])) for i in key_factors],
        bulletType='bullet'
    ))

    content.append(Spacer(1, 10))

    # Recommendations
    content.append(Paragraph("<b>Recommendations</b>", styles['Normal']))

    recommendations = []

    if float(data.get("glucose", 0)) > 150:
        recommendations.append("Reduce sugar intake")

    if "High" in str(data.get("heart")):
        recommendations.append("Avoid oily food")

    if float(data.get("bp", 0)) > 140:
        recommendations.append("Reduce salt & stress")

    if float(data.get("bmi", 0)) > 25:
        recommendations.append("Exercise and increase fiber intake")

    if not recommendations:
        recommendations.append("Maintain healthy lifestyle")

    content.append(ListFlowable(
        [ListItem(Paragraph(i, styles['Normal'])) for i in recommendations],
        bulletType='bullet'
    ))

    content.append(PageBreak())

    # ================= PAGE 3 =================
    content.append(Paragraph("<b>Doctor Review</b>", styles['Heading2']))
    content.append(Spacer(1, 40))

    content.append(Paragraph("Doctor Name: ____________________", styles['Normal']))
    content.append(Spacer(1, 30))
    content.append(Paragraph("Signature: ____________________", styles['Normal']))
    content.append(Spacer(1, 30))
    content.append(Paragraph("Date: ____________________", styles['Normal']))

    content.append(Spacer(1, 40))

    content.append(Paragraph(
        "This report is generated by HealthAI system. Please consult a certified doctor.",
        styles['Italic']
    ))

    content.append(Spacer(1, 20))

    # QR CODE
    from flask import request

    qr_data = request.host_url + f"uploads/{filename}"
    qr_code = qr.QrCodeWidget(qr_data)
    bounds = qr_code.getBounds()

    d = Drawing(100, 100)
    d.add(qr_code)

    content.append(Paragraph("<b>Scan to open report</b>", styles['Heading3']))
    content.append(d)

    # ================= BUILD =================
    doc.build(content, onFirstPage=header, onLaterPages=header)

    return jsonify({"file": f"/uploads/{filename}"})



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
