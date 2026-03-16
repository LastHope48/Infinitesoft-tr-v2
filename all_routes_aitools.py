import os
from flask import Flask,render_template,request,send_from_directory,send_file,redirect,session,url_for,Response,abort,jsonify,Blueprint
from flask_login import LoginManager, login_user, login_required, logout_user, current_user,UserMixin
from botocore.client import Config
from werkzeug.security import check_password_hash,generate_password_hash
from flask import current_app
from all_classes import Project,Account,Media,SiteMessage,SiteUpdate,Card,Recipe,Version
from flask_sqlalchemy import SQLAlchemy
import boto3
import requests
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime, timedelta
import io,zipfile
from sqlalchemy import func,text
from all_classes import db
bp = Blueprint('aitools', __name__,subdomain="aitools")
R2_BUCKET="infinitecloud"
MAX_STORAGE = 10 * 1024 * 1024 * 1024
PYANYWHERE_UPLOAD_URL = "https://wf5528.pythonanywhere.com/upload"
ALLOWED={"png","jpg","jpeg","mp4","mov","pdf","webp","mp3","pptx","zip"}
PYANYWHERE_LIST_URL   = "https://wf5528.pythonanywhere.com/list"
PYANYWHERE_SECRET   = os.getenv("PYANYWHERE_SECRET")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "dev-token")  # 'dev-token' lokal için
HF_URL="https://wf5528-infinitesoft-tr.hf.space/remove-bg"
PA_EXE_URL = "https://wf5529.pythonanywhere.com/static/uygulama/infinitesoft-tr.exe"
UPLOAD_FOLDER_GUIDES = "static/uploads"
@bp.route("/")
def tools():
        return render_template("ai_tools.html")
@bp.route("/images")
def images():
        return render_template("images.html")
    
@bp.route("/backdeleter",methods=["GET","POST"])
def back_delete():
        return render_template("background_remover.html")
@bp.route("/backdeleter/remove", methods=["POST"])
def delete_back():
        file = request.files["image"]

        r = requests.post(
            HF_URL,
            files={"image": (file.filename, file.read())},
            timeout=60
        )

        return Response(
            r.content,
            mimetype="image/png"
        )