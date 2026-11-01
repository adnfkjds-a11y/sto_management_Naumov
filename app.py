import os
from datetime import datetime, date
from decimal import Decimal
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///sto.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

STATUSES = ["Новый", "Диагностика", "В работе", "Ожидание запчастей", "Готов", "Выдан"]
STATUS_COLORS = {
    "Новый": "secondary", "Диагностика": "info", "В работе": "primary",
    "Ожидание запчастей": "warning", "Готов": "success", "Выдан": "dark"
}

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(40), default="Мастер-приёмщик")
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(140), nullable=False)
    phone = db.Column(db.String(40), nullable=False)
    email = db.Column(db.String(120))
    cars = db.relationship("Car", backref="client", cascade="all, delete-orphan")

class Car(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)
    brand = db.Column(db.String(60), nullable=False)
    model = db.Column(db.String(60), nullable=False)
    year = db.Column(db.Integer)
    plate = db.Column(db.String(20), nullable=False)
    vin = db.Column(db.String(40))

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    specialty = db.Column(db.String(80), default="Механик")
    phone = db.Column(db.String(40))

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    duration = db.Column(db.Integer, default=60)

class Part(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140), nullable=False)
    sku = db.Column(db.String(50), unique=True)
    quantity = db.Column(db.Integer, default=0)
    price = db.Column(db.Numeric(10, 2), default=0)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(30), unique=True, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)
    car_id = db.Column(db.Integer, db.ForeignKey("car.id"), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"))
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(40), default="Новый")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.Date)
    labor_cost = db.Column(db.Numeric(10, 2), default=0)
    client = db.relationship("Client")
    car = db.relationship("Car")
    employee = db.relationship("Employee")
    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")
    @property
    def total(self):
        return Decimal(str(self.labor_cost or 0)) + sum((Decimal(str(i.quantity)) * Decimal(str(i.unit_price)) for i in self.items), Decimal("0"))

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey("part.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    part = db.relationship("Part")

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    method = db.Column(db.String(40), default="Наличные")
    paid_at = db.Column(db.DateTime, default=datetime.utcnow)
    order = db.relationship("Order")

@login_manager.user_loader
def load_user(user_id): return db.session.get(User, int(user_id))

def admin_required(fn):
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.role != "Администратор":
            abort(403)
        return fn(*args, **kwargs)
    return wrapper

@app.context_processor
def inject_globals():
    return {"STATUSES": STATUSES, "STATUS_COLORS": STATUS_COLORS}

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get("username", "").strip()).first()
        if user and user.check_password(request.form.get("password", "")):
            login_user(user)
            return redirect(url_for("dashboard"))
        flash("Неверный логин или пароль", "danger")
    return render_template("login.html")

@app.get("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.get("/")
@login_required
def dashboard():
    orders = Order.query.order_by(Order.created_at.desc()).limit(7).all()
    month_start = date.today().replace(day=1)
    paid = db.session.query(db.func.sum(Payment.amount)).filter(db.func.date(Payment.paid_at) >= month_start).scalar() or 0
    return render_template("dashboard.html", orders=orders,
        orders_count=Order.query.count(),
        in_work=Order.query.filter(Order.status.in_(["Диагностика", "В работе", "Ожидание запчастей"])).count(),
        ready=Order.query.filter_by(status="Готов").count(), revenue=paid)

@app.route("/orders")
@login_required
def orders():
    q = request.args.get("q", "").strip()
    query = Order.query
    if q:
        query = query.join(Car).join(Client).filter(
            db.or_(Order.number.ilike(f"%{q}%"), Client.full_name.ilike(f"%{q}%"),
                   Car.plate.ilike(f"%{q}%"), Car.brand.ilike(f"%{q}%")))
    status = request.args.get("status")
    if status: query = query.filter_by(status=status)
    return render_template("orders.html", orders=query.order_by(Order.created_at.desc()).all(), q=q, selected_status=status)

@app.route("/orders/new", methods=["GET", "POST"])
@login_required
def order_new():
    if request.method == "POST":
        car = db.session.get(Car, int(request.form["car_id"]))
        if not car: abort(400)
        number = f"ЗН-{datetime.now():%y%m%d}-{int(datetime.now().timestamp())%10000:04d}"
        order = Order(number=number, client_id=car.client_id, car_id=car.id,
            employee_id=int(request.form["employee_id"]) if request.form.get("employee_id") else None,
            description=request.form["description"], due_date=date.fromisoformat(request.form["due_date"]) if request.form.get("due_date") else None,
            labor_cost=Decimal(request.form.get("labor_cost") or "0"))
        db.session.add(order); db.session.commit()
        flash(f"Заказ {number} создан", "success")
        return redirect(url_for("order_detail", order_id=order.id))
    return render_template("order_form.html", clients=Client.query.order_by(Client.full_name).all(),
        cars=Car.query.all(), employees=Employee.query.order_by(Employee.full_name).all())

@app.route("/orders/<int:order_id>", methods=["GET", "POST"])
@login_required
def order_detail(order_id):
    order = db.get_or_404(Order, order_id)
    if request.method == "POST":
        action = request.form.get("action")
        if action == "status":
            order.status = request.form["status"]
        elif action == "payment":
            amount = Decimal(request.form["amount"])
            if amount <= 0: flash("Сумма платежа должна быть положительной", "danger")
            else: db.session.add(Payment(order_id=order.id, amount=amount, method=request.form.get("method", "Наличные")))
        elif action == "part":
            part = db.get_or_404(Part, int(request.form["part_id"]))
            qty = int(request.form["quantity"])
            if qty <= 0 or qty > part.quantity:
                flash("Недостаточно запчастей на складе", "danger")
            else:
                part.quantity -= qty
                db.session.add(OrderItem(order_id=order.id, part_id=part.id, quantity=qty, unit_price=part.price))
        db.session.commit()
        return redirect(url_for("order_detail", order_id=order.id))
    payments = Payment.query.filter_by(order_id=order.id).order_by(Payment.paid_at.desc()).all()
    paid = sum((Decimal(str(p.amount)) for p in payments), Decimal("0"))
    return render_template("order_detail.html", order=order, parts=Part.query.filter(Part.quantity > 0).all(),
                           payments=payments, paid=paid, balance=order.total-paid)

@app.route("/clients", methods=["GET", "POST"])
@login_required
def clients():
    if request.method == "POST":
        client = Client(full_name=request.form["full_name"], phone=request.form["phone"], email=request.form.get("email"))
        db.session.add(client); db.session.commit()
        flash("Клиент добавлен", "success")
        return redirect(url_for("clients"))
    q = request.args.get("q", "").strip()
    query = Client.query
    if q: query = query.filter(db.or_(Client.full_name.ilike(f"%{q}%"), Client.phone.ilike(f"%{q}%")))
    return render_template("clients.html", clients=query.order_by(Client.full_name).all())

@app.route("/clients/<int:client_id>/cars", methods=["POST"])
@login_required
def add_car(client_id):
    client = db.get_or_404(Client, client_id)
    db.session.add(Car(client_id=client.id, brand=request.form["brand"], model=request.form["model"],
        year=int(request.form["year"]) if request.form.get("year") else None,
        plate=request.form["plate"], vin=request.form.get("vin")))
    db.session.commit(); flash("Автомобиль добавлен", "success")
    return redirect(url_for("clients"))

@app.route("/inventory", methods=["GET", "POST"])
@login_required
def inventory():
    if request.method == "POST":
        db.session.add(Part(name=request.form["name"], sku=request.form.get("sku") or None,
            quantity=int(request.form["quantity"]), price=Decimal(request.form["price"])))
        db.session.commit(); flash("Запчасть добавлена", "success")
        return redirect(url_for("inventory"))
    return render_template("inventory.html", parts=Part.query.order_by(Part.name).all())

@app.route("/employees", methods=["GET", "POST"])
@login_required
def employees():
    if request.method == "POST":
        db.session.add(Employee(full_name=request.form["full_name"], specialty=request.form["specialty"], phone=request.form.get("phone")))
        db.session.commit(); flash("Сотрудник добавлен", "success")
        return redirect(url_for("employees"))
    return render_template("employees.html", employees=Employee.query.order_by(Employee.full_name).all())

@app.route("/reports")
@login_required
def reports():
    status_counts = {s: Order.query.filter_by(status=s).count() for s in STATUSES}
    total_paid = db.session.query(db.func.sum(Payment.amount)).scalar() or 0
    return render_template("reports.html", status_counts=status_counts, total_paid=total_paid,
        orders_count=Order.query.count(), clients_count=Client.query.count())

@app.cli.command("init-db")
def init_db():
    db.create_all()
    if not User.query.filter_by(username="admin").first():
        u = User(username="admin", full_name="Администратор", role="Администратор"); u.set_password("admin123")
        db.session.add(u)
    if Client.query.count() == 0:
        c1 = Client(full_name="Александр Иванов", phone="+7 900 111-22-33", email="ivanov@example.com")
        c2 = Client(full_name="Мария Смирнова", phone="+7 900 222-33-44", email="smirnova@example.com")
        db.session.add_all([c1,c2]); db.session.flush()
        db.session.add_all([
            Car(client_id=c1.id, brand="BMW", model="X5", year=2019, plate="А123АА"),
            Car(client_id=c2.id, brand="Toyota", model="Camry", year=2021, plate="В456ВВ")
        ])
        db.session.add_all([Employee(full_name="Сергей Петров", specialty="Механик"), Employee(full_name="Дмитрий Волков", specialty="Диагност")])
        db.session.add_all([Part(name="Масляный фильтр", sku="OF-001", quantity=18, price=850), Part(name="Тормозные колодки", sku="BP-014", quantity=7, price=4200)])
        db.session.add_all([Service(name="Компьютерная диагностика", price=2500), Service(name="Замена масла", price=1800)])
        db.session.flush()
        cars = Car.query.all()
        db.session.add_all([
            Order(number="ЗН-26001", client_id=c1.id, car_id=cars[0].id, employee_id=1, description="Диагностика подвески и замена масла", status="В работе", labor_cost=3500),
            Order(number="ЗН-26002", client_id=c2.id, car_id=cars[1].id, employee_id=2, description="Плановое техническое обслуживание", status="Готов", labor_cost=2800)
        ])
    db.session.commit()
    print("База данных создана. Вход: admin / admin123")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
