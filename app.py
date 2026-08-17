from datetime import datetime, timedelta
import os
import uuid

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:///wifi_system.db"
)
app.config["JWT_SECRET_KEY"] = os.getenv(
    "JWT_SECRET_KEY", "CHANGE_THIS_IN_PRODUCTION"
)
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=8)

db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)


class Student(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="student", nullable=False)


class Ticket(db.Model):
    ticket_id = db.Column(
        db.String(36), primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    student_id = db.Column(db.String(20), db.ForeignKey("student.id"), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    issue_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    time_reported = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="Open", nullable=False)


class Router(db.Model):
    router_id = db.Column(db.String(50), primary_key=True)
    location = db.Column(db.String(100), nullable=False)
    signal_strength = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="Online", nullable=False)


def seed_data():
    if not Student.query.filter_by(id="UG0001").first():
        db.session.add(Student(
            id="UG0001",
            name="Demo Student",
            password_hash=generate_password_hash("student123"),
            role="student"
        ))

    if not Student.query.filter_by(id="admin").first():
        db.session.add(Student(
            id="admin",
            name="System Administrator",
            password_hash=generate_password_hash("admin123"),
            role="admin"
        ))

    if Router.query.count() == 0:
        db.session.add_all([
            Router(router_id="R001", location="Computer Science", signal_strength=92, status="Online"),
            Router(router_id="R002", location="Information Studies", signal_strength=76, status="Online"),
            Router(router_id="R003", location="Main Library", signal_strength=58, status="Weak"),
        ])

    db.session.commit()


def auth_user():
    identity = get_jwt_identity()
    return Student.query.filter_by(id=identity).first()


def require_admin():
    user = auth_user()
    return user if user and user.role == "admin" else None


@app.get("/api/health")
def health():
    return jsonify(status="ok")


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    student_id = str(data.get("student_id", "")).strip()
    password = str(data.get("password", ""))

    user = Student.query.filter_by(id=student_id).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify(msg="Bad credentials"), 401

    token = create_access_token(identity=user.id)
    return jsonify(
        access_token=token,
        student_id=user.id,
        name=user.name,
        role=user.role
    )


@app.post("/api/report")
@jwt_required()
def report_issue():
    user = auth_user()
    data = request.get_json(silent=True) or {}

    required = ["location", "issue_type", "description"]
    if any(not str(data.get(x, "")).strip() for x in required):
        return jsonify(msg="location, issue_type and description are required"), 400

    ticket = Ticket(
        student_id=user.id,
        location=str(data["location"]).strip(),
        issue_type=str(data["issue_type"]).strip(),
        description=str(data["description"]).strip()
    )
    db.session.add(ticket)
    db.session.commit()

    return jsonify(
        msg="Ticket created",
        ticket_id=ticket.ticket_id,
        status=ticket.status
    ), 201


@app.get("/api/tickets")
@jwt_required()
def get_tickets():
    user = auth_user()
    tickets = Ticket.query.filter_by(student_id=user.id).order_by(
        Ticket.time_reported.desc()
    ).all()

    return jsonify([ticket_json(t) for t in tickets])


@app.get("/api/admin/tickets")
@jwt_required()
def admin_tickets():
    if not require_admin():
        return jsonify(msg="Admin access required"), 403

    tickets = Ticket.query.order_by(Ticket.time_reported.desc()).all()
    return jsonify([ticket_json(t, include_student=True) for t in tickets])


@app.patch("/api/admin/tickets/<ticket_id>")
@jwt_required()
def update_ticket(ticket_id):
    if not require_admin():
        return jsonify(msg="Admin access required"), 403

    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        return jsonify(msg="Ticket not found"), 404

    data = request.get_json(silent=True) or {}
    status = data.get("status")
    allowed = {"Open", "In Progress", "Resolved"}

    if status not in allowed:
        return jsonify(msg="Invalid status"), 400

    ticket.status = status
    db.session.commit()
    return jsonify(msg="Ticket updated", ticket_id=ticket.ticket_id, status=ticket.status)


@app.get("/api/signal-map")
def signal_map():
    routers = Router.query.all()
    return jsonify([
        {
            "router_id": r.router_id,
            "location": r.location,
            "signal": r.signal_strength,
            "status": r.status
        }
        for r in routers
    ])


@app.get("/api/admin/routers")
@jwt_required()
def admin_routers():
    if not require_admin():
        return jsonify(msg="Admin access required"), 403

    return jsonify([router_json(r) for r in Router.query.all()])


@app.post("/api/admin/routers")
@jwt_required()
def add_router():
    if not require_admin():
        return jsonify(msg="Admin access required"), 403

    data = request.get_json(silent=True) or {}
    router_id = str(data.get("router_id", "")).strip()
    location = str(data.get("location", "")).strip()

    try:
        signal = int(data.get("signal_strength"))
    except (TypeError, ValueError):
        return jsonify(msg="signal_strength must be an integer"), 400

    if not router_id or not location or not 0 <= signal <= 100:
        return jsonify(msg="Invalid router data"), 400

    if db.session.get(Router, router_id):
        return jsonify(msg="Router already exists"), 409

    router = Router(
        router_id=router_id,
        location=location,
        signal_strength=signal,
        status=str(data.get("status", "Online"))
    )
    db.session.add(router)
    db.session.commit()
    return jsonify(router_json(router)), 201


def ticket_json(t, include_student=False):
    result = {
        "id": t.ticket_id,
        "location": t.location,
        "issue": t.issue_type,
        "description": t.description,
        "status": t.status,
        "time_reported": t.time_reported.isoformat() + "Z"
    }
    if include_student:
        result["student"] = t.student_id
    return result


def router_json(r):
    return {
        "router_id": r.router_id,
        "location": r.location,
        "signal": r.signal_strength,
        "status": r.status
    }


with app.app_context():
    db.create_all()
    seed_data()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
