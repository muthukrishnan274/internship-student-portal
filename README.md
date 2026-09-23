# CampusConnect — Student Placement & Internship Portal

A professional full-stack Flask + SQLite portal for students to discover opportunities, upload resumes, apply, track application status, and for placement admins to manage job postings and applications.

## Core features
- Student registration/login
- Student profile and resume upload
- Internship/job listings
- Search and filters
- Job detail pages
- One-click application
- Application status tracking
- Admin dashboard
- Add/delete job postings
- Update application status
- Responsive premium UI
- SQLite database with password hashing

## Demo admin
- Email: `admin@campusconnect.com`
- Password: `admin123`

Change the demo credentials before real deployment.

## Run locally

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

The database is created automatically on first run.

## Production
Use a strong `SECRET_KEY` environment variable and run with Gunicorn, for example:

```bash
gunicorn app:app
```
