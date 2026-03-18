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
bp = Blueprint('app', __name__)
R2_BUCKET="infinitecloud"
MAIL_PASSWORD=os.getenv("MAIL_PASSWORD")
DATABASE_URL=os.getenv("DATABASE_URL")
MAX_STORAGE = 10 * 1024 * 1024 * 1024
PYANYWHERE_UPLOAD_URL = "https://wf5528.pythonanywhere.com/upload"
ALLOWED={"png","jpg","jpeg","mp4","mov","pdf","webp","mp3","pptx","zip"}
PYANYWHERE_LIST_URL   = "https://wf5528.pythonanywhere.com/list"
PYANYWHERE_SECRET   = os.getenv("PYANYWHERE_SECRET")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "dev-token")  # 'dev-token' lokal için
HF_URL="https://wf5528-infinitesoft-tr.hf.space/remove-bg"
PA_EXE_URL = "https://wf5529.pythonanywhere.com/static/uygulama/infinitesoft-tr.exe"
UPLOAD_FOLDER_GUIDES = "static/uploads"
if os.getenv("DATABASE_URL"):
    ADMIN_PASSWORD_HASH=os.getenv("ADMIN_PASSWORD")
else:
    ADMIN_PASSWORD_HASH="admin"
try:
    SUBDOMAIN = os.getenv("SUBDOMAIN")
except:
    print("Bulunamadı")
def allowed(filename):
    return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED

@bp.route("/projects/<slug>")
def project_detail(slug):
        project = Project.query.filter_by(slug=slug).first_or_404()
        return render_template("project_detail.html", project=project)


@bp.route("/")
def projects():
        version=Version.query.get(1)
        try:
            if not version.version!=None:
                return render_template("projects.html")
        except:
            return render_template("projects.html")
        return render_template("projects.html",version=version.version)


@bp.route("/__reset_db__", methods=["GET"])
def reset_db():
        if not session.get("can_delete"):
            abort(403)
        try:
            db.drop_all()
            db.create_all()

            return redirect(url_for("app.projects"))
        except:
            abort(403)
@bp.route("/admin", methods=["GET", "POST"])
def reset_login():
        msg = ""
        if request.method == "POST":
            if ADMIN_PASSWORD_HASH==request.form["password"]:
                session["can_reset"] = True
                session["can_delete"]=True
                return redirect("/")
            else:
                msg = "❌ Admin şifre yanlış"
        return render_template("reset_login.html", msg=msg)

    # Sistemler
@bp.route('/sitemap.xml', methods=['GET'])
def sitemap():
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://www.infinitesoft-tr.com/</loc>
    </url>
    </urlset>
    """
        return Response(sitemap_xml, mimetype='application/xml')
@bp.route("/admin/broadcast", methods=["POST"])
def admin_broadcast():
        if not session.get("can_delete"):
            abort(403)

        msg = request.form["message"]
        minutes = int(request.form.get("minutes", 5))

        expires = datetime.utcnow() + timedelta(minutes=minutes)

        site_msg = SiteMessage(
            message=msg,
            expires_at=expires
        )

        db.session.add(site_msg)
        db.session.commit()

        return redirect(url_for("app.broadcast_panel"))
@bp.route("/admins")
def admin_panel():
        # ... (yetki kontrolleri)
        
        used_bytes = db.session.query(func.sum(Media.size)).scalar() or 0
        total_bytes = 10 * (1024 ** 3)
        
        # Yüzdeyi hesapla (Hala 0 görünebilir çünkü %0.001 gibi bir rakamdır)
        percent = (used_bytes / total_bytes) * 100
        
        # Birim dönüştürme mantığı
        if used_bytes < 1024:
            display_usage = f"{used_bytes} Byte"
        elif used_bytes < 1024**2:
            display_usage = f"{round(used_bytes/1024, 2)} KB"
        elif used_bytes < 1024**3:
            display_usage = f"{round(used_bytes/(1024**2), 2)} MB"
        else:
            display_usage = f"{round(used_bytes/(1024**3), 2)} GB"

        return render_template(
            "admins.html",
            display_usage=display_usage, # HTML'de bunu kullanacağız
            percent=round(percent, 2),
            bar_class="safe" if percent < 60 else "warning"
        )
@bp.context_processor
def inject_broadcast():
        try:
            now = datetime.utcnow()
            # Sadece aktif mesajı çek, silme işlemini buradan kaldır!
            active = SiteMessage.query.filter(
                SiteMessage.expires_at > now
            ).order_by(SiteMessage.created_at.desc()).first()

            return {
                "broadcast_message": active.message if active else None
            }
        except Exception as e:
            print(f"Broadcast hatası (yoksayıldı): {e}")
            return {"broadcast_message": None}
@bp.route("/news")
def news():
        updates = SiteUpdate.query.order_by(
            SiteUpdate.created_at.desc()
        ).all()
        return render_template("last_updates.html", updates=updates)

@bp.route("/admin/news", methods=["GET", "POST"])
def admin_news():
        if not session.get("can_delete"):
            abort(403)

        if request.method == "POST":
            version = request.form["version"]
            content = request.form["content"]

            update = SiteUpdate(
                version=version,
                content=content
            )

            db.session.add(update)
            db.session.commit()

            return redirect(url_for("app.news"))

        return render_template("make_update.html")
    # UYGULAMAMIZ
@bp.route("/indir")
def uygulama():
        return render_template("indir.html")
@bp.route("/infinitesoft-tr.exe")
def indir():
        r = requests.get(PA_EXE_URL, stream=True)
        if r.status_code != 200:
            return "Dosya bulunamadı"
        
        return Response(
            r.iter_content(chunk_size=8192),
            headers={
                "Content-Disposition": 'attachment; filename="infinitesoft-tr.exe"'
            },
            mimetype="application/octet-stream"
        )
@bp.route("/api/delete/<filename>")
def api_delete(filename):
        token = request.headers.get("X-SECRET")
        if token != os.environ.get("ADMIN_TOKEN"):
            return jsonify({"ok": False, "error": "Yetki yok"}), 403

        # dosya silme işlemi
        try:
            os.remove(os.path.join("uploads", filename))
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
@bp.route("/text_editor")
def editor():
        return render_template("text_editor.html")
    # GUIDES
    
    # MEKAPUS
@bp.route("/mekapus")
def home_mekapus():
        return render_template("mekapus.html")
    # DİJİTAL OYKU | EN GÜÇLÜ KULE
@bp.route("/admin/update-version")
def update_version():
        if not session.get("can_delete"):
            abort(403)
        version=Version.query.get(1)
        try:
            if not version.version!=None:
                return render_template("update_version.html")
        except:
            return render_template("update_version.html")
        return render_template("update_version.html",version=version.version)
@bp.route("/admin/update-version/version",methods=["POST"])
def version_data():
        if not session.get("can_delete"):
            abort(403)
        Version.query.delete()
        v1=request.form["v1"]
        v2=request.form["v2"]
        v3=request.form["v3"]
        v=Version(
            id=1,
            version=f"{v1}.{v2}.{v3}"
        )
        db.session.add(v)
        db.session.commit()
        return redirect(url_for("app.projects"))
@bp.route("/admin/broadcast-panel")
def broadcast_panel():
        if not session.get("can_delete"):
            return "Yetkisiz", 403
        return render_template("admin_broadcast.html")
@bp.route("/admin/backup-db")
def backup_db():
    if not session.get("can_delete"):
        abort(403)  # Yetkisiz kullanıcı
    
    # Dosya ismini tarih ile oluştur
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup_{now}.sql"
    if not DATABASE_URL:
        return "DATABASE_URL bulunamadı", 500
    # PostgreSQL backup komutu
    # Çevre değişkenlerinde DB bilgilerini tanımlamalısın: PGUSER, PGPASSWORD, PGHOST, PGDATABASE
    try:
        subprocess.run([
            "pg_dump",
            DATABASE_URL,
            "-Fc",
            "-f", backup_file
        ], check=True)
    except subprocess.CalledProcessError as e:
        return f"Backup alınamadı: {e}", 500

    # Dosyayı gönder ve sunucuda sil
    response = send_file(backup_file, as_attachment=True)
    response.call_on_close(lambda: os.remove(backup_file))
    return response
@bp.route("/privacy")
def privacy():
    return render_template("privacy.html")

@bp.route("/terms")
def terms():
    return render_template("terms.html")
@bp.route('/admin/send-email', methods=['GET', 'POST'])
def admin_send_email():
    # Sadece admin yetkisi kontrolü burada olmalı
    if request.method == 'POST':
        subject = request.form.get('subject')
        body = request.form.get('body')
        recipient = request.form.get('recipient')

        msg = Message(subject, sender=current_app.config['MAIL_USERNAME'], recipients=[recipient])
        msg.body = body
        mail.send(msg)

        flash("E-posta gönderildi!")
        return redirect(url_for('admin_send_email'))

    return render_template('admin_send_email.html')
@bp.route("/test-mail")
def test_mail():
    msg = Message(
        subject="InfiniteCloud Test",
        sender=current_app.config['MAIL_USERNAME'],
        recipients=["erenmehmetserdar87@gmail.com"]
    )
    msg.body = "Mail sistemi çalışıyor 🚀"
    
    mail.send(msg)
    return "Mail gönderildi!"