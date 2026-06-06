from flask_login import(
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)
from flask import (
    Flask, 
    render_template, 
    request, 
    redirect, 
    url_for,
    flash,
    Response
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, func
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
from datetime import datetime
import csv
from io import StringIO

app = Flask(__name__)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expense.db'
app.config['SECRET_KEY'] = 'my-super-secret-key'
    
db = SQLAlchemy(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key= True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    expenses = db.relationship("Expense",backref="owner", lazy=True)
    

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String(100))
    amount = db.Column(db.Float)
    category = db.Column(db.String(50))
    date = db.Column(db.Date, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"),nullable=False)

@login_manager.user_loader
def load_user(user_id):

    return User.query.get(int(user_id))

@app.route('/')
def home():
    username = "Mohit"
    # age = 25
    return render_template('index.html', name=username)

# @app.route('/about')
# def about():
#     textToPass = "This is about section"
#     return render_template('about.html',passtext = textToPass)

@app.route('/add_expense', methods=['GET','POST'])
@login_required
def add_expense():

    today = datetime.now().strftime("%Y-%m-%d")

    if request.method == 'POST':
        title = request.form.get('title')
        amount = request.form.get('amount')
        category = request.form.get('category')
        date_str = request.form.get("date")

        expense_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        

        if not title:
            flash("Titile is required.", "danger")

            return redirect(
                url_for("add_expense")
            )

        if not len(title) >= 3:
            flash("Title value should be more than three characters.", "warning")

            return redirect(
                url_for("add_expense")
            )
        
        if not amount:
            flash("Amount is required.","warning")

            return redirect(
                url_for("add_expense")
            )
        
        try:
            amount=float(amount)
        except ValueError:
            print("ERROR: Input value must be number")
            return redirect(
                url_for("add_expense")
            )

        if amount <= 0:
            flash("Value must be greater than zero.","warning")

            return redirect(
                url_for("add_expense")
            )
        
        if amount > 100000:
            flash("Value is greater than your aukaat.", "warning")

            return redirect(
                url_for("add_expense")
            )
        
        if not category:
            flash("Please select a category", "danger")

            return redirect(
                url_for("add_expense")
            )

        new_expense = Expense(
            title = title, 
            amount = float(amount),
            category = category,
            date = expense_date,
            user_id=current_user.id
        )

        db.session.add(new_expense)
        db.session.commit()
        flash("Expense added successfully.", "success")

    return render_template(
        'add_expense.html',
        today=today
    )

@app.route('/expenses')
@login_required
def expenses():

    search = request.args.get(
        "search",
        ""
    )

    selected_category = request.args.get(
        "category",
        ""
    )

    selected_month = request.args.get(
        "month",
        ""
    )

    query = Expense.query.filter_by(
        user_id=current_user.id
    )

    # Search by title
    if search:

        query = query.filter(
            Expense.title.ilike(
                f"%{search}%"
            )
        )

    # Filter by category
    if selected_category:

        query = query.filter_by(
            category=selected_category
        )

    expenses = query.order_by(
        Expense.date.desc()
    ).all()

    # Filter by month
    if selected_month:

        filtered_expenses = []

        for expense in expenses:

            if expense.date.month == int(
                selected_month
            ):

                filtered_expenses.append(
                    expense
                )

        expenses = filtered_expenses


    return render_template(
        'expenses.html',
        expenses=expenses
    )

@app.route("/dashboard")
@login_required
def dashboard():
    
    total_spent = db.session.query(func.sum(Expense.amount)).filter_by(user_id=current_user.id).scalar() or 0
    
    total_expenses = Expense.query.filter_by(user_id=current_user.id).count()

    current_month = datetime.now().month
    today = datetime.now().day
    year = datetime.now().year

    monthly_total = 0
    todays_expense = 0
    year_total = 0

    monthly_data = {}

    expenses = Expense.query.filter_by(user_id=current_user.id).all()

    for expense in expenses:
        if expense.date.month == current_month:
            monthly_total += expense.amount
    
    for expense in expenses:
        if expense.date.day == today:
            todays_expense += expense.amount

    for expense in expenses:
        if expense.date.year == year:
            year_total += expense.amount

    for expense in expenses:
        month_name = expense.date.strftime("%b")

        if month_name not in monthly_data:
            monthly_data[month_name] = 0
        
        monthly_data[month_name] += expense.amount
    
    month_labels = list(monthly_data.keys())
    month_amounts = list(monthly_data.values())


    avg_expense = db.session.query(func.avg(Expense.amount)).filter_by(user_id=current_user.id).scalar() or 0

    max_expense = db.session.query(func.max(Expense.amount)).filter_by(user_id=current_user.id).scalar() or 0

    category_totals = (
        db.session.query(Expense.category, func.sum(Expense.amount)).group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).filter_by(user_id=current_user.id).all()
    )

    top_category = None
    lowest_category = None

    if category_totals:
        top_category = max(category_totals, key=lambda item: item[1])

    if category_totals:
        lowest_category = min(category_totals, key=lambda item: item[1])

    labels = []
    amounts = []

    for category,total in category_totals:
        labels.append(category)
        amounts.append(float(total))

    category_length = len(category_totals)


    return render_template(
        "dashboard.html", 
        total_spent=total_spent,
        total_expenses = total_expenses,
        avg_expense=round(avg_expense,2),
        max_expense=max_expense,
        category_totals=category_totals,
        top_category=top_category,
        lowest_category=lowest_category,

        labels=labels,
        amounts=amounts,

        category_length = category_length,
        monthly_total=monthly_total,
        todays_expense=todays_expense,
        year_total=year_total,

        month_labels=month_labels,
        month_amounts=month_amounts
    )

@app.route('/delete_expense/<int:id>')
@login_required
def delete_expense(id):
    expense_to_delete = Expense.query.filter_by(id=id,user_id=current_user.id).get_or_404(id)

    db.session.delete(expense_to_delete)
    db.session.commit()
    flash("Expense deleted successfully.", "success")

    return redirect(url_for('expenses'))

@app.route('/edit_expense/<int:id>', methods=["GET","POST"])
@login_required
def edit_expense(id):
    expense = Expense.query.filter_by(id=id,user_id=current_user.id).get_or_404(id)

    if request.method == "POST":
        expense.title = request.form.get("title")
        expense.amount = float(request.form.get("amount"))
        expense.category = request.form.get("category")

        db.session.commit()
        flash("Expense updated successfully.", "success")

        return redirect(url_for("expenses"))

    return render_template(
        "edit_expense.html",
        expense = expense
    )

@app.route("/register", methods=["GET","POST"])
def register():

    if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username:
            flash("Username is required", "danger")
            return redirect(url_for("register"))
        if not len(username) >= 3:
            flash("Username should be greater than three characters", "danger")
            return redirect(url_for("register"))

        if not password:
            flash("Password is required", "danger")
            return redirect(url_for("register"))
        if not len(password) >= 6:
            flash("Password should be greater than 6 characters", "danger")
            return redirect(url_for("register"))
        
        existing_user= User.query.filter_by(username=username).first()

        if existing_user:
            flash("Username already exists", "danger")
            return redirect(url_for("register"))
        
        hashed_password = generate_password_hash(password)

        new_user = User(
            username=username,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully", "success")

        return redirect(url_for("login"))
            
    
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():

    if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Logged in successfully", "success")    

            return redirect(url_for("dashboard"))
        
        flash("Invalid username or password", "danger")

        return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/logout")
def logout():

    logout_user()

    flash("Logged out successfully", "success")

    return redirect(url_for("login"))

@app.route("/export")
@login_required
def export_csv():

    expenses = Expense.query.filter_by(user_id=current_user.id).all()
    today=datetime.now()
    csv_data =[]

    csv_data.append(
        [
            "Username",
            "Title",
            "Amount",
            "Category",
            "Date",
        ]
    )

    for expense in expenses:
        csv_data.append(
            [
                current_user.username,
                expense.title,
                expense.amount,
                expense.category,
                expense.date,
            ]
        )
    
    output = StringIO()
    writer = csv.writer(output)

    writer.writerows(csv_data),
    output.getvalue()

    return Response(
        output.getvalue(),

        mimetype="text/csv",
        
        headers={
            "Content-Disposition": f"attachment; filename=expenses_{today}.csv"
        }
    )

if __name__ == '__main__':
    app.run(debug=True)