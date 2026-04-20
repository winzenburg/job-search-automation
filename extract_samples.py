import fitz  # PyMuPDF
import glob
import os

pdf_files = [
    "/Users/ryanwinzenburg/Library/CloudStorage/GoogleDrive-ryanwinzenburg@gmail.com/My Drive/Projects/job-search/Cover Letter - Airbnb.pdf",
    "/Users/ryanwinzenburg/Library/CloudStorage/GoogleDrive-ryanwinzenburg@gmail.com/My Drive/Projects/job-search/Ryan_Winzenburg_Resume_ATS_Optimized.pdf"
]

print("--- COVER LETTER SAMPLE (AIRBNB) ---")
doc = fitz.open(pdf_files[0])
for page in doc:
    print(page.get_text())

print("\n--- RESUME SAMPLE (ATS OPTIMIZED) ---")
doc = fitz.open(pdf_files[1])
for page in doc:
    print(page.get_text())
