from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from datetime import datetime

db = SQLAlchemy()

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime)

class Upload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    detection_result = db.Column(db.String(255))
    confidence_score = db.Column(db.Float)
    remarks = db.Column(db.Text)
    upload_time = db.Column(db.DateTime, default=datetime.now)
    processed_file_path = db.Column(db.String(255))

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    details = db.Column(db.Text)

def init_db(app):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()
        if not Admin.query.filter_by(username='admin').first():
            default_admin = Admin(
                username='admin',
                password=generate_password_hash('admin123'),
                created_at=datetime.now()
            )
            db.session.add(default_admin)
            db.session.commit()

def log_action(admin_id, action, details=None):
    log = Log(admin_id=admin_id, action=action, details=details)
    db.session.add(log)
    db.session.commit()