import os,uuid
from flask import Flask,render_template,request,send_from_directory,send_file,redirect,session,url_for,Response,abort,jsonify,Blueprint
import requests
from flask_login import LoginManager, login_user, login_required, logout_user, current_user,UserMixin
from botocore.config import Config
from sqlalchemy import func,text
import io,zipfile
import boto3
from all_routes import bp
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from werkzeug.security import check_password_hash,generate_password_hash
from sqlalchemy.exc import IntegrityError
from all_classes import db,Account
from middleware import maintenance_mode
from all_routes_aitools import bp as aitools
from all_routes_camsepeti import bp as camsepeti
from all_routes_cards import bp as cards
from all_routes_guides import bp as guides
from all_routes_infinitecloud import bp as infinitecloud
from all_routes_pushgame import bp as pushgame
from all_routes_root import bp as root
load_dotenv()  # .env dosyasını yükler
try:
    load_dotenv(r"C:\Users\Mehmet Serdar EREN\Desktop\orasu2v.txt")
    print("LOCAL MODE: ENVIRONMENT SUCCESS")
except:
    pass
app=Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
s3 = boto3.client(
    service_name="s3",
    endpoint_url=f"https://{os.getenv('ACCOUNT_ID')}.r2.cloudflarestorage.com",
    aws_access_key_id=os.getenv("ACCESS_KEY"),
    aws_secret_access_key=os.getenv("SECRET_KEY"),
    region_name="auto"
)
DATABASE_URL=os.getenv("DATABASE_URL")
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    UPLOAD_PASSWORD=os.getenv("UPLOAD_PASSWORD")
    ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD")
else:
    app.config["SERVER_NAME"]="localhost:5000"
    load_dotenv(r"C:\Users\Mehmet Serdar EREN\Desktop\orasu2v.txt")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///local.db"

    app.config["SQLALCHEMY_BINDS"] = {
        "accounts": "sqlite:///accounts.db",
        "cards": "sqlite:///cards.db",
        "medias": "sqlite:///medias.db",
        "sitemessage": "sqlite:///sitemessage.db"
    }
    broadcast = {
        "message": None,
        "expires": None
    }

    UPLOAD_PASSWORD="yukle"
    ADMIN_PASSWORD_HASH = "admin"
db.init_app(app)
R2_BUCKET = "infinitecloud"
MAX_STORAGE = 10 * 1024 * 1024 * 1024
login_manager.login_view = "infinitecloud.login_ic"
DATABASE_URL = os.getenv("DATABASE_URL")
PYANYWHERE_UPLOAD_URL = "https://wf5528.pythonanywhere.com/upload"
PYANYWHERE_LIST_URL   = "https://wf5528.pythonanywhere.com/list"
PYANYWHERE_SECRET   = os.getenv("PYANYWHERE_SECRET")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "dev-token")  # 'dev-token' lokal için
HF_URL="https://wf5528-infinitesoft-tr.hf.space/remove-bg"
PA_EXE_URL = "https://wf5529.pythonanywhere.com/static/uygulama/infinitesoft-tr.exe"
UPLOAD_FOLDER_GUIDES = "static/uploads"
app.config["UPLOAD_FOLDER_GUIDES"] = UPLOAD_FOLDER_GUIDES
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret")
UPLOAD_FOLDER = "/home/wf5528/infinitecloud_api/uploads"
app.config["UPLOAD_FOLDER"]="uploads"
ALLOWED={"png","jpg","jpeg","mp4","mov","pdf","webp","mp3","pptx","zip"}
maintenance_mode(app)
# if DATABASE_URL:
#     with app.app_context():
#         # Schemaları oluştur
#         for schema_name in ["system", "storage", "auth", "details"]:
#             db.session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
#         db.session.commit()

#         # Tabloları oluştur
#         db.create_all()

#         # Kontrol (opsiyonel)
#         insp = inspect(db.engine)
#         for schema_name in ["system", "storage", "auth", "details"]:
#             print(f"Tables in schema '{schema_name}':", insp.get_table_names(schema=schema_name))
# aktif etmek için
MAINTANENCE=os.getenv("MAINTENANCE")
if MAINTANENCE=="True":
    app.config["MAINTENANCE"] = True
app.config["MAX_CONTENT_LENGTH"]=50*1024*1024


@login_manager.user_loader
def load_user(user_id):
    return Account.query.get(user_id)
@login_manager.unauthorized_handler
def unauthorized():
    host=request.host.split(".")[0]
    if host=="infinitecloud":
        return redirect(url_for("infinitecloud.login_ic", next=request.path))
    elif host=="camsepeti":
        return redirect(url_for("camsepeti.login", next=request.path))

# with app.app_context():
#     db.create_all()
# app_db_init.py veya app.py içinde deploy sırasında çalıştır

# POSTGRESQL DEĞİŞTİĞİ ZAMAN:
# with app.app_context():
#     # 1️⃣ Schemaları oluştur
#     for schema_name in ["system", "storage", "auth", "details"]:
#         db.session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
#     db.session.commit()

#     # 2️⃣ Tabloları oluştur (model class'larından alır)
#     # Eğer modeller başka dosyada, örn: app/models.py → import et

#     db.create_all()

#     # 3️⃣ Kontrol (opsiyonel, loglara düşer)
#     insp = inspect(db.engine)
#     for schema_name in ["system", "storage", "auth", "details"]:
#         print(f"Tables in schema '{schema_name}':", insp.get_table_names(schema=schema_name))
SUBDOMAIN=os.getenv("SUBDOMAIN")
if SUBDOMAIN=="true":
    app.register_blueprint(camsepeti)
    app.register_blueprint(infinitecloud)
    app.register_blueprint(pushgame)
    app.register_blueprint(cards)
    app.register_blueprint(aitools)
    app.register_blueprint(root)
    app.register_blueprint(guides)
else:
    app.register_blueprint(bp)
@app.errorhandler(404)
def page_not_found(e):
        return render_template("404.html"),404
@app.errorhandler(403)
def forbidden(e):
        return render_template("403.html"),403
@app.errorhandler(405)
def wrong_direction_to_come(e):
        return render_template("405.html"),405
@app.errorhandler(500)
def internal_error(e):
        return render_template("500.html"), 500
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)