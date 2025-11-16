from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jbucks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'dev-secret-key'  # change for production

db = SQLAlchemy(app)


# ---------------- Models ----------------
class Payee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    paid_for_other = db.Column(db.Boolean, default=False)
    payee_name = db.Column(db.String(120))


# ---------------- Helpers ----------------
def create_tables():
    """Create DB tables inside an application context."""
    with app.app_context():
        db.create_all()


# ---------------- Routes ----------------
@app.route('/')
def home():
    payees = Payee.query.order_by(Payee.name).all()

    today_date = date.today()
    start = today_date.replace(day=1)
    # compute first day of next month
    if today_date.month == 12:
        end = today_date.replace(year=today_date.year + 1, month=1, day=1)
    else:
        end = today_date.replace(month=today_date.month + 1, day=1)

    expenses = Expense.query.filter(Expense.date >= start, Expense.date < end).all()

    you_total = sum(e.amount for e in expenses if not e.paid_for_other)
    others_total = sum(e.amount for e in expenses if e.paid_for_other)

    # breakdown for "You" by category
    cat_totals = {}
    for e in expenses:
        if not e.paid_for_other:
            cat_totals[e.category] = cat_totals.get(e.category, 0) + e.amount

    return render_template(
        'home.html',
        payees=payees,
        you_total=you_total,
        others_total=others_total,
        cat_totals=cat_totals,
        today=today_date.isoformat(),
    )


@app.route('/expenses')
def index():
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    return render_template('index.html', expenses=expenses)


@app.route('/add', methods=['GET', 'POST'])
def add_expense():
    if request.method == 'POST':
        try:
            date_str = request.form.get('date') or date.today().isoformat()
            d = datetime.fromisoformat(date_str).date()

            category = request.form.get('category') or 'Other'
            amount = float(request.form['amount'])
            description = request.form.get('description') or ''

            paid_for_other = request.form.get('paid_for_other') == '1'
            payee_name = request.form.get('payee_name') or None

            # if a payee name was supplied and doesn't exist yet — add it
            if payee_name:
                payee_name = payee_name.strip()
                if payee_name and not Payee.query.filter_by(name=payee_name).first():
                    db.session.add(Payee(name=payee_name))

            e = Expense(
                date=d,
                category=category,
                amount=amount,
                description=description,
                paid_for_other=paid_for_other,
                payee_name=payee_name,
            )
            db.session.add(e)
            db.session.commit()
            flash('Expense saved', 'success')
            return redirect(url_for('index'))

        except Exception as ex:
            flash('Error: ' + str(ex), 'danger')
            return redirect(url_for('home'))

    # GET: prefill values if provided via query string
    category = request.args.get('category', '')
    paid_for_other = request.args.get('paid_for_other', '0')
    payee_name = request.args.get('payee_name', '')
    return render_template(
        'add.html',
        today=date.today().isoformat(),
        category=category,
        paid_for_other=paid_for_other,
        payee_name=payee_name,
    )


@app.route('/edit/<int:expense_id>', methods=['GET', 'POST'])
def edit_expense(expense_id):
    e = Expense.query.get_or_404(expense_id)

    if request.method == 'POST':
        try:
            e.date = datetime.fromisoformat(request.form['date']).date()
            e.category = request.form['category']
            e.amount = float(request.form['amount'])
            e.description = request.form.get('description')
            e.paid_for_other = request.form.get('paid_for_other') == '1'
            e.payee_name = request.form.get('payee_name') or None

            if e.payee_name and not Payee.query.filter_by(name=e.payee_name).first():
                db.session.add(Payee(name=e.payee_name))

            db.session.commit()
            flash('Updated successfully', 'success')
            return redirect(url_for('index'))

        except Exception as ex:
            flash('Error updating: ' + str(ex), 'danger')
            return redirect(url_for('index'))

    return render_template('edit.html', e=e)


@app.route('/delete/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    e = Expense.query.get_or_404(expense_id)
    db.session.delete(e)
    db.session.commit()
    flash('Deleted', 'info')
    return redirect(url_for('index'))


# ----------------- Run -----------------
if __name__ == '__main__':
    create_tables()  # make sure DB tables exist
    app.run(debug=True)
