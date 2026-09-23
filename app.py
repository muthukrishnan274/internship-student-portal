import os
import sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "portal.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'student',
        department TEXT DEFAULT '',
        year TEXT DEFAULT '',
        phone TEXT DEFAULT '',
        skills TEXT DEFAULT '',
        resume TEXT DEFAULT '',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        company TEXT NOT NULL,
        location TEXT NOT NULL,
        job_type TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        skills TEXT DEFAULT '',
        deadline TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        job_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'Applied',
        applied_at TEXT NOT NULL,
        UNIQUE(user_id, job_id),
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(job_id) REFERENCES jobs(id)
    );
    """)
    admin = conn.execute("SELECT id FROM users WHERE email = ?", ("admin@campusconnect.com",)).fetchone()
    if not admin:
        conn.execute(
            "INSERT INTO users (name,email,password,role,created_at) VALUES (?,?,?,?,?)",
            ("Placement Admin", "admin@campusconnect.com",
             generate_password_hash("admin123"), "admin", datetime.now().isoformat())
        )
    count = conn.execute("SELECT COUNT(*) AS c FROM jobs").fetchone()["c"]
    if count == 0:
        demo_jobs = [
            ("Software Engineer Intern", "NovaTech Labs", "Chennai • Hybrid", "Internship", "Software",
             "Build production-ready web services with a collaborative engineering team.",
             "Python, Flask, SQL, Git", "2026-10-15"),
            ("Data Analyst", "InsightGrid", "Bengaluru • On-site", "Full-time", "Data",
             "Turn business data into dashboards, insights and measurable decisions.",
             "SQL, Python, Power BI, Excel", "2026-10-22"),
            ("UI/UX Design Intern", "PixelForge Studio", "Remote", "Internship", "Design",
             "Create polished product experiences and design systems for modern digital products.",
             "Figma, UX Research, Prototyping", "2026-10-28"),
            ("AI/ML Trainee", "Aether Systems", "Hyderabad • Hybrid", "Internship", "AI & ML",
             "Work on applied machine learning prototypes and data-driven experiments.",
             "Python, ML, Pandas, TensorFlow", "2026-11-02"),
            ("Cloud Support Associate", "SkyLayer", "Pune • Hybrid", "Full-time", "Cloud",
             "Support cloud workloads and automate repetitive infrastructure tasks.",
             "Linux, AWS, Networking", "2026-11-08")
        ]
        conn.executemany("""
            INSERT INTO jobs (title,company,location,job_type,category,description,skills,deadline,created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, [j + (datetime.now().isoformat(),) for j in demo_jobs])
    conn.commit()
    conn.close()

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return wrapper

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.context_processor
def inject_user():
    user = None
    if session.get("user_id"):
        conn = db()
        user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
        conn.close()
    return {"current_user": user}

@app.route("/")
def index():
    conn = db()
    jobs = conn.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT 6").fetchall()
    stats = {
        "jobs": conn.execute("SELECT COUNT(*) c FROM jobs").fetchone()["c"],
        "students": conn.execute("SELECT COUNT(*) c FROM users WHERE role='student'").fetchone()["c"],
        "applications": conn.execute("SELECT COUNT(*) c FROM applications").fetchone()["c"]
    }
    conn.close()
    return render_template("index.html", jobs=jobs, stats=stats)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        department = request.form.get("department", "")
        year = request.form.get("year", "")
        if not name or not email or not password:
            flash("Please complete all required fields.", "danger")
            return render_template("register.html")
        conn = db()
        try:
            conn.execute("""
                INSERT INTO users (name,email,password,role,department,year,created_at)
                VALUES (?,?,?,?,?,?,?)
            """, (name, email, generate_password_hash(password), "student", department, year, datetime.now().isoformat()))
            conn.commit()
            flash("Account created. You can now sign in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("That email is already registered.", "danger")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        conn = db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["name"] = user["name"]
            return redirect(url_for("admin_dashboard" if user["role"] == "admin" else "dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    conn = db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    applications = conn.execute("""
        SELECT applications.*, jobs.title, jobs.company, jobs.location
        FROM applications JOIN jobs ON jobs.id = applications.job_id
        WHERE applications.user_id = ? ORDER BY applications.id DESC
    """, (session["user_id"],)).fetchall()
    recommended = conn.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT 4").fetchall()
    conn.close()
    return render_template("dashboard.html", user=user, applications=applications, recommended=recommended)

@app.route("/jobs")
def jobs():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    job_type = request.args.get("type", "").strip()
    conn = db()
    sql = "SELECT * FROM jobs WHERE 1=1"
    params = []
    if q:
        sql += " AND (title LIKE ? OR company LIKE ? OR skills LIKE ? OR location LIKE ?)"
        like = f"%{q}%"
        params += [like, like, like, like]
    if category:
        sql += " AND category = ?"
        params.append(category)
    if job_type:
        sql += " AND job_type = ?"
        params.append(job_type)
    sql += " ORDER BY id DESC"
    job_rows = conn.execute(sql, params).fetchall()
    categories = conn.execute("SELECT DISTINCT category FROM jobs ORDER BY category").fetchall()
    conn.close()
    return render_template("jobs.html", jobs=job_rows, categories=categories, q=q, selected_category=category, selected_type=job_type)

@app.route("/jobs/<int:job_id>")
def job_detail(job_id):
    conn = db()
    job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    applied = False
    if session.get("user_id"):
        applied = conn.execute("SELECT id FROM applications WHERE user_id=? AND job_id=?",
                                (session["user_id"], job_id)).fetchone() is not None
    conn.close()
    if not job:
        flash("Job not found.", "danger")
        return redirect(url_for("jobs"))
    return render_template("job_detail.html", job=job, applied=applied)

@app.route("/apply/<int:job_id>", methods=["POST"])
@login_required
def apply(job_id):
    if session.get("role") == "admin":
        flash("Admin accounts cannot apply for jobs.", "warning")
        return redirect(url_for("job_detail", job_id=job_id))
    conn = db()
    try:
        conn.execute("INSERT INTO applications (user_id,job_id,status,applied_at) VALUES (?,?,?,?)",
                     (session["user_id"], job_id, "Applied", datetime.now().isoformat()))
        conn.commit()
        flash("Application submitted successfully.", "success")
    except sqlite3.IntegrityError:
        flash("You have already applied for this opportunity.", "warning")
    finally:
        conn.close()
    return redirect(url_for("job_detail", job_id=job_id))

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    conn = db()
    if request.method == "POST":
        name = request.form["name"].strip()
        phone = request.form.get("phone", "").strip()
        department = request.form.get("department", "").strip()
        year = request.form.get("year", "").strip()
        skills = request.form.get("skills", "").strip()
        resume = None
        file = request.files.get("resume")
        if file and file.filename:
            if not allowed_file(file.filename):
                flash("Resume must be PDF, DOC or DOCX.", "danger")
                conn.close()
                return redirect(url_for("profile"))
            safe = secure_filename(file.filename)
            resume = f"{session['user_id']}_{safe}"
            file.save(os.path.join(UPLOAD_DIR, resume))
        if resume:
            conn.execute("""UPDATE users SET name=?,phone=?,department=?,year=?,skills=?,resume=? WHERE id=?""",
                         (name, phone, department, year, skills, resume, session["user_id"]))
        else:
            conn.execute("""UPDATE users SET name=?,phone=?,department=?,year=?,skills=? WHERE id=?""",
                         (name, phone, department, year, skills, session["user_id"]))
        conn.commit()
        session["name"] = name
        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile"))
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    conn.close()
    return render_template("profile.html", user=user)

@app.route("/resume/<filename>")
@login_required
def resume(filename):
    conn = db()
    owner = conn.execute("SELECT id FROM users WHERE resume = ?", (filename,)).fetchone()
    conn.close()
    if not owner or owner["id"] != session["user_id"]:
        return ("Unauthorized", 403)
    return send_from_directory(UPLOAD_DIR, filename, as_attachment=True)

@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = db()
    stats = {
        "jobs": conn.execute("SELECT COUNT(*) c FROM jobs").fetchone()["c"],
        "students": conn.execute("SELECT COUNT(*) c FROM users WHERE role='student'").fetchone()["c"],
        "applications": conn.execute("SELECT COUNT(*) c FROM applications").fetchone()["c"],
        "pending": conn.execute("SELECT COUNT(*) c FROM applications WHERE status='Applied'").fetchone()["c"]
    }
    applications = conn.execute("""
        SELECT applications.id, applications.status, applications.applied_at,
               users.name student, users.email, jobs.title, jobs.company
        FROM applications
        JOIN users ON users.id=applications.user_id
        JOIN jobs ON jobs.id=applications.job_id
        ORDER BY applications.id DESC
    """).fetchall()
    jobs_rows = conn.execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin.html", stats=stats, applications=applications, jobs=jobs_rows)

@app.route("/admin/jobs/add", methods=["POST"])
@admin_required
def admin_add_job():
    fields = ["title", "company", "location", "job_type", "category", "description", "skills", "deadline"]
    data = {f: request.form.get(f, "").strip() for f in fields}
    if not all(data.values()):
        flash("Please fill every job field.", "danger")
        return redirect(url_for("admin_dashboard"))
    conn = db()
    conn.execute("""
        INSERT INTO jobs (title,company,location,job_type,category,description,skills,deadline,created_at)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, tuple(data.values()) + (datetime.now().isoformat(),))
    conn.commit()
    conn.close()
    flash("Opportunity published.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/jobs/delete/<int:job_id>", methods=["POST"])
@admin_required
def admin_delete_job(job_id):
    conn = db()
    conn.execute("DELETE FROM applications WHERE job_id=?", (job_id,))
    conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))
    conn.commit()
    conn.close()
    flash("Job posting removed.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/applications/<int:app_id>/status", methods=["POST"])
@admin_required
def update_application(app_id):
    status = request.form.get("status", "Applied")
    allowed = {"Applied", "Shortlisted", "Interview", "Selected", "Rejected"}
    if status not in allowed:
        flash("Invalid application status.", "danger")
        return redirect(url_for("admin_dashboard"))
    conn = db()
    conn.execute("UPDATE applications SET status=? WHERE id=?", (status, app_id))
    conn.commit()
    conn.close()
    flash("Application status updated.", "success")
    return redirect(url_for("admin_dashboard"))

@app.errorhandler(413)
def too_large(_):
    flash("File is too large. Maximum size is 5 MB.", "danger")
    return redirect(request.referrer or url_for("profile"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
