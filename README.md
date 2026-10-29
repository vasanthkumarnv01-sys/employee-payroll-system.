# PayPilot — Employee Payroll System

A portfolio-ready employee and payroll management web app built with **Python, Flask, SQLite, HTML, and CSS**. It gives a junior developer a practical example of CRUD, relational data, validation, server-rendered templates, search, calculations, and printable reports.

> **Portfolio/demo project only.** It is not a production payroll or tax-compliance system. Use fictional employee data. No authentication, tax rules, statutory deductions, or payment integrations are implemented.

## Features

- Dashboard with employee count and current-month net payroll summary
- Create, list, search, edit, and delete employee records
- Monthly payroll records with base salary, allowances, deductions, and computed net salary
- Validation for required fields, numeric amounts, negative net pay, duplicate employee codes, and duplicate payroll months
- Printable payslip view (use the browser's Print / Save as PDF)
- SQLite database created automatically on first run
- Responsive layout for desktop and mobile
- Health endpoint at `/health`

## Stack

- Python 3.10+
- Flask
- SQLite (`sqlite3` from Python standard library)
- HTML/Jinja templates and custom CSS

## Run locally

### Windows (PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000` in your browser. SQLite creates `payroll.db` in the project directory at startup. Set `SECRET_KEY` in your environment before deployment. The app's development server is intended for local use only.

## Suggested demo flow

1. Add a fictional employee, such as `EMP-001`, in the Engineering department.
2. Create that employee's payroll for the current month.
3. Add allowances and deductions to demonstrate net pay calculation.
4. Open the payslip and print it or save it as a PDF.
5. Search the employee directory and edit the employee's details.

## Project structure

```text
employee-payroll-system/
├── app.py                  # Flask routes, validation, and database setup
├── requirements.txt
├── .gitignore
├── .env.example
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── employees.html
│   ├── employee_form.html
│   ├── payroll.html
│   ├── payroll_form.html
│   └── payslip.html
└── static/
    └── style.css
```

## Database model

- `employees`: unique employee code, contact details, department, and base salary
- `payroll`: employee reference, month, allowances, deductions, and timestamp; each employee has at most one payroll entry per month

## Future improvements

- User login and role-based access controls
- Automated tests with `pytest`
- CSV export and PDF generation
- configurable currency, payroll periods, and configurable statutory rules
- PostgreSQL deployment configuration and audit logging

## Author

**Vasanth Kumar** — Junior Developer portfolio project
