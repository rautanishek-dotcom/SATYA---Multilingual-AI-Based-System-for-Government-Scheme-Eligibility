import sys
sys.path.insert(0, '.')
import traceback

# Test 1: Does the pipeline crash?
try:
    from vault.ocr_utils import extract_structured_document_fields
    import cv2, numpy as np
    fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.imwrite('fake.jpg', fake_img)
    result = extract_structured_document_fields('fake.jpg', document_type='aadhaar_ocr')
    print('TEST 1 (no crash): PASS')
except Exception as e:
    print(f'TEST 1 (no crash): FAIL - {e}')
    traceback.print_exc()

# Test 2: Does the inline name extractor work?
try:
    from vault.ocr_utils import _extract_name_from_text_block

    # Simulated flat OCR text (the real failing case)
    flat_text = 'ey =e nAs Sd Cc coven ENT OT IDA ae YAN a pan AADHAAR Rakesh Ranjan 2004-03-27 Male'
    result = _extract_name_from_text_block(flat_text)
    name = result.get('value', '')
    status = 'PASS' if 'Rakesh Ranjan' in name else 'FAIL'
    print(f'TEST 2 (flat text): name="{name}" - {status}')

    # Normal multiline text
    multiline_text = 'Rakesh Ranjan\n2004-03-27\nMale'
    result2 = _extract_name_from_text_block(multiline_text)
    name2 = result2.get('value', '')
    status2 = 'PASS' if 'Rakesh' in name2 else 'FAIL'
    print(f'TEST 3 (multiline): name="{name2}" - {status2}')

    # Labelled text
    labelled_text = 'Name: Abhishek Kumar\nDOB: 01/01/2000\nGender: Male'
    result3 = _extract_name_from_text_block(labelled_text)
    name3 = result3.get('value', '')
    status3 = 'PASS' if 'Abhishek' in name3 else 'FAIL'
    print(f'TEST 4 (labelled): name="{name3}" - {status3}')

    # Name with 3 words
    three_word = 'ABHISHEK KUMAR RAUT 27/03/2004 Male'
    result4 = _extract_name_from_text_block(three_word)
    name4 = result4.get('value', '')
    status4 = 'PASS' if 'Abhishek' in name4 else 'FAIL'
    print(f'TEST 5 (3-word flat): name="{name4}" - {status4}')

except Exception as e:
    print(f'TESTS FAILED: {e}')
    traceback.print_exc()
