# SATYA - Multilingual AI-Based System for Government Scheme Eligibility

**SATYA** is an intelligent web-based platform designed to bridge the awareness gap surrounding government schemes in India. It enables users to input personal information, uses an eligibility engine to match them with relevant government welfare schemes, and assists them through an AI-powered multilingual chatbot.

## Features

- **Multilingual Support**: Available in English, Hindi, and Kannada using `i18next`.
- **AI Eligibility Engine**: Rule-based matching engine predicting scheme eligibility based on age, gender, state, district, income, occupation, category, and special statuses.
- **Premium User Interface**: Modern, responsive, and beautifully designed user interface utilizing glassmorphism, responsive grid layouts, and carefully curated colors.
- **Floating Chatbot Assistant**: Embedded conversational assistant to help users find schemes in plain language.
- **Comprehensive Scheme Database**: Currently seeded with a sample dataset of 50 government schemes.
- **Secure Authentication**: End-to-end user authentication with JWT, bcrypt password hashing.

---

## Tech Stack

### Frontend
- **React.js** (Vite template)
- **React Router** for navigation
- **Lucide React** for icons
- **React i18next** for localization
- **Vanilla CSS** with premium design tokens

### Backend
- **Python Flask** for REST API
- **PyMongo** for MongoDB Integration
- **Flask-CORS** for Cross-Origin resource sharing
- **PyJWT & bcrypt** for secure authentication

### Database
- **MongoDB** (Local or Atlas)
  
---

## Installation & Setup

### Requirements
- Node.js (v18+)
- Python (v3.10+)
- MongoDB Database Server running locally at `localhost:27017`

### 1. Database Setup
Ensure that you have MongoDB installed. You can either use a local instance or modify the DB URI in the `.env` file of the backend.

### 2. Backend Setup
1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Virtual Environment:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Mac/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Seed the Database with 50 Government Schemes:
   ```bash
   python seed.py
   ```
5. Start the backend Flask server:
   ```bash
   python app.py
   ```
   *The server runs on `http://localhost:5000`.*

### 3. Frontend Setup
1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
   *The frontend runs on `http://localhost:5173`.*

---

## Folder Structure

```
SATYA/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── i18n.js
│   │   └── index.css    (Global Styling & Premium Theme Tokens)
│   ├── package.json
│   └── vite.config.js
│
├── backend/
│   ├── routes/          (API endpoints)
│   ├── database.py      (MongoDB initialization)
│   ├── seed.py          (Script to populate Scheme database)
│   ├── app.py           (Flask server entrypoint)
│   └── requirements.txt
│
└── README.md
```

