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
bp=Blueprint("camsepeti",__name__,subdomain="camsepeti")
@bp.route("/home",subdomain="camsepeti")
@login_required
def home_shop():
    return render_template("home.html")
@bp.route("/sepete_ekle",methods=["POST"],subdomain="camsepeti")
@login_required
def sepete_ekle():
        urun={
            "ad": request.form["ad"],
            "fiyat": request.form["fiyat"],
            "resim":request.form["resim"]
        }
        if "sepet" not in session:
            session["sepet"]=[]
        sepet=session["sepet"]
        sepet.append(urun)
        session["sepet"]=sepet
        return redirect(url_for("camsepeti.home_shop"))
@bp.route("/sepet_sil", methods=["POST"],subdomain="camsepeti")
@login_required
def sepet_sil():
        index = int(request.form["index"])

        sepet = session.get("sepet", [])

        if 0 <= index < len(sepet):
            sepet.pop(index)
            session["sepet"] = sepet

        return redirect(url_for("camsepeti.sepet"))
@bp.route("/buy_success",methods=["POST"],subdomain="camsepeti")
@login_required
def buy_success():
        return render_template("buy_success.html")
@bp.route("/sepet",subdomain="camsepeti")
@login_required
def sepet():
        return render_template("sepet.html",sepet=session.get("sepet"))
@bp.route("/buy",subdomain="camsepeti")
@login_required
def buy():
        return render_template("buy.html")

@bp.route("/register",methods=["GET","POST"],subdomain="camsepeti")
def register():
        if request.method=="POST":
            name=request.form["name"]
            password=request.form["password"]

            if Account.query.filter_by(name=name).first():
                return "Bu kullanıcı adı zaten var"

            try:
                hashed_pw=generate_password_hash(password)
                new_user=Account(name=name,password=hashed_pw)
                db.session.add(new_user)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                return "Bu kullanıcı adı zaten var"
            except Exception as e:
                db.session.rollback()
                return f"GERÇEK HATA: {e}"

            return redirect(url_for("camsepeti.login"))
        return render_template("register.html")

@bp.route("/",methods=["GET","POST"],subdomain="camsepeti")
def login():
        if request.method=="POST":
            name=request.form["name"]
            password=request.form["password"]
            user=Account.query.filter_by(name=name).first()
            if user and check_password_hash(user.password,password):
                login_user(user)
                session["user_id"]=user.id
                next_page = request.args.get("next")

                if next_page:
                    return redirect(next_page)

                return redirect(url_for("camsepeti.home_shop"))
            else:
                return "Hatalı giriş❌"
        return render_template("login.html")
@bp.route("/logout",subdomain="camsepeti")
@login_required
def logout():
        logout_user()
        return redirect(url_for("camsepeti.login"))
@bp.route("/create_db")
def create_db():
        if not session.get("can_delete"):
            abort(403)
        db.create_all()
        return redirect(url_for("app.projects"))
