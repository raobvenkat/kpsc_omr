#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from CounterFoilScanning import process_single_sheet_for_demo

# Test with the image from the workspace
print("Processing test image: OMR/img1.jpg")
result = process_single_sheet_for_demo('OMR/img1.jpg')
print("Test completed successfully!")
print(f"Subject Code: {result.get('subject_code', 'N/A')}")
print(f"Booklet Number: {result.get('booklet_number', 'N/A')}")
print(f"Candidate Signed: {result.get('candidate_signed', 'N/A')}")
print(f"Invigilator Signed: {result.get('invigilator_signed', 'N/A')}")
print("Image processing completed without errors")
