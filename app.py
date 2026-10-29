"""Employee Payroll System - Flask + SQLite portfolio project."""
from __future__ import annotations

import os
import sqlite3
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("PAYROLL_DB", BASE_DIR / "payroll.db"))
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key-change-before-deployment")


def get_db() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db() -> None:
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_code TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            department TEXT NOT NULL,
            email TEXT NOT NULL,
            base_salary NUMERIC NOT NULL CHECK (base_salary >= 0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS payroll (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
            pay_month TEXT NOT NULL,
            allowances NUMERIC NOT NULL DEFAULT 0 CHECK (allowances >= 0),
            deductions NUMERIC NOT NULL DEFAULT 0 CHECK (deductions >= 0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(employee_id, pay_month)
        );
        """)


def money(value: object) -> Decimal:
    try:
        number = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        raise ValueError("Enter a valid amount.") from None
    if not number.is_finite() or number < 0:
        raise ValueError("Amounts must be zero or greater.")
    return number


@app.template_filter("currency")
def currency(value: object) -> str:
    return f"₹{Decimal(str(value or 0)):,.2f}"


@app.get("/")
def dashboard():
    with get_db() as db:
        total_employees = db.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
        latest_month = date.today().strftime("%Y-%m")
        current_total = db.execute(
            "SELECT COALESCE(SUM(e.base_salary + p.allowances - p.deductions), 0) "
            "FROM payroll p JOIN employees e ON e.id = p.employee_id WHERE p.pay_month = ?",
            (latest_month,),
        ).fetchone()[0]
        recent = db.execute(
            "SELECT p.*, e.employee_code, e.full_name, e.department, e.base_salary, "
            "(e.base_salary + p.allowances - p.deductions) AS net_salary "
            "FROM payroll p JOIN employees e ON e.id = p.employee_id "
            "ORDER BY p.pay_month DESC, p.id DESC LIMIT 8"
        ).fetchall()
    return render_template("dashboard.html", total_employees=total_employees,
                           current_total=current_total, latest_month=latest_month, recent=recent)


@app.get("/employees")
def employees():
    q = request.args.get("q", "").strip()
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM employees WHERE full_name LIKE ? OR employee_code LIKE ? OR department LIKE ? "
            "ORDER BY id DESC", (f"%{q}%", f"%{q}%", f"%{q}%")
        ).fetchall()
    return render_template("employees.html", employees=rows, q=q)


@app.route("/employees/new", methods=["GET", "POST"])
def employee_new():
    if request.method == "POST":
        code = request.form.get("employee_code", "").strip().upper()
        name = request.form.get("full_name", "").strip()
        department = request.form.get("department", "").strip()
        email = request.form.get("email", "").strip()
        try:
            salary = money(request.form.get("base_salary", ""))
            if not all([code, name, department, email]):
                raise ValueError("Please complete all fields.")
            if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
                raise ValueError("Enter a valid email address.")
            with get_db() as db:
                db.execute("INSERT INTO employees(employee_code, full_name, department, email, base_salary) VALUES (?, ?, ?, ?, ?)",
                           (code, name, department, email, str(salary)))
            flash("Employee added successfully.", "success")
            return redirect(url_for("employees"))
        except ValueError as exc:
            flash(str(exc), "error")
        except sqlite3.IntegrityError:
            flash("That employee code already exists. Please use a unique code.", "error")
    return render_template("employee_form.html", employee=None)


@app.route("/employees/<int:employee_id>/edit", methods=["GET", "POST"])
def employee_edit(employee_id: int):
    with get_db() as db:
        employee = db.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()
    if employee is None:
        flash("Employee not found.", "error")
        return redirect(url_for("employees"))
    if request.method == "POST":
        code = request.form.get("employee_code", "").strip().upper()
        name = request.form.get("full_name", "").strip()
        department = request.form.get("department", "").strip()
        email = request.form.get("email", "").strip()
        try:
            salary = money(request.form.get("base_salary", ""))
            if not all([code, name, department, email]):
                raise ValueError("Please complete all fields.")
            if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
                raise ValueError("Enter a valid email address.")
            with get_db() as db:
                db.execute("UPDATE employees SET employee_code=?, full_name=?, department=?, email=?, base_salary=? WHERE id=?",
                           (code, name, department, email, str(salary), employee_id))
            flash("Employee updated successfully.", "success")
            return redirect(url_for("employees"))
        except ValueError as exc:
            flash(str(exc), "error")
        except sqlite3.IntegrityError:
            flash("That employee code already exists. Please use a unique code.", "error")
    return render_template("employee_form.html", employee=employee)


@app.post("/employees/<int:employee_id>/delete")
def employee_delete(employee_id: int):
    with get_db() as db:
        db.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
    flash("Employee and associated payroll records deleted.", "success")
    return redirect(url_for("employees"))


@app.route("/payroll/new", methods=["GET", "POST"])
def payroll_new():
    with get_db() as db:
        employee_rows = db.execute("SELECT id, employee_code, full_name, base_salary FROM employees ORDER BY full_name").fetchall()
    if request.method == "POST":
        try:
            employee_id = int(request.form.get("employee_id", ""))
            pay_month = request.form.get("pay_month", "").strip()
            # Strict YYYY-MM validation also prevents unusual strings being saved as months.
            if len(pay_month) != 7 or pay_month[4] != "-":
                raise ValueError("Choose a valid payroll month.")
            date.fromisoformat(pay_month + "-01")
            allowances = money(request.form.get("allowances", "0"))
            deductions = money(request.form.get("deductions", "0"))
            with get_db() as db:
                employee = db.execute("SELECT id, base_salary FROM employees WHERE id = ?", (employee_id,)).fetchone()
                if employee is None:
                    raise ValueError("Select a valid employee.")
                net = Decimal(str(employee["base_salary"])) + allowances - deductions
                if net < 0:
                    raise ValueError("Deductions cannot exceed base salary plus allowances.")
                db.execute("INSERT INTO payroll(employee_id, pay_month, allowances, deductions) VALUES (?, ?, ?, ?)",
                           (employee_id, pay_month, str(allowances), str(deductions)))
            flash("Payroll record created.", "success")
            return redirect(url_for("payroll"))
        except (ValueError, TypeError) as exc:
            flash(str(exc) or "Please check the form values.", "error")
        except sqlite3.IntegrityError:
            flash("A payroll record already exists for this employee and month.", "error")
    return render_template("payroll_form.html", employees=employee_rows, current_month=date.today().strftime("%Y-%m"))


@app.get("/payroll")
def payroll():
    month = request.args.get("month", "").strip()
    query = (
        "SELECT p.*, e.employee_code, e.full_name, e.department, e.base_salary, "
        "(e.base_salary + p.allowances - p.deductions) AS net_salary "
        "FROM payroll p JOIN employees e ON e.id = p.employee_id"
    )
    params: tuple[str, ...] = ()
    if month:
        query += " WHERE p.pay_month = ?"
        params = (month,)
    query += " ORDER BY p.pay_month DESC, e.full_name ASC"
    with get_db() as db:
        records = db.execute(query, params).fetchall()
    return render_template("payroll.html", records=records, month=month)


@app.get("/payroll/<int:payroll_id>/slip")
def payslip(payroll_id: int):
    with get_db() as db:
        record = db.execute(
            "SELECT p.*, e.employee_code, e.full_name, e.department, e.email, e.base_salary, "
            "(e.base_salary + p.allowances - p.deductions) AS net_salary "
            "FROM payroll p JOIN employees e ON e.id = p.employee_id WHERE p.id = ?", (payroll_id,)
        ).fetchone()
    if record is None:
        flash("Payslip not found.", "error")
        return redirect(url_for("payroll"))
    return render_template("payslip.html", record=record)


@app.get("/health")
def health():
    return {"status": "ok"}


with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
