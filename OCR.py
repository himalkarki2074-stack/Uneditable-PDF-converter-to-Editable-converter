from PIL import Image
import pytesseract
import re

# Path to Tesseract OCR
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Load timesheet image
img = Image.open(r"C:\Users\HimalK\OneDrive - APTASK\Desktop\Aptask\Timesheets\Test\Francisco Rivera 0713.jpeg")

# OCR the whole image
text = pytesseract.image_to_string(img)

print("---- OCR OUTPUT ----")
print(text)
print("-------------------")

# Dynamic approach:
# Look for "Name" and capture text to the right (on same line)
lines = text.splitlines()
employee_name = None

for line in lines:
    # Look for 'Name' ignoring case and allow extra spaces
    if re.search(r'\bName\b', line, re.IGNORECASE):
        # Split line by 'Name' and take text after it
        parts = re.split(r'\bName\b', line, flags=re.IGNORECASE)
        if len(parts) > 1:
            # Clean and remove extra symbols
            candidate = parts[1].strip()
            # Keep only letters and spaces
            candidate = re.sub(r'[^A-Za-z\s]', '', candidate)
            if candidate:
                employee_name = candidate
                break

if employee_name:
    print("✅ Extracted Employee Name:", employee_name)
else:
    print("❌ Could not find employee name dynamically.")
