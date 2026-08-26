import os
import sys

# Add backend directory to sys path to import vault
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vault.field_extractor import FieldExtractor

def run_test(case_num, test_text, expected_name):
    # Mocking ocr_result
    ocr_result = {
        "full_text": test_text,
        "words": []
    }
    
    print(f"\n--- RUNNING CASE {case_num} ---")
    print(f"INPUT TEXT:\n{test_text}\n---")
    
    fields_result = FieldExtractor.extract_fields(ocr_result)
    fields = fields_result.get("fields", {})
    
    extracted_name = fields.get("name", {}).get("value")
    
    print(f"EXPECTED: {expected_name}")
    print(f"GOT:      {extracted_name}")
    
    if extracted_name == expected_name:
        print("[PASS]")
        return True
    else:
        print("[FAIL]")
        return False

cases = [
    (1, "Name: ABHISHEK KUMAR RAUT\nDOB: 01/01/2000\nGender: Male", "ABHISHEK KUMAR RAUT"),
    (2, "Name\nABHISHEK KUMAR RAUT\nDOB\n01/01/2000\nMale", "ABHISHEK KUMAR RAUT"),
    (3, "ABHISHEK KUMAR RAUT\nDOB: 01/01/2000\nGender: Male", "ABHISHEK KUMAR RAUT"),
    (4, "Nane:\nABHISHEK KUMAR RAUT\nDOB: 01/01/2000\nMale", "ABHISHEK KUMAR RAUT"),
    (5, "Father's Name: RAM KUMAR\nName: ABHISHEK KUMAR RAUT\nDOB: 01/01/2000", "ABHISHEK KUMAR RAUT"),
    (6, "ABHISHEK KUMAR RAUT\nDate of Birth: 01/01/2000\nGender: MALE\nAddress: ABC...", "ABHISHEK KUMAR RAUT"),
    (7, "DOB: 01/01/2000\nGender: MALE\nGovernment of India", None)
]

passed = 0
for case in cases:
    if run_test(*case):
        passed += 1

print(f"\nTOTAL PASSED: {passed}/{len(cases)}")
if passed == len(cases):
    print("ALL TESTS SUCCESSFUL.")
    sys.exit(0)
else:
    print("SOME TESTS FAILED.")
    sys.exit(1)
