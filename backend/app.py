from flask import Flask, jsonify
from flask_cors import CORS
from database import init_db
from routes.auth import auth_bp
from routes.schemes import schemes_bp
from routes.chatbot import chatbot_bp
from routes.verification import verification_bp
from routes.scraper_status import scraper_bp
from routes.admin import admin_bp
from routes.vault_routes import vault_bp
from routes.eligibility_routes import eligibility_bp
from routes.otp_routes import otp_bp
from services.email_service import init_mail

app = Flask(__name__)
CORS(app)

# Initialize Database
try:
    init_db(app)
    print("MongoDB Connected Successfully")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")

# Initialize Flask-Mail for Gmail SMTP
try:
    init_mail(app)
    print("Flask-Mail Initialized Successfully")
except Exception as e:
    print(f"Flask-Mail initialization warning: {e}")

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(schemes_bp, url_prefix="/api/schemes")
app.register_blueprint(chatbot_bp, url_prefix="/api/chatbot")
app.register_blueprint(verification_bp, url_prefix="/api/verify")
app.register_blueprint(scraper_bp, url_prefix="/api/scraper")
app.register_blueprint(admin_bp, url_prefix="/api/admin")
app.register_blueprint(vault_bp, url_prefix="/api/vault")
app.register_blueprint(eligibility_bp, url_prefix="/api/eligibility")
app.register_blueprint(otp_bp, url_prefix="/api/otp")

@app.route("/")
def home():
    return jsonify({"message": "Welcome to SATYA Backend API!"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)