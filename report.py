from flask import Blueprint, redirect, url_for, send_file, session, flash, current_app
from fpdf import FPDF
import os
from database import db, Upload, log_action  # Import SQLAlchemy db and models
from io import BytesIO
from functools import wraps
from datetime import datetime

report_bp = Blueprint('report', __name__)

class DetectionReportPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 18)
        self.cell(0, 10, 'Detection Report', 0, 1, 'C')
        self.set_font('Arial', 'I', 12)
        self.cell(0, 10, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1, 'C')
        self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@report_bp.route('/generate_report', methods=['GET'])
@login_required
def generate_report():
    try:
        uploads = Upload.query.order_by(Upload.upload_time.desc()).all()
        if not uploads:
            flash("No images found in the database to generate a report.", "warning")
            return redirect(url_for('detection.history'))
        
        # Initialize PDF with custom class
        pdf = DetectionReportPDF()
        pdf.alias_nb_pages()
        pdf.add_page()
        
        # Create report content
        for upload in uploads:
            # Extract data
            file_name = upload.file_name
            detection_result = upload.detection_result
            confidence_score = upload.confidence_score
            remarks = upload.remarks if upload.remarks else 'None'
            upload_time = upload.upload_time.strftime("%Y-%m-%d %H:%M:%S")
            original_path = upload.file_path
            processed_path = upload.processed_file_path
            
            # Add a clear section header with background
            pdf.set_fill_color(230, 230, 230)
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, f"Image Analysis: {file_name}", 1, 1, 'L', True)
            
            # Image details in a structured format
            pdf.set_font('Arial', '', 10)
            pdf.cell(35, 7, "Upload Time:", 0, 0)
            pdf.cell(0, 7, f"{upload_time}", 0, 1)
            
            pdf.cell(35, 7, "Detection Result:", 0, 0)
            # Color code the detection result
            if "foreign_object" in detection_result.lower():
                pdf.set_text_color(255, 0, 0)  # Red for foreign objects
            else:
                pdf.set_text_color(0, 128, 0)  # Green for no foreign objects
            pdf.cell(0, 7, f"{detection_result}", 0, 1)
            pdf.set_text_color(0, 0, 0)  # Reset text color
            
            pdf.cell(35, 7, "Confidence Score:", 0, 0)
            confidence_str = f"{confidence_score:.2f}" if confidence_score else "N/A"
            pdf.cell(0, 7, f"{confidence_str}", 0, 1)
            
            pdf.cell(35, 7, "Remarks:", 0, 0)
            pdf.cell(0, 7, f"{remarks}", 0, 1)
            pdf.ln(5)
            
            # Starting Y position for images
            start_y = pdf.get_y()
            
            # Check if we have enough space for images
            if start_y > 180:  # If less than about 90 points left on page
                pdf.add_page()
                start_y = pdf.get_y()
            
            # Add original image on the left
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(90, 7, 'Original Image:', 0, 1)
            if original_path and os.path.exists(original_path):
                pdf.image(original_path, x=10, y=pdf.get_y(), w=90, h=65)
            else:
                pdf.cell(90, 65, 'Image not available', 1, 0, 'C')
            
            # Add processed image on the right
            pdf.set_xy(105, start_y)
            pdf.cell(90, 7, 'Processed Image:', 0, 1)
            if processed_path and os.path.exists(processed_path):
                pdf.image(processed_path, x=105, y=pdf.get_y(), w=90, h=65)
            else:
                pdf.set_xy(105, pdf.get_y())
                pdf.cell(90, 65, 'Image not available', 1, 0, 'C')
            
            # Move cursor below images and add some spacing
            pdf.set_y(start_y + 75)
            pdf.ln(10)
            
            # Add a separator line between entries
            if upload != uploads[-1]:
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(5)
                
                # Check if we have enough space for the next entry
                if pdf.get_y() > 240:
                    pdf.add_page()
        
        # Output PDF directly to memory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"detection_report_{timestamp}.pdf"
        
        # Get PDF as bytes directly in memory
        pdf_bytes = pdf.output(dest='S').encode('latin1')
        pdf_stream = BytesIO(pdf_bytes)
        pdf_stream.seek(0)
        
        # Log the action
        admin_id = session.get('admin_id')
        log_action(admin_id, "generate_report", f"Generated report with {len(uploads)} images")
        
        return send_file(
            pdf_stream,
            as_attachment=True,
            download_name=report_filename,
            mimetype='application/pdf'
        )
    
    except Exception as e:
        flash(f"Error generating report: {str(e)}", "danger")
        return redirect(url_for('detection.history'))

@report_bp.route('/single_report/<int:image_id>', methods=['GET'])
@login_required
def single_report(image_id):
    """Generate a report for a single image"""
    try:
        upload = Upload.query.get(image_id)
        if not upload:
            flash("Image not found in the database.", "warning")
            return redirect(url_for('detection.history'))
        
        # Initialize PDF with custom class
        pdf = DetectionReportPDF()
        pdf.alias_nb_pages()
        pdf.add_page()
        
        # Extract data
        file_name = upload.file_name
        detection_result = upload.detection_result
        confidence_score = upload.confidence_score
        remarks = upload.remarks if upload.remarks else 'None'
        upload_time = upload.upload_time.strftime("%Y-%m-%d %H:%M:%S")
        original_path = upload.file_path
        processed_path = upload.processed_file_path
        
        # Add a clear section header with background
        pdf.set_fill_color(230, 230, 230)
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, f"Image Analysis: {file_name}", 1, 1, 'L', True)
        
        # Image details in a structured format
        pdf.set_font('Arial', '', 10)
        pdf.cell(35, 7, "Upload Time:", 0, 0)
        pdf.cell(0, 7, f"{upload_time}", 0, 1)
        
        pdf.cell(35, 7, "Detection Result:", 0, 0)
        # Color code the detection result
        if "foreign_object" in detection_result.lower():
            pdf.set_text_color(255, 0, 0)  # Red for foreign objects
        else:
            pdf.set_text_color(0, 128, 0)  # Green for no foreign objects
        pdf.cell(0, 7, f"{detection_result}", 0, 1)
        pdf.set_text_color(0, 0, 0)  # Reset text color
        
        pdf.cell(35, 7, "Confidence Score:", 0, 0)
        confidence_str = f"{confidence_score:.2f}" if confidence_score else "N/A"
        pdf.cell(0, 7, f"{confidence_str}", 0, 1)
        
        pdf.cell(35, 7, "Remarks:", 0, 0)
        pdf.cell(0, 7, f"{remarks}", 0, 1)
        pdf.ln(5)
        
        # Starting Y position for images
        start_y = pdf.get_y()
        
        # Add original image on the left
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(90, 7, 'Original Image:', 0, 1)
        if original_path and os.path.exists(original_path):
            pdf.image(original_path, x=10, y=pdf.get_y(), w=90, h=65)
        else:
            pdf.cell(90, 65, 'Image not available', 1, 0, 'C')
        
        # Add processed image on the right
        pdf.set_xy(105, start_y)
        pdf.cell(90, 7, 'Processed Image:', 0, 1)
        if processed_path and os.path.exists(processed_path):
            pdf.image(processed_path, x=105, y=pdf.get_y(), w=90, h=65)
        else:
            pdf.set_xy(105, pdf.get_y())
            pdf.cell(90, 65, 'Image not available', 1, 0, 'C')
        
        # Output PDF directly to memory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"detection_report_{file_name}_{timestamp}.pdf"
        
        # Get PDF as bytes directly in memory
        pdf_bytes = pdf.output(dest='S').encode('latin1')
        pdf_stream = BytesIO(pdf_bytes)
        pdf_stream.seek(0)
        
        # Log the action
        admin_id = session.get('admin_id')
        log_action(admin_id, "generate_single_report", f"Generated report for image ID: {image_id}")
        
        return send_file(
            pdf_stream,
            as_attachment=True,
            download_name=report_filename,
            mimetype='application/pdf'
        )
    
    except Exception as e:
        flash(f"Error generating report: {str(e)}", "danger")
        return redirect(url_for('detection.image_details', image_id=image_id))