import os
from flask import Flask,render_template,request,send_from_directory,send_file,redirect,session,url_for,Response,abort,jsonify,Blueprint,flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user,UserMixin
from botocore.client import Config
from werkzeug.security import check_password_hash,generate_password_hash
from flask import current_app
from all_classes import Project,Account,Media,SiteMessage,SiteUpdate,Card,Recipe,Version,FormData
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail,Message
import boto3
import requests
import subprocess
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime, timedelta
import io,zipfile
from sqlalchemy import func,text
from all_classes import db
from extensions import mail
from dotenv import load_dotenv
bp = Blueprint('fun', __name__,subdomain="fun")
@bp.route("/forms/get_form", methods=["POST"])
def get_form():
    ad = request.form.get("ad")
    soyad = request.form.get("soyad")
    eposta = request.form.get("eposta")
    parola = request.form.get("parola")
    renk = request.form.get("renk")
    hatirla = request.form.get("hatirla")
    cinsiyet = request.form.get("cin")
    hobiler = request.form.getlist("hobi")
    dogum = request.form.get("dogum")
    ara = request.form.get("ara")
    tarih = request.form.get("date")
    number = request.form.get("number")
    bobrek = request.form.get("bobrek")

    # DB'ye kaydet
    yeni = FormData(
        ad=ad,
        soyad=soyad,
        eposta=eposta,
        parola=parola,
        renk=renk,
        hatirla=bool(hatirla),
        cinsiyet=cinsiyet,
        hobiler=",".join(hobiler),
        dogum=dogum,
        ara=ara,
        tarih=tarih,
        number=number,
        bobrek=bool(bobrek)
    )

    db.session.add(yeni)
    db.session.commit()

    return "Kayıt alındı 😎"
@bp.route("/forms/forms")
def fun_forms():
    dosyalar = FormData.query.all()
    return render_template("fiz.html", dosyalar=dosyalar)
@bp.route("/pushgame")
def gamestart():
        return render_template("pushgame.html")
@bp.route("/pushgame/game", methods=["POST"])
def game():
        return render_template("pushgame_game.html")
@bp.route("/")
def games():
      version=Version.query.get(1)
      return render_template("games.html",version=version.version)
    # ZAMAN YOLCULUĞU BİLİMİ KURTAR
@bp.route("/bilim-oyunu")
def bilim_game():
        return render_template("bilimgame.html")
@bp.route("/dijital_oyku")
def dijital_oyku():
        return render_template("dijital_oyku.html")