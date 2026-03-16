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

bp = Blueprint('guides', __name__,subdomain="guides")
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
try:
    SUBDOMAIN = os.getenv("SUBDOMAIN")
except:
    print("Bulunamadı")
def allowed(filename):
    return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED

@bp.route("/",subdomain="guides")
def guides_home():
        recipes=Recipe.query.all()
        return render_template("guides.html",recipes=recipes)
@bp.route("/recipes/<int:id>",subdomain="guides")
def recipe_detail(id):
        recipe = Recipe.query.get_or_404(id)
        return render_template("recipe.html", recipe=recipe)
@bp.route("/recipes/<int:id>/delete", methods=["POST"],subdomain="guides")
def delete_recipe(id):
        if not session.get("can_delete"):
            abort(403)
        
        recipe = Recipe.query.get_or_404(id)
        db.session.delete(recipe)
        db.session.commit()
        return redirect(url_for("guides.guides_home"))


@bp.route("/add", methods=["GET","POST"],subdomain="guides")
def add():
        if request.method == "POST":
            file = request.files["image"]
            if file:
                                    
                filename = secure_filename(file.filename)

            # Klasör yoksa oluştur
                upload_folder = current_app.config["UPLOAD_FOLDER_GUIDES"]
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)

                path = os.path.join(upload_folder, filename)
                file.save(path)

            # image_url başına / koyarak tarayıcıya doğru yol ve
            else:
                file="NONE"
            if file:
                r = Recipe(
                        title=request.form["title"],
                        image_url=f"uploads/{filename}",
                        desc=request.form["desc"],
                        ingredients=request.form["ingredients"],
                        steps=request.form["steps"]
                )
            else:
                 r=Recipe(
                      title=request.form["title"],
                      image_url="NONE",
                      desc=request.form["desc"],
                      ingredients=request.form["ingredients"],
                      steps=request.form["steps"]
                 )    
            db.session.add(r)
            db.session.commit()
            return redirect(url_for("guides.guides_home"))

        return render_template("add_guide.html")
