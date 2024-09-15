import cv2
import sqlite3
from datetime import datetime, timedelta
from fpdf import FPDF
import pygame
import tkinter as tk
from tkinter import simpledialog
import os

ALARM_SOUND_PATH = rf'C:\Users\lingi\OneDrive\Desktop\face_dection\a.mp3'
DB_PATH = 'driver_data.db'
LOGO_PATH = rf"C:\Users\lingi\OneDrive\Desktop\face_dection\logo.jpeg"


# Setup the SQLite database and create tables if they don't exist.
def setup_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create Drivers_info table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Drivers_info (
        driver_employee_id INTEGER PRIMARY KEY,
        driver_name TEXT NOT NULL,
        driver_licence_id TEXT NOT NULL,
        driver_mobile_number TEXT NOT NULL
    )
    ''')

    # Create Vechile_info table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Vechile_info (
        driver_employee_id INTEGER,
        vechile_type TEXT NOT NULL,
        vechile_number TEXT NOT NULL,
        vechile_model TEXT NOT NULL,
        FOREIGN KEY (driver_employee_id) REFERENCES Drivers_info(driver_employee_id)
    )
    ''')

    # Create Detection_system table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Detection_system1 (
        id INTEGER PRIMARY KEY,
        driver_employee_id INTEGER,
        driver_detection_start DATETIME,
        driver_capture_image TEXT,
        driver_alarm_alert TEXT,
        driver_detection_end_time DATETIME,
        FOREIGN KEY (driver_employee_id) REFERENCES Drivers_info(driver_employee_id)
    )
    ''')
    # Insert sample data
    cursor.execute('''
    INSERT OR IGNORE INTO Drivers_info (driver_employee_id, driver_name, driver_licence_id, driver_mobile_number)
    VALUES (1000, 'Rajesh Kumar', 'DL10123', '9123456789'),
    (1001, 'Vajesh Kumar', 'DL10125', '9127456789'),
    (1002, 'Majesh Kumar', 'DL10126', '9129456789'),
    (1003, 'Uajesh Kumar', 'DL10127', '9129056789')              
    ''')

    cursor.execute('''
    INSERT OR IGNORE INTO Vechile_info (driver_employee_id, vechile_type, vechile_number, vechile_model)
    VALUES (1000, 'Bus', 'KA01 1234', 'Volvo 2021')
    ,(1001, 'Bus', 'AP01 1237', 'Volvo 2023')
    ,(1002, 'Bus', 'TN01 1237', 'Volvo 2022')
    ,(1003, 'Bus', 'AP01 737', 'Volvo 2021')              
    ''')

    conn.commit()
    conn.close()

# Fetch details of a driver using their employee ID.
def fetch_driver_details(driver_employee_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Drivers_info WHERE driver_employee_id=?", (driver_employee_id,))
    details = cursor.fetchone()
    conn.close()
    return details

# Fetch vehicle details of a driver using their employee ID.
def fetch_vehicle_details(driver_employee_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Vechile_info WHERE driver_employee_id=?", (driver_employee_id,))
    details = cursor.fetchone()
    conn.close()
    return details

# Authenticate the user using an OTP.
def authenticate_with_otp_gui(phone_number):
    root = tk.Tk()
    root.withdraw()
    otp = "1234"  # Mock OTP for demonstration
    entered_otp = simpledialog.askstring("OTP Authentication", f"An OTP has been sent to {phone_number}. Please enter it:")
    root.destroy()
    return entered_otp == otp

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
EYE_AR_CONSEC_FRAMES = 5

def start_face_detection():
    if not os.path.exists(ALARM_SOUND_PATH):
        print("Alarm sound not found. Exiting detection.")
        return None, None, None, None

    pygame.mixer.init()
    pygame.mixer.music.load(ALARM_SOUND_PATH)

    COUNTER = 0
    ALARM_ON = False
    alert_count = 0
    detection_start = datetime.now()
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return None, None, None, None

    print("Starting face detection. Press 'q' to stop...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(30, 30))

        for (x, y, w, h) in faces:
            face_gray = gray[y:y+h, x:x+w]
            eyes = eye_cascade.detectMultiScale(face_gray)
            
            if len(eyes) < 2:
                COUNTER += 1
                if COUNTER >= EYE_AR_CONSEC_FRAMES:
                    if not ALARM_ON:
                        ALARM_ON = True
                        alert_count += 1
                        pygame.mixer.music.play()
                        img_name = f'screenshot_{datetime.now().strftime("%Y%m%d%H%M%S")}.png'
                        cv2.imwrite(img_name, frame)
                    cv2.putText(frame, "DROWSINESS ALERT!", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            else:
                COUNTER = 0
                ALARM_ON = False

        cv2.imshow("Drowsiness Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    detection_end = datetime.now()
    alarm_status = "Yes" if pygame.mixer.music.get_busy() else "No"
    
    cap.release()
    cv2.destroyAllWindows()
    
    return detection_start, detection_end, img_name, alarm_status,alert_count

# Update the Detection_system table with the necessary information
def update_detection_system(driver_employee_id, detection_start, img_name, alarm_status, detection_end):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO Detection_system1 (driver_employee_id, driver_detection_start, driver_capture_image, driver_alarm_alert, driver_detection_end_time)
    VALUES (?, ?, ?, ?, ?)
    ''', (driver_employee_id, detection_start, img_name, alarm_status, detection_end))
    
    conn.commit()
    conn.close()

def generate_pdf_enhanced(driver_details, vehicle_details, detection_start, detection_end, alert_count, alarm_status):
    pdf = FPDF()
    pdf.add_page()

    # Header: Add a logo at the top-center
    pdf.image(LOGO_PATH, x=85, y=10, w=40)  # Adjust the size and positioning as per your logo
    pdf.ln(60)  # Move below the logo

    # Driver Details Centered
    pdf.set_font("Arial", 'B', size=16)
    pdf.cell(0, 10, txt="Driver Monitoring Report", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.ln(5)
    col_width = 63.3
    pdf.set_fill_color(200, 220, 255)
    pdf.ln(10)
    
    # Split into Field Name and Field Value
    field_width = 90  # width for the field name
    value_width = 90  # width for the field value
    pdf.cell(field_width, 10, txt="Driver Name:", border=1, fill=True, ln=False)
    pdf.cell(value_width, 10, txt=f"{driver_details[1]}", border=1, ln=True)

    pdf.cell(field_width, 10, txt="Driver Licence ID:", border=1, fill=True, ln=False)
    pdf.cell(value_width, 10, txt=f"{driver_details[2]}", border=1, ln=True)
    pdf.cell(field_width, 10, txt="Mobile Number:", border=1, fill=True, ln=False)
    pdf.cell(value_width, 10, txt=f"{driver_details[3]}", border=1, ln=True)
    # Split into Field Name and Field Value
    field_width = 90  # width for the field name
    value_width = 90  # width for the field value
    pdf.cell(field_width, 10, txt="Vehicle Type:", border=1, fill=True, ln=False)
    pdf.cell(value_width, 10, txt=f"{vehicle_details[1]}", border=1, ln=True)
    pdf.cell(field_width, 10, txt="Vehicle Number:", border=1, fill=True, ln=False)
    pdf.cell(value_width, 10, txt=f"{vehicle_details[2]}", border=1, ln=True)
    pdf.cell(field_width, 10, txt="Vehicle Model:", border=1, fill=True, ln=False)
    pdf.cell(value_width, 10, txt=f"{vehicle_details[3]}", border=1, ln=True)
    
    pdf.ln(10)
    col_width = 63.3
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(col_width, 10, txt="Detection Start", border=1, fill=True)
    pdf.cell(col_width, 10, txt="Detection End", border=1, fill=True)
    pdf.cell(col_width, 10, txt="Alarm Status", border=1, fill=True, ln=True)
    pdf.cell(col_width, 10, txt=str(detection_start), border=1)
    pdf.cell(col_width, 10, txt=str(detection_end), border=1)
    pdf.cell(col_width, 10, txt=alarm_status, border=1, ln=True)

    # Footer
    pdf.set_y(-50)  # Move 50 from the bottom
    pdf.set_font("Arial", 'I', size=8)
    pdf.cell(0, 10, txt="Department Address: RTC HOUSE, 1st Floor NTR administration Block, Pandit Nehru Bus Station in Vijayawada-520013", ln=True, align='C')
    pdf.cell(0, 10, txt="Support: ctmcomm@apsrtc.ap.gov.in | +91-9959222746", ln=True, align='C')

    file_name = f"report_{driver_details[0]}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    pdf.output(file_name)
    print(f"Report generated: {file_name}")

    # Footer
    pdf.set_y(-50)  # Move 50 from the bottom
    pdf.set_font("Arial", 'I', size=8)
    pdf.cell(0, 10, txt="Department Address: 1234 Main St, Your City", ln=True, align='C')
    pdf.cell(0, 10, txt="Support: support@department.com | 123-456-7890", ln=True, align='C')

def main():
    setup_database()
    driver_employee_id = int(input('Enter the valid Driver employee id:'))  
    driver_details = fetch_driver_details(driver_employee_id)
    vehicle_details = fetch_vehicle_details(driver_employee_id)

    if not driver_details:
        print("Error fetching driver details.")
        return

    if not authenticate_with_otp_gui(driver_details[3]):
        print("Invalid OTP!")
        return

    detection_start, detection_end, img_name, alarm_status,alert_count = start_face_detection()
    if detection_start and detection_end:
        update_detection_system(driver_employee_id, detection_start, img_name, alarm_status, detection_end)
        duration = detection_end - detection_start
        if duration > timedelta(seconds=10):
            generate_pdf_enhanced(driver_details, vehicle_details, detection_start, detection_end, alert_count, alarm_status)
        else:
            print("Duration was less than 10 seconds. No report generated.")

if __name__ == "__main__":
    main()
