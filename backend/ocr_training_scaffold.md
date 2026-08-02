# OCR Training, Dataset Schema, and API Contract for SATYA

## 1. Training Dataset Schema for Indian Government Documents

### Purpose
This schema is designed to support fine-tuning and evaluation of OCR / document understanding models on Indian government documents such as Aadhaar, PAN, Passport, Driving Licence, Ration Card, Income Certificate, Caste Certificate, Disability Certificate, Birth Certificate, and related forms.

### Top-level record structure

- `document_id`: unique identifier for the document sample
- `user_id`: optional anonymized user identifier
- `document_type`: canonical type, e.g. `aadhaar_ocr`, `pan`, `passport`, `income_certificate`
- `document_label`: human-readable label for the document type
- `language`: primary language code, e.g. `en`, `hi`, `bn`, `mr`
- `source`: metadata about upload/origin
  - `file_name`
  - `file_type`
  - `file_hash`
  - `capture_date`
  - `source_app`
- `pages`: list of page-level objects
- `annotations`: structured labels for fields and layout
- `created_at`
- `notes`

### Page object

Each page includes raw image, OCR text, and segmentation metadata.

- `page_number`
- `image_path`
- `width`
- `height`
- `raw_text`
- `layout_blocks`: list of text/layout blocks
- `ocr_candidates`: optional OCR engine candidates
- `qr_data`: optional QR / barcode payloads

### Layout block object

Used for LayoutLMv3 / Donut / semantic layout-aware training.

- `block_id`
- `text`
- `label`: e.g. `header`, `name_field`, `dob_field`, `address`, `identity_number`
- `bbox`: normalized box `[x0, y0, x1, y1]` in page coordinates
- `page_number`
- `font_size`
- `confidence`

### Field annotation object

This is the core cleaned extraction target.

- `field_name`: canonical field key
- `value`: extracted text value
- `normalized_value`: normalized canonical form where applicable
- `confidence`: optional float
- `bbox`: optional bounding box `[x0, y0, x1, y1]`
- `source`: `ocr`, `qr`, `xml`, `document`, `classifier`
- `page_number`
- `field_type`: optional semantic type, e.g. `date`, `number`, `amount`
- `notes`

### Canonical fields for Indian government documents

Common fields:
- `name`
- `dob`
- `gender`
- `address`
- `identity_number`
- `masked_aadhaar`
- `aadhaar_reference_id`
- `certificate_number`
- `issuing_authority`
- `income`
- `caste`
- `category`
- `disability_percent`
- `disability_type`
- `parents`
- `bride`
- `groom`
- `marriage_date`
- `family_members`
- `document_language`
- `digital_signature`
- `qr_code_data`
- `barcode_data`

Document-specific required fields are defined in the backend policy.

### Example JSON record

```json
{
  "document_id": "sample-0001",
  "user_id": "anon-123",
  "document_type": "aadhaar_ocr",
  "document_label": "Aadhaar Card",
  "language": "en",
  "source": {
    "file_name": "aadhaar_front.jpg",
    "file_type": "image/jpeg",
    "file_hash": "...",
    "capture_date": "2026-07-25T12:00:00Z",
    "source_app": "mobile_upload"
  },
  "pages": [
    {
      "page_number": 1,
      "image_path": "images/sample-0001-page-1.jpg",
      "width": 2480,
      "height": 3508,
      "raw_text": "...",
      "layout_blocks": [
        {
          "block_id": "b1",
          "text": "Name",
          "label": "label",
          "bbox": [0.10, 0.08, 0.42, 0.13],
          "page_number": 1,
          "font_size": 18,
          "confidence": 95.0
        }
      ],
      "ocr_candidates": [
        {
          "engine": "paddleocr",
          "lang": "en",
          "text": "...",
          "confidence": 94.3
        }
      ],
      "qr_data": []
    }
  ],
  "annotations": {
    "fields": [
      {
        "field_name": "name",
        "value": "RAHUL KUMAR",
        "normalized_value": "Rahul Kumar",
        "confidence": 98.0,
        "bbox": [0.15, 0.10, 0.65, 0.16],
        "source": "ocr",
        "page_number": 1,
        "field_type": "text"
      }
    ]
  },
  "created_at": "2026-07-25T12:00:00Z",
  "notes": "Aadhaar front sample with English text"
}
```

## 2. Fine-tuning Pipeline

### a) PaddleOCR

Training for line/word recognition or box detection on Indian government documents.

1. Prepare dataset:
   - Use `train_data/` for images and annotation files.
   - Convert dataset to PaddleOCR format: `anns/*.txt` with `image_path\tword1 word2 ...`.
   - Include a vocabulary file for English plus Devanagari and other Indian scripts.

2. Example command:

```bash
python3 tools/train.py -c configs/rec/rec_r34_vd_tb.yml \
  -o Global.pretrain_weights=./pretrained/rec_r34_vd_none_bilstm_ctc_v2.0_train.tar \
  -o TrainReader.dataset.train_file_list=./train_data/train_list.txt \
  -o Global.save_model_dir=./output/paddleocr/ \
  -o Global.checkpoints=./output/paddleocr/checkpoint
```

3. Evaluation:

```bash
python3 tools/eval.py -c configs/rec/rec_r34_vd_tb.yml \
  -o Global.pretrain_weights=./output/paddleocr/best_accuracy.tar \
  -o Global.saved_model_dir=./output/paddleocr
```

### b) TrOCR

For document-level text recognition and weak-layout sequence extraction, fine-tune Hugging Face `microsoft/trocr-base-handwritten` or `microsoft/trocr-base-printed`.

1. Convert samples to Hugging Face `datasets` with:
   - `image` tensor
   - `text` target transcription

2. Example script invocation:

```bash
python train_trocr.py \
  --model_name_or_path microsoft/trocr-base-printed \
  --dataset_name ./datasets/trocr_ocr_dataset \
  --output_dir ./models/trocr-indian-documents \
  --per_device_train_batch_size 8 \
  --per_device_eval_batch_size 4 \
  --learning_rate 3e-5 \
  --num_train_epochs 5 \
  --fp16 \
  --remove_unused_columns false
```

3. Fine-tune targets:
   - `text` = full concatenated transcription per page
   - optionally include field labels as prompt tokens: `name: Rahul Kumar; dob: 1990-05-01; ...`

### c) Donut / LayoutLMv3

For structured field extraction and visual layout understanding.

1. Prepare dataset:
   - Page images
   - JSON labels with `input` / `output` pairs for Donut, or `tokens` + `bbox` + `labels` for LayoutLMv3.
   - Example for Donut: `question: Extract fields`, `answer: {"name": "Rahul Kumar", "dob": "1990-05-01", "identity_number": "ABCDE1234F"}`.
   - Example for LayoutLMv3: token-level transcription and normalized bounding boxes for each field value.

2. Example Donut-style `jsonl` entry:

```json
{
  "image": "images/sample-0001-page-1.jpg",
  "prompt": "Extract fields from this government document.",
  "answer": "{\"name\": \"Rahul Kumar\", \"dob\": \"1990-05-01\", \"identity_number\": \"ABCDE1234F\"}"
}
```

3. Example LayoutLMv3 tf-like entry:

```json
{
  "input_ids": [...],
  "bbox": [[100, 120, 450, 160], ...],
  "labels": ["O", "B-name", "I-name", ..., "B-dob", ...]
}
```

4. Training approach:
   - Use a visual tokenizer / image encoder for the document page.
   - For Donut: fine-tune with text-generation-style field extraction and a JSON-structured answer template.
   - For LayoutLMv3: fine-tune on token classification or sequence labeling with bounding boxes.
   - Use document-specific prompts to reduce field confusion and support multilingual layouts.

### d) End-to-end pipeline notes

- Start with OCR segmentation, then normalize field values.
- Keep a canonical field ontology matching `SUPPORTED_DOCUMENT_TYPES` in `backend/vault/policy.py`.
- Collect both raw OCR candidates and cleaned field outputs for model training.
- For Indian government documents, include bilingual OCR examples whenever possible.
- Use synthetic augmentation for scripts, handwritten variations, and low-quality scans.

## 3. API Contract for Clean Field Objects

### New endpoint

`POST /api/vault/extract`

### Request

- `user_id` (form/data or JSON)
- `file` (multipart file upload)
- `share_code` (optional, for Aadhaar offline e-KYC ZIP)
- `force_engine` (optional, e.g. `aadhaar_ocr`, `income_verifier`, `caste_verifier`, `ration_verifier`, `disability_verifier`)

### Response

```json
{
  "status": "EXTRACTED",
  "message": "Field extraction complete",
  "classification": {
    "document_type": "aadhaar_ocr",
    "document_label": "Aadhaar Card",
    "confidence": 100.0,
    "verification_engine": "aadhaar_ocr",
    "supported": true
  },
  "quality": {
    "quality_score": 92,
    "passed": true,
    "issues": []
  },
  "fields": {
    "name": {"value": "Rahul Kumar", "confidence": 98.0, "source": "document"},
    "dob": {"value": "1990-05-01", "confidence": 95.0, "source": "document"},
    "gender": {"value": "Male", "confidence": 96.0, "source": "document"},
    "masked_aadhaar": {"value": "XXXX-XXXX-1234", "confidence": 96.0, "source": "document"},
    "address": {"value": "123 Sample Street, Delhi", "confidence": 88.0, "source": "document"}
  },
  "raw_text": "...",
  "ocr_candidates": [
    {"engine": "paddleocr", "lang": "en", "text": "...", "confidence": 93.5}
  ],
  "qr": {
    "qr_data": ["..."],
    "barcode_data": []
  },
  "missing_fields": [],
  "validation": {
    "required_fields": ["name", "dob", "gender", "masked_aadhaar"],
    "document_type": "aadhaar_ocr"
  }
}
```

### UI contract guidance

- Use `fields` as the canonical source for extracted values.
- Display `missing_fields` and required field rules clearly.
- Preserve `quality` and `classification` for user-facing verification feedback.
- Use `ocr_candidates` only for debugging or fallback UI.
- For confirmed user input, the UI may send `confirm_match=true` to the verification endpoint if needed.

### Recommended UI flow

1. Upload document to `/api/vault/extract`.
2. Receive `fields`, `classification`, and `missing_fields`.
3. Show extracted values in a review form.
4. If user confirms, send to `/api/vault/<verify-route>` to complete verification.
5. Handle `CONFIRMATION_REQUIRED` or `REJECTED` responses with clear messaging.

## 4. Notes for implementation

- The data schema reflects actual document field labels used in the backend.
- The new endpoint returns clean structured objects without storing them in the vault.
- Use `SUPPORTED_DOCUMENT_TYPES` in `backend/vault/policy.py` as the single source of truth for field requirements.
- Add training examples matching the contract field names so the model outputs align with the UI.
