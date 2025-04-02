from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import db, Admin, log_action  # Import SQLAlchemy db and models
from functools import wraps
from datetime import datetime
import click

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Input validation
        if not username or not password:
            flash("Username and password are required.", "danger")
            return render_template('login.html')
            
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password, password):
            session.clear()
            session['admin_logged_in'] = True
            session['admin_id'] = admin.id
            session['last_login'] = admin.last_login.strftime("%Y-%m-%d %H:%M:%S") if admin.last_login else None
            session.permanent = True
            
            # Update last login time
            admin.last_login = datetime.now()
            db.session.commit()
            
            flash("Login successful!", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password.", "danger")
            
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))

@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate inputs
        if not all([current_password, new_password, confirm_password]):
            flash("All fields are required", "danger")
            return render_template('change_password.html')
            
        if new_password != confirm_password:
            flash("New passwords don't match", "danger")
            return render_template('change_password.html')
            
        if len(new_password) < 8:
            flash("Password must be at least 8 characters long", "danger")
            return render_template('change_password.html')
            
        # Verify current password
        admin_id = session.get('admin_id')
        admin = Admin.query.get(admin_id)
        
        if not admin or not check_password_hash(admin.password, current_password):
            flash("Current password is incorrect", "danger")
            return render_template('change_password.html')
            
        # Update password
        admin.password = generate_password_hash(new_password)
        db.session.commit()
        
        flash("Password updated successfully", "success")
        return redirect(url_for('index'))
        
    return render_template('change_password.html')

# Admin creation function - to be used by CLI only, not exposed via route
def add_admin(username, password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
        
    if Admin.query.filter_by(username=username).first():
        return False, "Username already exists"
    
    hashed_password = generate_password_hash(password)
    new_admin = Admin(username=username, password=hashed_password, created_at=datetime.now())
    db.session.add(new_admin)
    db.session.commit()
    return True, "Admin user created successfully"

# Flask CLI Command to add an admin user
@click.command("add-admin")
@click.argument("username")
@click.argument("password")
def create_admin(username, password):
    """Create a new admin user from the command line."""
    success, message = add_admin(username, password)
    click.echo(message)

# Function to register CLI commands in the app
def register_cli_commands(app):
    app.cli.add_command(create_admin)
