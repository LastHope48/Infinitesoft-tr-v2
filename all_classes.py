import os
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from sqlalchemy import text, inspect
from flask import Flask,Blueprint
from flask_login import UserMixin
from datetime import datetime, timedelta
import uuid
db=SQLAlchemy()
app=Flask(__name__)
DATABASE_URL=os.getenv("DATABASE_URL")
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    UPLOAD_PASSWORD=os.getenv("UPLOAD_PASSWORD")
    ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD")
else:
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
if DATABASE_URL:
    class Project(db.Model):
        __tablename__="project_details"
        __table_args__={"schema":"details"}
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(100), nullable=False)
        slug = db.Column(db.String(100), unique=True, nullable=False)
        short_desc = db.Column(db.String(200))
        description = db.Column(db.Text)
        icon=db.Column(db.String(200))
        tech = db.Column(db.String(200))  
        github = db.Column(db.String(200))
        live_url = db.Column(db.String(200))
    class Recipe(db.Model):
        __tablename__="recipes_table"
        __table_args__={"schema":"storage"}
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(150), nullable=False)
        image_url = db.Column(db.String(300))
        desc = db.Column(db.Text)
        ingredients = db.Column(db.Text)
        steps = db.Column(db.Text)
        created_at = db.Column(db.DateTime, server_default=db.func.now())
    class Account(UserMixin,db.Model):
        __tablename__ = "accounts_table"
        __table_args__={"schema":"auth"}
        name = db.Column(db.String(20), nullable=False, unique=True)
        password = db.Column(db.String(300), nullable=False)
        id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    class Card(db.Model):
        __table_args__={"schema":"system"}
        __tablename__="card_table"
        title=db.Column(db.String(100),nullable=False)
        subtitle=db.Column(db.String(100),nullable=False)
        text=db.Column(db.String(600),nullable=False)
        id=db.Column(db.Integer,primary_key=True)
        def __repr__(self):
            return f"<Card {self.id}>"
    class Media(db.Model):
        __tablename__ = "medias_table"
        __table_args__ = {"schema": "storage"}
        id = db.Column(db.Integer, primary_key=True)
        original_name = db.Column(db.String(200))
        stored_name = db.Column(db.String(200))
        r2_key = db.Column(db.String(300))
        size = db.Column(db.BigInteger)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        download_count = db.Column(db.Integer, default=0)
        is_global = db.Column(db.Boolean, default=False)
        high_lighted = db.Column(db.Boolean, default=False)

        owner_id = db.Column(
            db.String(36),
            db.ForeignKey("auth.accounts_table.id", ondelete="CASCADE"),
            nullable=False
        )
    class SiteMessage(db.Model):
        __tablename__ = "sitemessage_table"
        __table_args__ = {"schema": "system"}

        id = db.Column(db.Integer, primary_key=True)
        message = db.Column(db.String(300), nullable=False)
        expires_at = db.Column(db.DateTime, nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

    class SiteUpdate(db.Model):
        __tablename__ = "site_updates"
        __table_args__ = {"schema": "system"}

        id = db.Column(db.Integer, primary_key=True)
        version = db.Column(db.String(20), nullable=False)
        content = db.Column(db.Text, nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
    class Version(db.Model):
        __tablename__="site_version"
        __table_args__={"schema":"system"}
        id=db.Column(db.Integer,nullable=False,primary_key=True)
        version=db.Column(db.String(30),nullable=False)
else:
    class Recipe(db.Model):
        __tablename__="recipes_table"
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(150), nullable=False)
        image_url = db.Column(db.String(300))
        desc = db.Column(db.Text)
        ingredients = db.Column(db.Text)
        steps = db.Column(db.Text)
        created_at = db.Column(db.DateTime, server_default=db.func.now())
    class Account(UserMixin,db.Model):
        __tablename__ = "accounts_table"

        name = db.Column(db.String(20), nullable=False, unique=True)
        password = db.Column(db.String(300), nullable=False)
        id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    class Card(db.Model):
        __tablename__="card_table"
        title=db.Column(db.String(100),nullable=False)
        subtitle=db.Column(db.String(100),nullable=False)
        text=db.Column(db.String(600),nullable=False)
        id=db.Column(db.Integer,primary_key=True)
        def __repr__(self):
            return f"<Card {self.id}>"
    class Media(db.Model):
        __tablename__ = "medias_table"
        id = db.Column(db.Integer, primary_key=True)
        original_name = db.Column(db.String(200))
        stored_name = db.Column(db.String(200))
        r2_key = db.Column(db.String(300))
        size = db.Column(db.BigInteger)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        download_count = db.Column(db.Integer, default=0)
        is_global = db.Column(db.Boolean, default=False)
        high_lighted = db.Column(db.Boolean, default=False)
        owner_id=db.Column(db.String(36),db.ForeignKey('accounts_table.id'))

    class SiteMessage(db.Model):
        __tablename__ = "sitemessage_table"

        id = db.Column(db.Integer, primary_key=True)
        message = db.Column(db.String(300), nullable=False)
        expires_at = db.Column(db.DateTime, nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

    class SiteUpdate(db.Model):
        __tablename__ = "site_updates"

        id = db.Column(db.Integer, primary_key=True)
        version = db.Column(db.String(20), nullable=False)
        content = db.Column(db.Text, nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
    class Project(db.Model):
        __tablename__="project_details"
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(100), nullable=False)
        slug = db.Column(db.String(100), unique=True, nullable=False)
        short_desc = db.Column(db.String(200))
        description = db.Column(db.Text)
        icon=db.Column(db.String(200))
        tech = db.Column(db.String(200))  
        github = db.Column(db.String(200))
        live_url = db.Column(db.String(200))
    class Version(db.Model):
        __tablename__="site_version"
        id=db.Column(db.Integer,nullable=False,primary_key=True)
        version=db.Column(db.String(30),nullable=False)