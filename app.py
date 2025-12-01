from flask import Flask, render_template, request, jsonify, Response, send_file
import sqlite3
from datetime import datetime
import os
import csv
import io

app = Flask(__name__)

# ------------------------ DATABASE SETUP ------------------------

DB_PATH = os.path.join(os.path.dirname(__file__), "chatbot.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            message TEXT,
            ts TEXT
        )
    ''')
    conn.commit()
    conn.close()

def log_message(role, message, ts=None):
    if ts is None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO messages (role, message, ts) VALUES (?, ?, ?)", (role, message, ts))
    conn.commit()
    conn.close()

def clear_messages():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM messages")
    conn.commit()
    conn.close()

# ------------------------ COLLEGE INFORMATION (editable) ------------------------
# Edit these fields to match your college details
college_info = {
    "name": "Your College Name",
    "short_name": "ABC College",
    "about": "ABC College is a reputed institution offering undergraduate and diploma courses in science, commerce and arts. Founded in 19XX, it focuses on academic excellence and practical training.",
    "address": "Street name, City, State, PIN",
    "phone": "+91-XXXXXXXXXX",
    "email": "info@abccollege.edu.in",
    "website": "http://www.abccollege.edu.in",
    "principal": "Dr. Firstname Lastname",
    "admissions": "Admissions open from June 1 to July 31. Visit admissions page or contact the office for details.",
    "courses": [
        {"name": "B.Sc. (Computer Science)", "duration": "3 years"},
        {"name": "B.A. (Economics)", "duration": "3 years"},
        {"name": "B.Com", "duration": "3 years"},
        {"name": "Diploma in IT", "duration": "1 year"}
    ],
    "departments": ["Computer Science", "Mathematics", "Physics", "Commerce", "Economics"],
    "events": [
        {"title": "Freshers Day", "date": "2025-08-10"},
        {"title": "Tech Fest", "date": "2025-09-12"}
    ],
    "faculty_contact": [
        {"name": "Prof. A", "dept": "Computer Science", "email": "a@abccollege.edu.in"},
        {"name": "Dr. B", "dept": "Mathematics", "email": "b@abccollege.edu.in"}
    ]
}

# ------------------------ CHATBOT LOGIC ------------------------

def chatbot_response(message):
    msg = message.lower().strip()

    # College quick queries
    if msg == "__greet__":
        return f"Hello! Welcome to {college_info['short_name']}. Ask about courses, admissions, contact, or events."
    if "about college" in msg or "about" == msg:
        return college_info.get("about")
    if "courses" in msg or "what courses" in msg:
        return "Courses: " + ", ".join([c["name"] for c in college_info.get("courses", [])])
    if "departments" in msg or "department" in msg:
        return "Departments: " + ", ".join(college_info.get("departments", []))
    if "events" in msg or "event" in msg:
        return "Upcoming events: " + ", ".join([f'{e["title"]} ({e["date"]})' for e in college_info.get("events", [])])
    if "principal" in msg or "who is principal" in msg:
        return f"Principal: {college_info.get('principal')}"
    if "address" in msg or "location" in msg:
        return f"{college_info.get('address')} (Phone: {college_info.get('phone')})"
    if "contact" in msg or "phone" in msg or "email" in msg:
        return f"Phone: {college_info.get('phone')}, Email: {college_info.get('email')}"
    if "admission" in msg or "admissions" in msg:
        return college_info.get("admissions")
    if "faculty" in msg:
        fac = college_info.get("faculty_contact", [])
        return "Faculty: " + ", ".join([f'{f["name"]} ({f["dept"]})' for f in fac])

    # Basic conversational replies
    if "hello" in msg or "hi" in msg:
        return "Hello! How can I assist you? Ask about courses, admissions, contact, or events."
    if "how are you" in msg:
        return "I'm fine — ready to help you with your college queries!"
    if "your name" in msg:
        return "I am your College Chatbot 🤖"
    if "joke" in msg:
        return "Why did the programmer quit his job? Because he didn't get arrays (a raise)!"
    if "bye" in msg:
        return "Goodbye! Good luck."

    return "Sorry, I didn't understand that. Try asking about admissions, courses, contact, or 'tell me a joke'."

# ------------------------ ROUTES ------------------------

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/get", methods=["POST"])
def get_bot_response():
    user_msg = request.form.get("msg", "").strip()
    ts_user = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if user_msg:
        log_message("user", user_msg, ts_user)

    bot_reply = chatbot_response(user_msg)
    ts_bot = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message("bot", bot_reply, ts_bot)

    return jsonify({"response": bot_reply, "bot_ts": ts_bot})

@app.route("/greet", methods=["GET"])
def greet():
    bot_reply = chatbot_response("__greet__")
    ts_bot = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message("bot", bot_reply, ts_bot)
    return jsonify({"response": bot_reply, "bot_ts": ts_bot})

# History (JSON)
@app.route("/history", methods=["GET"])
def history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, role, message, ts FROM messages ORDER BY id DESC LIMIT 200")
    rows = c.fetchall()
    conn.close()
    rows.reverse()
    data = [{"id": r[0], "role": r[1], "message": r[2], "ts": r[3]} for r in rows]
    return jsonify({"history": data})

# ----------------- Admin UI, Export CSV, Clear DB -----------------

@app.route("/admin")
def admin_page():
    return render_template("admin.html")

@app.route("/export_csv")
def export_csv():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, role, message, ts FROM messages ORDER BY id ASC")
    rows = c.fetchall()
    conn.close()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "role", "message", "ts"])
    for r in rows:
        writer.writerow([r[0], r[1], r[2], r[3]])
    csv_data = output.getvalue()
    output.close()

    return Response(csv_data, mimetype="text/csv",
                    headers={"Content-Disposition":"attachment;filename=chat_history.csv"})

@app.route("/clear_db", methods=["POST"])
def clear_db_endpoint():
    try:
        clear_messages()
        return jsonify({"status":"ok"})
    except Exception as e:
        return jsonify({"status":"error", "error": str(e)}), 500

# ------------------------ START SERVER ------------------------

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)