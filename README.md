# Job Application Tracker

A full-stack web app for tracking job applications: companies, job postings, applications, and contacts, plus a **Job Match** page that ranks saved jobs by how well they fit your skills.

**Stack:** MySQL · Python 3 / Flask · HTML + CSS (no frameworks)

## Features

- **Dashboard**: totals, applications by status, response rate, recent applications, upcoming interviews
- **Companies / Jobs / Applications / Contacts**: full CRUD (list, detail, add, edit, delete with a confirmation page that shows what else will be removed)
- **Server-side validation**: required fields, lengths, dates, whole-number salaries (min ≤ max), URLs, emails, valid choices
- **JSON columns**: `jobs.requirements` (list of skills) and `applications.interview_data` (date, type, interviewer, notes)
- **Job Match**: enter your skills, get jobs ranked by match percentage, with the skills you have and the ones you're missing
- Parameterized SQL everywhere (no string-built queries) and escaped templates

## Setup

You need **Python 3.10+** and **MySQL 8.0.16+** (running locally).

```bash
# 1. Get the code
git clone <your-repo-url>
cd job_tracker

# 2. Create a virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Configure the database connection
cp .env.example .env               # Windows: copy .env.example .env
#    then edit .env and set DB_USER / DB_PASSWORD for your MySQL

# 4. Create the database and tables
mysql -u root -p < schema.sql

# 5. (Optional) load demo data
mysql -u root -p job_tracker < seed.sql

# 6. Run the app
python app.py
```

Open <http://127.0.0.1:5000>.

> `schema.sql` drops and recreates the four tables, so re-running it resets the database to empty.

## Database

Four tables, linked by foreign keys:

```
companies 1───* jobs 1───* applications
    1
    └───* contacts
```

Deleting a company also deletes its jobs, applications, and contacts (`ON DELETE CASCADE`); deleting a job deletes its applications. The delete confirmation page tells you exactly how many records will go. See `schema.sql` for column types, constraints, and the JSON shapes.

## How Job Match works

For each job, the app compares your skills with the job's required skills (case-insensitive):

```
match % = (required skills you have) ÷ (total required skills) × 100
```

Jobs are ranked by percentage, then by number of matched skills, then by title. Jobs with no required skills listed can't be scored and are listed separately. The logic lives in `matching.py` and is covered by unit tests.

## Project structure

```
job_tracker/
├── app.py            # Flask routes, validation, dashboard queries
├── database.py       # MySQL connection + query helpers
├── matching.py       # Job Match algorithm (pure Python, unit tested)
├── schema.sql        # Creates the database and tables
├── seed.sql          # Optional demo data
├── templates/        # Jinja2 HTML templates (base, pages, forms, detail views)
├── static/style.css  # Styling
├── tests/            # Unit tests for matching.py
├── AI_USAGE.md       # How generative AI was used on this project
├── requirements.txt
└── .env.example      # Copy to .env and add your DB password
```

## Running the tests

```bash
python -m unittest discover tests
```

## Troubleshooting

- **"Database problem" page / `Access denied`**: check `DB_USER` and `DB_PASSWORD` in `.env`.
- **`Unknown database 'job_tracker'`**: run step 4 (`schema.sql`).
- **`Can't connect to MySQL server`**: make sure the MySQL service is running.
