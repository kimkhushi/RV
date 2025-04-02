from flask import Flask, render_template, redirect, url_for, flash, session
from auth import auth_bp, register_cli_commands
from detection import detection_bp
from report import report_bp
from database import init_db, db  # Import db from Database.py
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Use environment variable for secret key, fallback to random if not set
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize database with SQLAlchemy
init_db(app)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(detection_bp)
app.register_blueprint(report_bp)

# Register CLI commands
register_cli_commands(app)

@app.route('/')
def index():
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login'))
    return render_template('index.html')

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

if __name__ == "__main__":
    app.run(debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true')
