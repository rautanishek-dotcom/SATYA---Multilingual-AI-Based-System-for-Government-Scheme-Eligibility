# SATYA

## Multilingual AI-Based Government Scheme Eligibility Platform

SATYA (System for AI-based Transparency and Yielding Assistance) is a web application for discovering Indian government schemes and assessing a user's eligibility. It combines a rule-based eligibility engine, multilingual assistance, document processing, identity verification, and a protected Document Vault.

The project is intended to reduce the difficulty of finding relevant schemes and preparing trustworthy supporting information. SATYA is an educational project and is not affiliated with any government agency.

## Project Overview

SATYA provides:

- User registration and login.
- Government scheme browsing and eligibility assessment.
- A multilingual chatbot and user interface.
- Document upload, classification, OCR, and verification.
- Identity Lock based on verified Aadhaar information.
- A Document Vault protected by Gmail SMTP OTP verification.
- Administrative and diagnostic endpoints for project operation.

The frontend is a React application served by Vite. The backend is a Flask REST API that stores application data and document metadata in MongoDB.

## Key Features

### Authentication

- User registration with a bcrypt-hashed password.
- Login using email and password.
- JWT access tokens for protected API requests.
- Flask session cookies for short-lived session state such as Document Vault OTP verification.
- Logout that clears the server-side Flask session and removes the frontend login state.

### Government Scheme Eligibility

- Scheme listing and category browsing.
- Eligibility evaluation using user-provided attributes and the configured scheme rules.
- Eligibility verification endpoints that can use verified identity and OTP-protected email verification.
- Scheme data stored in MongoDB.

### Document Vault

- Upload and storage of supported identity and supporting documents.
- Document classification and type-specific verification.
- OCR extraction and review of fields such as name, date of birth, gender, and document identifiers.
- Confidence, quality, fraud, QR, and verification results where produced by the processing pipeline.
- Search, preview, download, and delete operations for the user's stored documents.
- Review and correction flow for documents awaiting review.
- Identity Lock enforcement for documents that require a verified identity.

### Identity Verification and Identity Lock

- Aadhaar OCR and offline e-KYC processing paths.
- Identity matching against the authenticated user's stored identity profile.
- Persistent Identity Lock state stored with the user account.
- Identity Lock information includes the verified identity profile, verification time, document type, verification method, and confidence when available.
- A locked identity is not silently replaced by a later upload.
- Reset Identity verifies the user's existing login password, clears identity verification data, and keeps the login account intact. It does not use Document Vault OTP.

### OCR and Document Processing

- Image preprocessing with OpenCV and Pillow.
- PaddleOCR as the primary OCR engine where available.
- Tesseract OCR fallback support through `pytesseract`.
- Document-specific field extraction and normalization.
- QR and barcode processing support.
- Document quality checks and confidence calculations.
- Local storage of uploaded files, thumbnails, and processing artifacts.

### Email OTP Protection

- Gmail SMTP delivery through the existing Flask-Mail email service.
- OTP recipients are obtained from the logged-in user's registered email in MongoDB.
- OTP values are hashed before storage and are never returned to the frontend.
- OTPs have expiration and verification-attempt protections.
- The same OTP infrastructure supports Document Vault and eligibility verification purposes.

### Multilingual Support

- React localization through i18next and react-i18next.
- Translation support in the backend using language detection and translation libraries.
- The frontend includes English and additional Indian-language options configured in `frontend/src/i18n.js`.

## Document Vault Security

Document Vault access is protected by the existing Gmail SMTP OTP flow:

1. The user logs in and opens Document Vault.
2. The backend checks the current Flask login session.
3. If the session has not verified the vault, an OTP is sent to the user's registered MongoDB email address.
4. The user enters the OTP in the existing UI.
5. After successful verification, the backend marks the current session as vault-verified.

The verification state is session-level, not a permanent user-account flag:

- The vault remains unlocked while the current authenticated session is active.
- Navigation to another section does not require another OTP.
- Returning to Document Vault during the same session does not require another OTP.
- Refreshing the page during the same session does not require another OTP.
- The session check occurs before the locked-vault/OTP card is rendered, preventing an OTP card flash for an already verified session.
- Logout clears the Flask session verification state.
- When the same user logs in again, a new login session starts and Document Vault requires OTP again.
- A previous verified OTP record must not permanently unlock future login sessions.

Gmail SMTP settings, OTP generation, expiration, hashing, and validation are handled by the existing backend services. The frontend does not store OTPs or credentials.

## Identity Lock

After successful Aadhaar verification and confirmation, SATYA stores an identity profile associated with the user's account. The profile can include:

- Full name.
- Date of birth.
- Gender.
- Masked Aadhaar/reference information where available.
- Verification status and timestamp.
- Verification method and confidence.

The backend is the source of truth for Identity Lock state. Documents that require identity verification are checked against the stored profile, and a new identity document cannot silently replace an already locked identity.

### Reset Identity

Reset Identity is separate from Document Vault OTP:

- It requires the user's existing login password.
- It uses the existing bcrypt password verification mechanism.
- It does not send or request Gmail OTP.
- It does not change the user's password.
- It does not delete the user's account, email, user ID, or login credentials.
- It clears the persisted Identity Lock and stored identity verification profile.
- It removes identity-linked Aadhaar verification records according to the current implementation.
- It preserves unrelated user documents and application data.
- It removes reset metadata and has no 24-hour reset restriction.
- After reset, the user can start identity verification again.

An incorrect password leaves the identity data unchanged and returns an authentication error.

## Authentication and Sessions

The application uses two complementary mechanisms:

- JWT: the login endpoint returns a token, and the frontend sends it as a Bearer token to protected API routes.
- Flask session: the backend stores temporary session state in a signed Flask session cookie. Document Vault verification is stored there for the current login session.

The logout endpoint clears the Flask session. The frontend logout action also removes the locally stored access token and user summary. Secrets such as the JWT signing secret, Flask secret key, database URI, and mail password are loaded from environment configuration and are not documented here.

## Technology Stack

### Frontend

- React.
- Vite.
- React Router.
- i18next and react-i18next.
- Framer Motion.
- Lucide React.
- CSS with project-specific design tokens and inline component styling.

### Backend

- Python.
- Flask.
- Flask-CORS.
- Flask-Mail for SMTP email delivery.
- PyMongo for MongoDB access.
- PyJWT for JWT tokens.
- bcrypt for password and OTP hashing.

### OCR and Document Processing

- PaddleOCR and PaddlePaddle.
- Tesseract through pytesseract.
- OpenCV and NumPy.
- Pillow.
- pyzbar for QR/barcode support.
- BeautifulSoup and lxml for configured scraping tasks.

### Translation and Language Services

- langdetect.
- deep-translator.
- googletrans.

### Database and Storage

- MongoDB database named `Satya` by default.
- Local filesystem directories for uploads, vault files, thumbnails, and temporary processing files.

## Project Structure

```text
.
|-- backend/
|   |-- app.py                         Flask application entry point
|   |-- database.py                    MongoDB initialization and access
|   |-- routes/                        Flask route blueprints
|   |-- services/                      OTP and email services
|   |-- vault/                         Vault, OCR, identity, and security logic
|   |-- document_intelligence/         Document processing pipeline
|   |-- data/                          Backend data and translation cache
|   |-- tests/                         Backend tests
|   |-- scripts/                       Maintenance scripts
|   |-- uploads/                       Temporary upload storage
|   |-- vault_storage/                 Stored vault files
|   |-- vault_thumbnails/              Generated thumbnails
|   |-- temp_uploads/                  Temporary preprocessing files
|   |-- requirements.txt                Python dependencies
|   `-- .env                            Local environment configuration
|-- frontend/
|   |-- src/
|   |   |-- components/                Shared UI components
|   |   |-- pages/                     Application pages
|   |   |-- i18n.js                    Frontend localization configuration
|   |   `-- index.css                  Global styles and design tokens
|   |-- package.json                    Frontend scripts and dependencies
|   `-- vite.config.js                 Vite configuration
|-- database.py                         Root-level compatibility module
|-- run.bat                             Windows development launcher
`-- README.md
```

Important backend route modules include `auth.py`, `otp_routes.py`, `vault_routes.py`, `eligibility_routes.py`, `schemes.py`, `chatbot.py`, `verification.py`, `admin.py`, and `scraper_status.py`.

## Environment Configuration

Environment files are used for local configuration. Do not copy real secrets into documentation or source code.

Typical configuration categories include:

```text
MONGO_URI=YOUR_VALUE_HERE
JWT_SECRET=YOUR_VALUE_HERE
SECRET_KEY=YOUR_VALUE_HERE
MAIL_BACKEND=YOUR_VALUE_HERE
MAIL_SERVER=YOUR_VALUE_HERE
MAIL_PORT=YOUR_VALUE_HERE
MAIL_USE_TLS=YOUR_VALUE_HERE
MAIL_USE_SSL=YOUR_VALUE_HERE
MAIL_USERNAME=YOUR_VALUE_HERE
MAIL_PASSWORD=YOUR_VALUE_HERE
MAIL_DEFAULT_SENDER=YOUR_VALUE_HERE
```

The backend email service reads Gmail SMTP configuration from environment variables. Use a Google App Password for SMTP when required by the Gmail account. Never put the real password or any other secret in this README.

## Installation and Setup

### Prerequisites

- Python 3.10 or newer.
- Node.js and npm.
- A running MongoDB instance, or a reachable MongoDB URI.
- Tesseract OCR installed and available to the backend where required.
- PaddleOCR/PaddlePaddle runtime requirements for the primary OCR path.

### Backend

From the repository root on Windows PowerShell:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

The Flask API runs on `http://localhost:5000` when started through `app.py`. If the environment does not already provide Flask-Mail, install the package in the active virtual environment because the email service imports it directly.

### Frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

The Vite development server normally runs at `http://localhost:5173`.

### Windows Launcher

From the repository root, `run.bat` starts the backend and frontend in separate command windows:

```text
run.bat
```

## Development Workflow

1. Start MongoDB and confirm the configured URI is reachable.
2. Activate the backend virtual environment.
3. Start `python app.py` from `backend/`.
4. Start `npm run dev` from `frontend/`.
5. Use the frontend at `http://localhost:5173` and the backend health/API endpoints at `http://localhost:5000`.
6. Use `npm run build` to create a production frontend build.
7. Use `npm run lint` for frontend ESLint checks.

## API Overview

The backend registers these route groups:

| Prefix | Purpose |
| --- | --- |
| `/api/auth` | Registration, login, and logout |
| `/api/schemes` | Scheme listing, categories, and eligibility calculations |
| `/api/chatbot` | Chatbot messages and suggestions |
| `/api/verify` | Legacy/general document verification and Aadhaar operations |
| `/api/vault` | Upload, extraction, review, identity, storage, analytics, and vault health |
| `/api/otp` | OTP send, verify, resend, and status operations |
| `/api/eligibility` | Eligibility verification and OTP-backed eligibility operations |
| `/api/admin` | Administrative dashboard and management operations |
| `/api/scraper` | Scraper status and operational controls |

Important existing endpoints include:

### Authentication

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`

### OTP

- `POST /api/otp/send`
- `POST /api/otp/verify`
- `POST /api/otp/resend`
- `GET /api/otp/status`

Document Vault OTP requests use the `document_verification` purpose. Eligibility OTP requests use the `eligibility_check` purpose.

### Document Vault

- `POST /api/vault/upload`
- `POST /api/vault/extract`
- `POST /api/vault/confirm_review`
- `POST /api/vault/confirm_review_with_otp`
- `GET /api/vault/`
- `GET /api/vault/documents`
- `GET /api/vault/identity`
- `POST /api/vault/identity/reset`
- `DELETE /api/vault/<document_id>`
- `GET /api/vault/download/<document_id>`
- `GET /api/vault/preview/<document_id>`
- `GET /api/vault/thumbnail/<document_id>`
- `GET /api/vault/health`
- `GET /api/vault/analytics`

Protected endpoints require the Bearer token returned by login. Document Vault OTP status and verification additionally use the Flask session cookie.

## Security Notes

- Passwords are hashed with bcrypt before storage.
- Protected API routes validate JWT Bearer tokens.
- Flask session state is used for current-session Document Vault verification.
- Logout clears the Flask session, including the vault verification flag.
- OTPs are generated and hashed by the backend service, with expiration and attempt controls.
- OTP recipients are resolved from the authenticated user's MongoDB record.
- Gmail SMTP credentials are loaded from environment configuration.
- Identity Lock state is persisted in the user record and enforced by backend verification logic.
- Reset Identity requires the existing login password and does not use OTP.
- Uploaded files and vault payloads are processed through the project's storage and security helpers.

These controls do not replace production security review, secure deployment configuration, access-control hardening, or official government verification.

## Troubleshooting

### Backend does not start

- Confirm the virtual environment is active.
- Run `pip install -r backend/requirements.txt`.
- Check that MongoDB is running and `MONGO_URI` is valid.
- Review the first import or initialization error printed by Flask.
- Confirm Tesseract is installed if routes that use it are enabled.

### Frontend does not start

- Confirm Node.js and npm are installed.
- Run `npm install` from `frontend/`.
- Check that port `5173` is available.
- Confirm the backend is running on port `5000`.

### OTP is not arriving

- Confirm the backend loaded the intended `MAIL_SERVER`, `MAIL_PORT`, TLS, username, and password configuration.
- Use a Gmail App Password rather than the normal Gmail account password when required.
- Confirm `MAIL_BACKEND` selects SMTP rather than a console, file, or dry-run backend.
- Confirm the recipient email belongs to the logged-in MongoDB user.
- Check the recipient Inbox, Spam, Promotions, and Gmail filters.
- Review backend SMTP diagnostics and errors without exposing credentials or OTP values.

### Document Vault asks for OTP after returning

- Confirm the browser allows cookies for the local frontend/backend combination.
- Confirm requests to `/api/otp/status` include credentials and the JWT Bearer token.
- Confirm logout was not triggered in another tab.
- A new login session is expected to require a new OTP.

### OCR or document processing fails

- Confirm the file type and size are supported.
- Confirm Tesseract is installed and available on the configured system path.
- Allow additional startup time for OCR model initialization.
- Check the backend console for classification, OCR, quality, QR, or storage errors.
- Verify that temporary upload and vault storage directories are writable.

### Identity Lock or reset state looks stale

- Refresh the vault after the backend has completed the operation.
- Confirm the request uses the currently logged-in user's token and ID.
- For Reset Identity, enter the existing login password, not an OTP.
- Review the backend response and MongoDB user/document records without exposing identity data.

## Important Security Rules

- Never commit `.env` files or real environment values.
- Never commit Gmail SMTP passwords or Google App Passwords.
- Never expose JWT secrets, Flask secret keys, database credentials, API keys, passwords, or OTPs.
- Never log plaintext passwords, App Passwords, OTPs, JWTs, or unnecessary identity/document data.
- Do not store OTPs or credentials in localStorage, source code, or API responses.
- Use the existing authentication and session mechanisms for protected flows.
- Resolve OTP recipients from the authenticated user's registered database email; do not hardcode recipient addresses.
- Keep user identity data and uploaded documents restricted to the appropriate authenticated account.
- Remove secrets from logs and screenshots before sharing diagnostics.

## License and Project Use

SATYA is an educational and research project. It does not replace official government portals, government verification, legal advice, or eligibility decisions made by the relevant authorities.
