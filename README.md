Chest X-Ray Detection Web Application - README

Submission Context

This README accompanies the chest X-ray detection web application submitted for the IB Computer Science Internal Assessment. The product files are provided in the submission folder, including all source code, dependencies, and the pretrained YOLO model (best.pt). This application was developed for Mr. {Client}, an emergency department physician, to detect foreign objects in chest X-ray images. The system meets the success criteria outlined in Criterion A, with testing results documented in Criterion B and functionality demonstrated in Criterion D. Please refer to the accompanying IA documentation for full details.

Project Overview

This web application assists in detecting foreign objects (e.g., metal fragments) in chest X-ray images using the YOLOv5 model (best.pt). It is built with Flask (web framework), SQLite (database), and FPDF (PDF report generation). The system meets 10 success criteria from Criterion A:

- SC1: Authenticate users in under 2 seconds (achieved 0.8s).
- SC2: Process X-ray images (JPG/PNG, ≤16MB) in under 5 seconds with bounding boxes (achieved 3.2s for 1MB, 4.8s for 16MB).
- SC3: Achieve detection precision of at least 60% (achieved 61.17%).
- SC4: Store and retrieve metadata via a history page.
- SC5: Generate PDF reports in under 10 seconds (achieved 6.7s).
- SC6: Ensure error-free navigation across 10 uses.
- SC7: Display specific error messages for invalid uploads.
- SC8: Show object names and confidence scores (limited to single-object detection).
- SC9: Delete upload records in under 2 seconds (achieved 0.9s).
- SC10: Clear session on logout in under 1 second (achieved 0.3s).

Limitation: The YOLO model, trained on a 14 GB dataset, can only detect one object per image, affecting SC8 (multi-object detection fails, as noted in Criterion B Test Plan).

Requirements

- Python 3.8+
- Dependencies (listed in requirements.txt):
  - flask
  - flask-sqlalchemy
  - werkzeug
  - ultralytics
  - opencv-python
  - fpdf
  - gunicorn (for production deployment)
- Hardware: CPU (GPU recommended for faster processing)
- YOLO Model: best.pt (pretrained model, included in models/ directory)

Installation

The product files are provided in the submission folder. Follow these steps to set up and run the application on your local machine:

1. Extract the Submission Folder
   - Unzip the provided submission folder (chest-xray-detection) to a directory on your computer (e.g., C:\chest-xray-detection or /home/user/chest-xray-detection).

2. Set Up a Virtual Environment (optional but recommended)
   - Open a terminal in the project directory.
   - Create and activate a virtual environment:
     python -m venv venv
     source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install Dependencies
   - Ensure requirements.txt is in the project directory.
   - Install the required Python packages:
     pip install -r requirements.txt

4. Set Up the Database
   - The application uses SQLite (database.db).
   - Initialize the database by running:
     python -c "from Database import db, init_app; from App import app; init_app(app); db.create_all()"
   - Default admin credentials: username admin, password admin123.

5. Verify the YOLO Model
   - Ensure best.pt is in the models/ directory. This model has a precision of 61.17% (epoch 10).

6. Run the Application
   - Start the Flask development server:
     python App.py
   - Alternatively, for a production-like setup (using Gunicorn):
     gunicorn -w 4 -b 0.0.0.0:5000 App:app
   - Access the app at http://localhost:5000.

Usage

1. Login
   - Open a browser and navigate to http://localhost:5000/login.
   - Enter username admin and password admin123.
   - Successful login redirects to the home page (index.html).

2. Upload an X-Ray Image
   - On the home page, select a JPG or PNG file (≤16MB).
   - Click "Upload" to process the image.
   - Results are displayed in result.html with bounding boxes, object names, and confidence scores (e.g., "Fragment, 0.92").

3. View Detection History
   - Click "View History" to see past uploads (history.html).
   - Metadata includes file name, detection result, confidence, and timestamp.

4. Generate a PDF Report
   - From the history page, click "Generate Full Report".
   - A PDF is downloaded, listing all uploads with details.

5. Delete Uploads
   - On the history page, click "Delete" next to an upload to remove it.

6. Logout
   - Click "Logout" to clear the session and return to the login page.

File Structure

- App.py: Main Flask application file; defines routes and initializes the app.
- Auth.py: Handles authentication (login/logout) and session management.
- Database.py: Defines SQLite database models (Admin, Upload, Log) and initialization.
- Detection.py: Manages file uploads, YOLO detection, bounding box drawing, and deletion.
- Report.py: Generates PDF reports using FPDF, including images and metadata.
- templates/:
  - index.html: Home page for uploading images.
  - login.html: Login page for authentication.
  - result.html: Displays detection results with bounding boxes.
  - history.html: Shows past uploads with metadata.
  - 404.html, 500.html: Error pages for handling invalid routes or server errors.
- static/:
  - Styles.css: Stylesheet for the web interface.
  - uploads/: Directory for storing uploaded X-ray images.
  - processed/: Directory for storing processed images with bounding boxes.
- models/:
  - best.pt: Pretrained YOLO model (61.17% precision).
- requirements.txt: List of Python dependencies.

