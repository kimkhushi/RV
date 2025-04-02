from flask import Blueprint, request, redirect, url_for, flash, render_template, send_file, session, current_app
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import cv2
import os
import json
from functools import lru_cache, wraps
from database import db, Upload, log_action  # Import SQLAlchemy db and models
from PIL import Image
import io
import uuid
import numpy as np
import time
from datetime import datetime
import imghdr

# Check for YOLO availability and version
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("Warning: YOLO not available. Install ultralytics package for detection functionality.")

detection_bp = Blueprint('detection', __name__)

# Define allowed extensions for security
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_image(stream):
    """Validate that file is actually an image"""
    header = stream.read(512)
    stream.seek(0)
    format = imghdr.what(None, header)
    if not format:
        return None
    return '.' + (format if format != 'jpeg' else 'jpg')

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# Import torch and the YOLO detection model class
import torch
from ultralytics.nn.tasks import DetectionModel

# --- PATCH: Allowlist DetectionModel for safe deserialization ---
if hasattr(torch.serialization, '_default_safe_globals'):
    torch.serialization._default_safe_globals["ultralytics.nn.tasks.DetectionModel"] = DetectionModel
# -----------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_model():
    if not YOLO_AVAILABLE:
        print(" YOLO package is not available.")
        return None

    model_path = r"E:\RedVision\RV (1)\best.pt"
    print(f" Using model path: {model_path}")

    if not os.path.exists(model_path):
        print(f" Error: Model file not found at {model_path}")
        return None

    try:
        # Initialize the YOLO model (this internally calls torch.load)
        model = YOLO(model_path)
        print(" YOLO model loaded successfully!")
        return model
    except Exception as e:
        print(f" Error loading YOLO model: {e}")
        return None

def predict_image(image_path):
    """Predict using YOLO model with error handling"""
    model = get_model()
    if model is None:
        return [], "Model not available"
        
    try:
        img = cv2.imread(image_path)
        if img is None:
            return [], "Failed to read image"
            
        results = model.predict(source=img, save=False)
        return results, None
    except Exception as e:
        return [], f"Prediction error: {str(e)}"

def draw_boxes_on_image(image_path, boxes, class_names=None):
    """Draw detection boxes on image"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return None
            
        for box in boxes:
            x_min, y_min, x_max, y_max = map(int, box.xyxy[0].tolist())
            confidence = float(box.conf[0])
            class_id = int(box.cls[0])
            class_name = class_names[class_id] if class_names else "Object"
            
            cv2.rectangle(img, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
            cv2.putText(img, f"{class_name} {confidence:.2f}", (x_min, y_min - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        # Generate unique filename for processed image
        filename = f"processed_{uuid.uuid4().hex}.jpg"
        processed_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        cv2.imwrite(processed_path, img)
        return processed_path
    except Exception as e:
        print(f"Error drawing boxes: {e}")
        return None

@detection_bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    try:
        if 'file' not in request.files:
            flash("No file part in the request.", "danger")
            return redirect(url_for('index'))
            
        file = request.files['file']
        if file.filename == '':
            flash("No file selected.", "danger")
            return redirect(url_for('index'))
            
        if not allowed_file(file.filename):
            flash("Only JPG, JPEG and PNG files allowed.", "danger")
            return redirect(url_for('index'))
            
        # Additional validation
        file_extension = validate_image(file.stream)
        if not file_extension:
            flash("Invalid image file.", "danger")
            return redirect(url_for('index'))
            
        # Secure the filename and generate unique name
        original_filename = secure_filename(file.filename)
        unique_filename = f"{int(time.time())}_{uuid.uuid4().hex}{file_extension}"
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Save the file
        file.save(file_path)
        
        # Process image with YOLO
        results, error = predict_image(file_path)
        if error:
            flash(f"Detection error: {error}", "danger")
            return redirect(url_for('index'))
            
        # Process detection results
        predictions = []
        threshold = 0.25
        model = get_model()
        class_names = model.names if model else {}
        
        detection_result = "No foreign object detected"
        confidence_score = 0.0
        
        for result in results:
            for box in result.boxes:
                if box.conf[0] > threshold:
                    class_id = int(box.cls[0])
                    class_name = class_names.get(class_id, "Unknown")
                    conf = float(box.conf[0])
                    predictions.append({
                        "class": class_name,
                        "confidence": conf,
                        "coordinates": box.xyxy[0].tolist()
                    })
                    
        if predictions:
            # Sort by confidence and use highest confidence prediction
            predictions.sort(key=lambda x: x['confidence'], reverse=True)
            detection_result = predictions[0]['class']
            confidence_score = predictions[0]['confidence']
        
        # Draw boxes on the image
        processed_file_path = draw_boxes_on_image(file_path, results[0].boxes, class_names) if results else None
        
        # Save to database with SQLAlchemy
        new_upload = Upload(
            file_name=original_filename,
            file_path=file_path,
            detection_result=detection_result,
            confidence_score=confidence_score,
            processed_file_path=processed_file_path,
            upload_time=datetime.now()
        )
        db.session.add(new_upload)
        db.session.commit()
        upload_id = new_upload.id
        
        # Log the action
        admin_id = session.get('admin_id')
        log_action(admin_id, "upload_detection", f"Uploaded file: {original_filename}, Result: {detection_result}")
        
        flash("Detection completed!", "success")
        return redirect(url_for('detection.image_details', image_id=upload_id))
    except RequestEntityTooLarge:
        flash("File too large. Maximum size is 16MB.", "danger")
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"Error processing file: {str(e)}", "danger")
        return redirect(url_for('index'))

@detection_bp.route('/history', methods=['GET'])
@login_required
def history():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    
    total = Upload.query.count()
    images = Upload.query.order_by(Upload.upload_time.desc()).limit(per_page).offset(offset).all()
    
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('history.html', 
                           images=images, 
                           page=page, 
                           total_pages=total_pages)

@detection_bp.route('/view_image/<int:image_id>/<string:image_type>')
@login_required
def view_image(image_id, image_type):
    upload = Upload.query.get(image_id)
    if upload:
        if image_type == 'original':
            file_path = upload.file_path
        else:
            file_path = upload.processed_file_path
        if file_path and os.path.exists(file_path):
            return send_file(file_path, mimetype='image/jpeg')
    return "Image not found", 404

@detection_bp.route('/image/<int:image_id>')
@login_required
def image_details(image_id):
    upload = Upload.query.get(image_id)
    if upload:
        return render_template(
            'result.html',
            image_id=upload.id,
            file_name=upload.file_name,
            detection_result=upload.detection_result,
            confidence_score=upload.confidence_score,
            upload_time=upload.upload_time.strftime("%Y-%m-%d %H:%M:%S"),
            remarks=upload.remarks
        )
    else:
        flash("Image not found", "danger")
        return redirect(url_for('detection.history'))

@detection_bp.route('/save_remarks', methods=['POST'])
@login_required
def save_remarks():
    image_id = request.form.get('image_id')
    remarks = request.form.get('remarks')
    
    if not image_id:
        flash("Missing image information", "danger")
        return redirect(url_for('detection.history'))
    
    upload = Upload.query.get(image_id)
    if upload:
        upload.remarks = remarks
        db.session.commit()
        
        # Log the action
        admin_id = session.get('admin_id')
        log_action(admin_id, "update_remarks", f"Updated remarks for image ID: {image_id}")
        
        flash("Remarks saved successfully!", "success")
    else:
        flash("Image not found", "danger")
    
    return redirect(url_for('detection.image_details', image_id=image_id))

@detection_bp.route('/delete/<int:image_id>', methods=['POST'])
@login_required
def delete_image(image_id):
    upload = Upload.query.get(image_id)
    if upload:
        # Delete files from filesystem
        if upload.file_path and os.path.exists(upload.file_path):
            os.remove(upload.file_path)
        if upload.processed_file_path and os.path.exists(upload.processed_file_path):
            os.remove(upload.processed_file_path)
        
        # Delete from database
        db.session.delete(upload)
        db.session.commit()
        
        # Log the action
        admin_id = session.get('admin_id')
        log_action(admin_id, "delete_image", f"Deleted image ID: {image_id}")
        
        flash("Image deleted successfully", "success")
    else:
        flash("Image not found", "danger")
        
    return redirect(url_for('detection.history'))