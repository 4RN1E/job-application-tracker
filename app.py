"""Job Application Tracker - main Flask application.

Pages: Dashboard, Companies, Jobs, Applications, Contacts, Job Match.
Every table has full CRUD: list, detail, add, edit, and delete-with-confirmation.
All SQL uses %s placeholders (never string formatting) to prevent SQL injection.
"""
import json
import os
import re
from datetime import date, datetime

import mysql.connector
from flask import Flask, abort, flash, redirect, render_template, request, url_for

from database import execute, fetch_all, fetch_one, load_json
from matching import parse_skills, rank_jobs, top_missing_skills

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")

JOB_TYPES = ["Full-time", "Part-time", "Contract", "Internship"]
STATUSES = ["Applied", "Screening", "Interview", "Offer", "Accepted", "Rejected", "Withdrawn"]
INTERVIEW_TYPES = ["Phone screen", "Video call", "Technical", "On-site", "Behavioral", "Other"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------
@app.template_filter("salary")
def salary_filter(job):
    """'$75,000 - $95,000', '$75,000+', 'Up to $95,000', or an em dash."""
    low, high = job.get("salary_min"), job.get("salary_max")
    if low is not None and high is not None:
        return f"${low:,} – ${high:,}"
    if low is not None:
        return f"${low:,}+"
    if high is not None:
        return f"Up to ${high:,}"
    return "—"


@app.template_filter("nice_date")
def nice_date_filter(value):
    """Show dates as 'Nov 15, 2026'. Accepts date objects or ISO strings."""
    if not value:
        return "—"
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return value
    return f"{value.strftime('%b')} {value.day}, {value.year}"


@app.template_filter("zip")
def zip_filter(first, second):
    """Pair two lists for <select> options: [(value, label), ...]."""
    return list(zip(first, second))


@app.context_processor
def inject_globals():
    return {"STATUSES": STATUSES, "JOB_TYPES": JOB_TYPES, "INTERVIEW_TYPES": INTERVIEW_TYPES}


# ---------------------------------------------------------------------
# Validation helpers - each appends to `errors` instead of raising, so a
# form can show every problem at once.
# ---------------------------------------------------------------------
def get_text(form, name, label, errors, max_len=None, required=False):
    value = (form.get(name) or "").strip()
    if not value:
        if required:
            errors.append(f"{label} is required.")
        return None
    if max_len and len(value) > max_len:
        errors.append(f"{label} must be {max_len} characters or fewer.")
    return value


def get_url(form, name, label, errors, max_len):
    value = get_text(form, name, label, errors, max_len)
    if value and not re.match(r"^https?://\S+$", value, re.IGNORECASE):
        errors.append(f"{label} must start with http:// or https://")
    return value


def get_email(form, name, label, errors, max_len):
    value = get_text(form, name, label, errors, max_len)
    if value and not EMAIL_RE.match(value):
        errors.append(f"{label} doesn't look like a valid email address.")
    return value


def get_date(form, name, label, errors, required=False):
    value = (form.get(name) or "").strip()
    if not value:
        if required:
            errors.append(f"{label} is required.")
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        errors.append(f"{label} must be a valid date.")
        return None


def get_int(form, name, label, errors):
    value = (form.get(name) or "").strip()
    if not value:
        return None
    try:
        number = int(value)
    except ValueError:
        errors.append(f"{label} must be a whole number.")
        return None
    if number < 0:
        errors.append(f"{label} cannot be negative.")
        return None
    return number


def get_choice(form, name, label, options, errors):
    value = (form.get(name) or "").strip()
    if value not in options:
        errors.append(f"Please choose a valid {label}.")
        return None
    return value


def get_foreign_key(form, name, label, table, pk, errors):
    """Check that the chosen parent row exists. table/pk are our own constants."""
    value = (form.get(name) or "").strip()
    if not value.isdigit():
        errors.append(f"Please choose a {label}.")
        return None
    if not fetch_one(f"SELECT 1 FROM {table} WHERE {pk} = %s", (int(value),)):
        errors.append(f"That {label} no longer exists.")
        return None
    return int(value)


def get_or_404(sql, params):
    row = fetch_one(sql, params)
    if row is None:
        abort(404)
    return row


# ---------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------
@app.route("/")
def dashboard():
    totals = fetch_one(
        """SELECT
               (SELECT COUNT(*) FROM companies)    AS companies,
               (SELECT COUNT(*) FROM jobs)         AS jobs,
               (SELECT COUNT(*) FROM applications) AS applications,
               (SELECT COUNT(*) FROM contacts)     AS contacts"""
    )

    counts = {r["status"]: r["n"] for r in fetch_all(
        "SELECT status, COUNT(*) AS n FROM applications GROUP BY status")}
    by_status = [{"status": s, "count": counts.get(s, 0)} for s in STATUSES]
    total_apps = totals["applications"] or 0
    for row in by_status:
        row["pct"] = round(100 * row["count"] / total_apps) if total_apps else 0

    active = sum(counts.get(s, 0) for s in ("Applied", "Screening", "Interview"))
    # Share of applications that got any human response (everything past Applied,
    # excluding ones you withdrew yourself)
    responded = sum(counts.get(s, 0) for s in ("Screening", "Interview", "Offer", "Accepted", "Rejected"))
    countable = total_apps - counts.get("Withdrawn", 0)
    response_rate = round(100 * responded / countable) if countable else 0

    recent = fetch_all(
        """SELECT a.application_id, a.application_date, a.status,
                  j.job_title, c.company_name
           FROM applications a
           JOIN jobs j      ON j.job_id = a.job_id
           JOIN companies c ON c.company_id = j.company_id
           ORDER BY a.application_date DESC, a.application_id DESC
           LIMIT 5"""
    )

    # interview_data is JSON, so filter upcoming interviews in Python
    upcoming = []
    rows = fetch_all(
        """SELECT a.application_id, a.interview_data, j.job_title, c.company_name
           FROM applications a
           JOIN jobs j      ON j.job_id = a.job_id
           JOIN companies c ON c.company_id = j.company_id
           WHERE a.interview_data IS NOT NULL
             AND a.status NOT IN ('Rejected', 'Withdrawn')"""
    )
    today = date.today().isoformat()
    for row in rows:
        data = load_json(row["interview_data"], {}) or {}
        if data.get("date") and data["date"] >= today:
            upcoming.append({**row, "interview": data})
    upcoming.sort(key=lambda r: r["interview"]["date"])

    return render_template(
        "dashboard.html", totals=totals, by_status=by_status, active=active,
        offers=counts.get("Offer", 0) + counts.get("Accepted", 0),  # offers received
        response_rate=response_rate,
        recent=recent, upcoming=upcoming[:5],
    )


# ---------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------
def validate_company(form):
    errors = []
    data = {
        "company_name": get_text(form, "company_name", "Company name", errors, 100, required=True),
        "industry": get_text(form, "industry", "Industry", errors, 50),
        "website": get_url(form, "website", "Website", errors, 200),
        "city": get_text(form, "city", "City", errors, 50),
        "state": get_text(form, "state", "State", errors, 50),
        "notes": get_text(form, "notes", "Notes", errors),
    }
    return data, errors


@app.route("/companies")
def companies():
    rows = fetch_all(
        """SELECT c.*,
                  (SELECT COUNT(*) FROM jobs j     WHERE j.company_id = c.company_id) AS job_count,
                  (SELECT COUNT(*) FROM contacts t WHERE t.company_id = c.company_id) AS contact_count
           FROM companies c
           ORDER BY c.company_name"""
    )
    return render_template("companies.html", companies=rows)


@app.route("/companies/<int:company_id>")
def company_detail(company_id):
    company = get_or_404("SELECT * FROM companies WHERE company_id = %s", (company_id,))
    jobs = fetch_all(
        """SELECT j.*, (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.job_id) AS application_count
           FROM jobs j WHERE j.company_id = %s ORDER BY j.date_posted DESC, j.job_id DESC""",
        (company_id,),
    )
    contacts = fetch_all(
        "SELECT * FROM contacts WHERE company_id = %s ORDER BY contact_name", (company_id,))
    return render_template("company_detail.html", company=company, jobs=jobs, contacts=contacts)


@app.route("/companies/new", methods=["GET", "POST"])
def company_new():
    errors, values = [], {}
    if request.method == "POST":
        values = request.form
        data, errors = validate_company(request.form)
        if not errors:
            new_id = execute(
                """INSERT INTO companies (company_name, industry, website, city, state, notes)
                   VALUES (%(company_name)s, %(industry)s, %(website)s, %(city)s, %(state)s, %(notes)s)""",
                data,
            )
            flash("Company added.", "success")
            return redirect(url_for("company_detail", company_id=new_id))
    return render_template("company_form.html", values=values, errors=errors,
                           title="Add company", cancel_url=url_for("companies"))


@app.route("/companies/<int:company_id>/edit", methods=["GET", "POST"])
def company_edit(company_id):
    company = get_or_404("SELECT * FROM companies WHERE company_id = %s", (company_id,))
    errors, values = [], company
    if request.method == "POST":
        values = request.form
        data, errors = validate_company(request.form)
        if not errors:
            data["company_id"] = company_id
            execute(
                """UPDATE companies SET company_name=%(company_name)s, industry=%(industry)s,
                          website=%(website)s, city=%(city)s, state=%(state)s, notes=%(notes)s
                   WHERE company_id=%(company_id)s""",
                data,
            )
            flash("Company updated.", "success")
            return redirect(url_for("company_detail", company_id=company_id))
    return render_template("company_form.html", values=values, errors=errors,
                           title=f"Edit {company['company_name']}",
                           cancel_url=url_for("company_detail", company_id=company_id))


@app.route("/companies/<int:company_id>/delete", methods=["GET", "POST"])
def company_delete(company_id):
    company = get_or_404("SELECT * FROM companies WHERE company_id = %s", (company_id,))
    if request.method == "POST":
        execute("DELETE FROM companies WHERE company_id = %s", (company_id,))
        flash(f"Deleted {company['company_name']}.", "success")
        return redirect(url_for("companies"))
    counts = fetch_one(
        """SELECT (SELECT COUNT(*) FROM jobs WHERE company_id = %(id)s) AS jobs,
                  (SELECT COUNT(*) FROM applications a JOIN jobs j ON j.job_id = a.job_id
                    WHERE j.company_id = %(id)s) AS applications,
                  (SELECT COUNT(*) FROM contacts WHERE company_id = %(id)s) AS contacts""",
        {"id": company_id},
    )
    return render_template(
        "confirm_delete.html", kind="company", label=company["company_name"],
        cascade={"job(s)": counts["jobs"], "application(s)": counts["applications"],
                 "contact(s)": counts["contacts"]},
        cancel_url=url_for("company_detail", company_id=company_id))


# ---------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------
def company_choices():
    return fetch_all("SELECT company_id, company_name FROM companies ORDER BY company_name")


def validate_job(form):
    errors = []
    data = {
        "company_id": get_foreign_key(form, "company_id", "company", "companies", "company_id", errors),
        "job_title": get_text(form, "job_title", "Job title", errors, 100, required=True),
        "job_type": get_choice(form, "job_type", "job type", JOB_TYPES, errors),
        "salary_min": get_int(form, "salary_min", "Minimum salary", errors),
        "salary_max": get_int(form, "salary_max", "Maximum salary", errors),
        "job_url": get_url(form, "job_url", "Job URL", errors, 300),
        "date_posted": get_date(form, "date_posted", "Date posted", errors),
    }
    if (data["salary_min"] is not None and data["salary_max"] is not None
            and data["salary_min"] > data["salary_max"]):
        errors.append("Minimum salary cannot be greater than maximum salary.")
    skills = parse_skills(form.get("requirements", ""))
    data["requirements"] = json.dumps(skills) if skills else None
    return data, errors


def job_form_values(job):
    """Turn a jobs row into form values (JSON array -> 'Python, SQL')."""
    values = dict(job)
    values["requirements"] = ", ".join(load_json(job["requirements"], []) or [])
    return values


@app.route("/jobs")
def jobs():
    rows = fetch_all(
        """SELECT j.*, c.company_name,
                  (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.job_id) AS application_count
           FROM jobs j JOIN companies c ON c.company_id = j.company_id
           ORDER BY j.date_posted DESC, j.job_id DESC"""
    )
    for row in rows:
        row["requirements"] = load_json(row["requirements"], []) or []
    return render_template("jobs.html", jobs=rows)


@app.route("/jobs/<int:job_id>")
def job_detail(job_id):
    job = get_or_404(
        """SELECT j.*, c.company_name FROM jobs j
           JOIN companies c ON c.company_id = j.company_id WHERE j.job_id = %s""", (job_id,))
    job["requirements"] = load_json(job["requirements"], []) or []
    applications = fetch_all(
        "SELECT * FROM applications WHERE job_id = %s ORDER BY application_date DESC", (job_id,))
    return render_template("job_detail.html", job=job, applications=applications)


@app.route("/jobs/new", methods=["GET", "POST"])
def job_new():
    errors = []
    values = {"company_id": request.args.get("company_id", type=int), "job_type": "Full-time"}
    if request.method == "POST":
        values = request.form
        data, errors = validate_job(request.form)
        if not errors:
            new_id = execute(
                """INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max,
                                     job_url, date_posted, requirements)
                   VALUES (%(company_id)s, %(job_title)s, %(job_type)s, %(salary_min)s, %(salary_max)s,
                           %(job_url)s, %(date_posted)s, %(requirements)s)""",
                data,
            )
            flash("Job added.", "success")
            return redirect(url_for("job_detail", job_id=new_id))
    return render_template("job_form.html", values=values, errors=errors, companies=company_choices(),
                           title="Add job", cancel_url=url_for("jobs"))


@app.route("/jobs/<int:job_id>/edit", methods=["GET", "POST"])
def job_edit(job_id):
    job = get_or_404("SELECT * FROM jobs WHERE job_id = %s", (job_id,))
    errors, values = [], job_form_values(job)
    if request.method == "POST":
        values = request.form
        data, errors = validate_job(request.form)
        if not errors:
            data["job_id"] = job_id
            execute(
                """UPDATE jobs SET company_id=%(company_id)s, job_title=%(job_title)s,
                          job_type=%(job_type)s, salary_min=%(salary_min)s, salary_max=%(salary_max)s,
                          job_url=%(job_url)s, date_posted=%(date_posted)s, requirements=%(requirements)s
                   WHERE job_id=%(job_id)s""",
                data,
            )
            flash("Job updated.", "success")
            return redirect(url_for("job_detail", job_id=job_id))
    return render_template("job_form.html", values=values, errors=errors, companies=company_choices(),
                           title=f"Edit {job['job_title']}",
                           cancel_url=url_for("job_detail", job_id=job_id))


@app.route("/jobs/<int:job_id>/delete", methods=["GET", "POST"])
def job_delete(job_id):
    job = get_or_404(
        """SELECT j.job_id, j.job_title, c.company_name FROM jobs j
           JOIN companies c ON c.company_id = j.company_id WHERE j.job_id = %s""", (job_id,))
    if request.method == "POST":
        execute("DELETE FROM jobs WHERE job_id = %s", (job_id,))
        flash(f"Deleted {job['job_title']}.", "success")
        return redirect(url_for("jobs"))
    n = fetch_one("SELECT COUNT(*) AS n FROM applications WHERE job_id = %s", (job_id,))["n"]
    return render_template(
        "confirm_delete.html", kind="job", label=f"{job['job_title']} at {job['company_name']}",
        cascade={"application(s)": n}, cancel_url=url_for("job_detail", job_id=job_id))


# ---------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------
def job_choices():
    return fetch_all(
        """SELECT j.job_id, j.job_title, c.company_name FROM jobs j
           JOIN companies c ON c.company_id = j.company_id
           ORDER BY c.company_name, j.job_title""")


def validate_application(form):
    errors = []
    data = {
        "job_id": get_foreign_key(form, "job_id", "job", "jobs", "job_id", errors),
        "application_date": get_date(form, "application_date", "Application date", errors, required=True),
        "status": get_choice(form, "status", "status", STATUSES, errors),
        "resume_version": get_text(form, "resume_version", "Resume version", errors, 50),
        "cover_letter_sent": form.get("cover_letter_sent") == "on",
    }
    # Pack the interview fields into one JSON object (or NULL if all are empty)
    interview = {
        "date": get_date(form, "interview_date", "Interview date", errors),
        "type": (form.get("interview_type") or "").strip() or None,
        "interviewer": get_text(form, "interviewer", "Interviewer", errors, 100),
        "notes": get_text(form, "interview_notes", "Interview notes", errors),
    }
    if interview["type"] and interview["type"] not in INTERVIEW_TYPES:
        errors.append("Please choose a valid interview type.")
    interview["date"] = interview["date"].isoformat() if interview["date"] else None
    interview = {k: v for k, v in interview.items() if v}
    data["interview_data"] = json.dumps(interview) if interview else None
    return data, errors


def application_form_values(app_row):
    """Turn an applications row into flat form values."""
    values = dict(app_row)
    interview = load_json(app_row["interview_data"], {}) or {}
    values["interview_date"] = interview.get("date", "")
    values["interview_type"] = interview.get("type", "")
    values["interviewer"] = interview.get("interviewer", "")
    values["interview_notes"] = interview.get("notes", "")
    return values


@app.route("/applications")
def applications():
    status = request.args.get("status", "")
    sql = """SELECT a.*, j.job_title, c.company_name
             FROM applications a
             JOIN jobs j      ON j.job_id = a.job_id
             JOIN companies c ON c.company_id = j.company_id"""
    params = ()
    if status in STATUSES:
        sql += " WHERE a.status = %s"
        params = (status,)
    sql += " ORDER BY a.application_date DESC, a.application_id DESC"
    return render_template("applications.html", applications=fetch_all(sql, params),
                           current_status=status if status in STATUSES else "")


@app.route("/applications/<int:application_id>")
def application_detail(application_id):
    application = get_or_404(
        """SELECT a.*, j.job_title, j.company_id, c.company_name
           FROM applications a
           JOIN jobs j      ON j.job_id = a.job_id
           JOIN companies c ON c.company_id = j.company_id
           WHERE a.application_id = %s""", (application_id,))
    interview = load_json(application["interview_data"], {}) or {}
    return render_template("application_detail.html", application=application, interview=interview)


@app.route("/applications/new", methods=["GET", "POST"])
def application_new():
    errors = []
    values = {"job_id": request.args.get("job_id", type=int), "status": "Applied",
              "application_date": date.today().isoformat()}
    if request.method == "POST":
        values = request.form
        data, errors = validate_application(request.form)
        if not errors:
            new_id = execute(
                """INSERT INTO applications (job_id, application_date, status, resume_version,
                                             cover_letter_sent, interview_data)
                   VALUES (%(job_id)s, %(application_date)s, %(status)s, %(resume_version)s,
                           %(cover_letter_sent)s, %(interview_data)s)""",
                data,
            )
            flash("Application added.", "success")
            return redirect(url_for("application_detail", application_id=new_id))
    return render_template("application_form.html", values=values, errors=errors, jobs=job_choices(),
                           title="Add application", cancel_url=url_for("applications"))


@app.route("/applications/<int:application_id>/edit", methods=["GET", "POST"])
def application_edit(application_id):
    existing = get_or_404("SELECT * FROM applications WHERE application_id = %s", (application_id,))
    errors, values = [], application_form_values(existing)
    if request.method == "POST":
        values = request.form
        data, errors = validate_application(request.form)
        if not errors:
            data["application_id"] = application_id
            execute(
                """UPDATE applications SET job_id=%(job_id)s, application_date=%(application_date)s,
                          status=%(status)s, resume_version=%(resume_version)s,
                          cover_letter_sent=%(cover_letter_sent)s, interview_data=%(interview_data)s
                   WHERE application_id=%(application_id)s""",
                data,
            )
            flash("Application updated.", "success")
            return redirect(url_for("application_detail", application_id=application_id))
    return render_template("application_form.html", values=values, errors=errors, jobs=job_choices(),
                           title="Edit application",
                           cancel_url=url_for("application_detail", application_id=application_id))


@app.route("/applications/<int:application_id>/delete", methods=["GET", "POST"])
def application_delete(application_id):
    row = get_or_404(
        """SELECT a.application_id, j.job_title, c.company_name FROM applications a
           JOIN jobs j      ON j.job_id = a.job_id
           JOIN companies c ON c.company_id = j.company_id
           WHERE a.application_id = %s""", (application_id,))
    if request.method == "POST":
        execute("DELETE FROM applications WHERE application_id = %s", (application_id,))
        flash("Application deleted.", "success")
        return redirect(url_for("applications"))
    return render_template(
        "confirm_delete.html", kind="application",
        label=f"your application for {row['job_title']} at {row['company_name']}",
        cascade={}, cancel_url=url_for("application_detail", application_id=application_id))


# ---------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------
def validate_contact(form):
    errors = []
    data = {
        "company_id": get_foreign_key(form, "company_id", "company", "companies", "company_id", errors),
        "contact_name": get_text(form, "contact_name", "Name", errors, 100, required=True),
        "title": get_text(form, "title", "Title", errors, 100),
        "email": get_email(form, "email", "Email", errors, 100),
        "phone": get_text(form, "phone", "Phone", errors, 20),
        "linkedin_url": get_url(form, "linkedin_url", "LinkedIn URL", errors, 200),
        "notes": get_text(form, "notes", "Notes", errors),
    }
    return data, errors


@app.route("/contacts")
def contacts():
    rows = fetch_all(
        """SELECT t.*, c.company_name FROM contacts t
           JOIN companies c ON c.company_id = t.company_id
           ORDER BY t.contact_name""")
    return render_template("contacts.html", contacts=rows)


@app.route("/contacts/<int:contact_id>")
def contact_detail(contact_id):
    contact = get_or_404(
        """SELECT t.*, c.company_name FROM contacts t
           JOIN companies c ON c.company_id = t.company_id WHERE t.contact_id = %s""", (contact_id,))
    return render_template("contact_detail.html", contact=contact)


@app.route("/contacts/new", methods=["GET", "POST"])
def contact_new():
    errors = []
    values = {"company_id": request.args.get("company_id", type=int)}
    if request.method == "POST":
        values = request.form
        data, errors = validate_contact(request.form)
        if not errors:
            new_id = execute(
                """INSERT INTO contacts (company_id, contact_name, title, email, phone, linkedin_url, notes)
                   VALUES (%(company_id)s, %(contact_name)s, %(title)s, %(email)s, %(phone)s,
                           %(linkedin_url)s, %(notes)s)""",
                data,
            )
            flash("Contact added.", "success")
            return redirect(url_for("contact_detail", contact_id=new_id))
    return render_template("contact_form.html", values=values, errors=errors, companies=company_choices(),
                           title="Add contact", cancel_url=url_for("contacts"))


@app.route("/contacts/<int:contact_id>/edit", methods=["GET", "POST"])
def contact_edit(contact_id):
    contact = get_or_404("SELECT * FROM contacts WHERE contact_id = %s", (contact_id,))
    errors, values = [], contact
    if request.method == "POST":
        values = request.form
        data, errors = validate_contact(request.form)
        if not errors:
            data["contact_id"] = contact_id
            execute(
                """UPDATE contacts SET company_id=%(company_id)s, contact_name=%(contact_name)s,
                          title=%(title)s, email=%(email)s, phone=%(phone)s,
                          linkedin_url=%(linkedin_url)s, notes=%(notes)s
                   WHERE contact_id=%(contact_id)s""",
                data,
            )
            flash("Contact updated.", "success")
            return redirect(url_for("contact_detail", contact_id=contact_id))
    return render_template("contact_form.html", values=values, errors=errors, companies=company_choices(),
                           title=f"Edit {contact['contact_name']}",
                           cancel_url=url_for("contact_detail", contact_id=contact_id))


@app.route("/contacts/<int:contact_id>/delete", methods=["GET", "POST"])
def contact_delete(contact_id):
    contact = get_or_404("SELECT * FROM contacts WHERE contact_id = %s", (contact_id,))
    if request.method == "POST":
        execute("DELETE FROM contacts WHERE contact_id = %s", (contact_id,))
        flash(f"Deleted {contact['contact_name']}.", "success")
        return redirect(url_for("contacts"))
    return render_template("confirm_delete.html", kind="contact", label=contact["contact_name"],
                           cascade={}, cancel_url=url_for("contact_detail", contact_id=contact_id))


# ---------------------------------------------------------------------
# Job Match
# ---------------------------------------------------------------------
@app.route("/job-match")
def job_match():
    skills_text = request.args.get("skills", "")
    skills = parse_skills(skills_text)
    ranked, unscored, top_missing = [], [], []
    if skills:
        rows = fetch_all(
            """SELECT j.job_id, j.job_title, j.job_type, j.requirements, c.company_name
               FROM jobs j JOIN companies c ON c.company_id = j.company_id""")
        for row in rows:
            row["requirements"] = load_json(row["requirements"], []) or []
        ranked, unscored = rank_jobs(rows, skills)
        top_missing = top_missing_skills(ranked)
    return render_template("job_match.html", skills_text=skills_text, skills=skills,
                           ranked=ranked, unscored=unscored, top_missing=top_missing)


# ---------------------------------------------------------------------
# Error pages
# ---------------------------------------------------------------------
@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", heading="Page not found",
                           message="That record or page doesn't exist (it may have been deleted)."), 404


@app.errorhandler(mysql.connector.Error)
def database_error(error):
    app.logger.exception("Database error")
    return render_template(
        "error.html", heading="Database problem",
        message="The app couldn't complete that database request. Check that MySQL is running "
                "and that your .env settings are correct.",
        detail=str(error)), 500


if __name__ == "__main__":
    app.run(debug=True)
