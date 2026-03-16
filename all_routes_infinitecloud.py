import os
from flask import Flask,render_template,request,send_from_directory,send_file,redirect,session,url_for,Response,abort,jsonify,Blueprint,flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user,UserMixin
from botocore.client import Config
from werkzeug.security import check_password_hash,generate_password_hash
from flask import current_app
from flask_mail import Mail,Message
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
bp = Blueprint('infinitecloud', __name__,subdomain="infinitecloud")
R2_BUCKET="infinitecloud"
MAX_STORAGE = 10 * 1024 * 1024 * 1024
PYANYWHERE_UPLOAD_URL = "https://wf5528.pythonanywhere.com/upload"
ALLOWED={"png","jpg","jpeg","mp4","mov","pdf","webp","mp3","pptx","zip"}
PYANYWHERE_LIST_URL   = "https://wf5528.pythonanywhere.com/list"
PYANYWHERE_SECRET   = os.getenv("PYANYWHERE_SECRET")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "dev-token")  # 'dev-token' lokal için
HF_URL="https://wf5528-infinitesoft-tr.hf.space/remove-bg"
UPLOAD_PASSWORD=os.getenv("UPLOAD_PASSWORD")
ADMIN_PASSWORD_HASH=os.getenv("ADMIN_PASSWORD")
PA_EXE_URL = "https://wf5529.pythonanywhere.com/static/uygulama/infinitesoft-tr.exe"
UPLOAD_FOLDER_GUIDES = "static/uploads"
s3 = boto3.client(
    service_name="s3",
    endpoint_url=f"https://{os.getenv('ACCOUNT_ID')}.r2.cloudflarestorage.com",
    aws_access_key_id=os.getenv("ACCESS_KEY"),
    aws_secret_access_key=os.getenv("SECRET_KEY"),
    region_name="auto"
)
def get_total_files_from_r2():
    # R2 için S3 istemcisi oluşturma
    
    try:
        # Bucket içindeki nesneleri listele
        response = s3.list_objects_v2(Bucket=R2_BUCKET)
        # Eğer bucket boşsa 'Contents' anahtarı olmaz, bu yüzden 0 döneriz
        return response.get('KeyCount', 0)
    except Exception as e:
        print(f"Hata oluştu: {e}")
        return 0
def allowed(filename):
    return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED

def send_to_pythonanywhere(filename, file_bytes):
    try:
        r = requests.post(
            PYANYWHERE_UPLOAD_URL,
            files={"file": (filename, file_bytes)},
            headers={"X-SECRET": PYANYWHERE_SECRET},
            timeout=10
        )
        print("STATUS:", r.status_code)
        print("TEXT:", r.text)
    except Exception as e:
        print("ERR:", e)
@bp.route("/")
@login_required
def cloud():
    print("CLOUD PAGE CALLED")
    total_files = get_total_files_from_r2()
    return render_template("home_cloud.html", total_files=total_files,active_page="cloud")
@bp.route("/upload", methods=["GET","POST"],subdomain="infinitecloud")
@login_required
def upload():
        can_delete=session.get("can_delete")
        if request.method=="POST":
            if UPLOAD_PASSWORD != request.form.get("password"):
                return jsonify(success=False, message="❌ Şifre yanlış")

            file = request.files.get("file")
            if not file or not allowed(file.filename) and session.get("can_delete") is not True:
                return jsonify(success=False, message="❌ Geçersiz dosya")

            original_name = secure_filename(file.filename)
            ext = original_name.rsplit(".", 1)[1].lower()
            exists = Media.query.filter_by(original_name=original_name).first()
            stored_name = f"{uuid.uuid4()}.{ext}" if exists else original_name

            is_global = "is_global" in request.form
            high_lighted = bool(request.form.get("high_lighted"))
            print("UPLOAD API CALLED")
            print("FILES:", request.files)
            print("FORM:", request.form)

            if "uploader_id" not in session:
                session["uploader_id"] = str(uuid.uuid4())

            file_bytes = file.read()
            file_size = len(file_bytes)

            # mevcut kullanım
            current_usage = db.session.query(
                func.coalesce(func.sum(Media.size), 0)
            ).scalar()

            if current_usage + file_size > MAX_STORAGE:
                return jsonify(
                    success=False,
                    message="❌ Üzgünüz, 10GB kota doldu."
                )
            else:
                r2_key = f"{uuid.uuid4()}_{stored_name}"

                try:
                    s3.put_object(
                        Bucket=R2_BUCKET,
                        Key=r2_key,
                        Body=file_bytes
                    )
                except Exception as e:
                    print("R2 UPLOAD HATA:", e)
                    return jsonify(success=False, message="R2 upload hatası")
            media = Media(
                original_name=original_name,
                stored_name=stored_name,
                r2_key=r2_key,
                size=file_size,
                is_global=is_global,
                high_lighted=high_lighted,
                owner_id=current_user.id   # 🔥 burası değişti
            )

            db.session.add(media)
            db.session.commit()
            send_to_pythonanywhere(original_name, file_bytes)
            print("UPLOAD OK:", original_name)
            return jsonify(success=True, message="✅ Dosya yüklendi")

        return render_template("upload.html",can_delete=can_delete,active_page="upload")


@bp.route("/files/<int:media_id>/download",subdomain="infinitecloud")
@login_required
def download_file(media_id):
        media = Media.query.get_or_404(media_id)

        if not media.is_global:
            if session.get("can_delete") is not True and media.owner_session != session.get("uploader_id"):
                return "❌ Bu dosya gizli", 403

        media.download_count += 1
        db.session.commit()

        obj = s3.get_object(
            Bucket=R2_BUCKET,
            Key=media.r2_key
        )

        return Response(
            obj["Body"].read(),
            headers={
                "Content-Disposition": f'attachment; filename="{media.original_name}"',
                "Content-Type": "application/octet-stream"
            }
        )

@bp.route("/files/<int:media_id>",subdomain="infinitecloud")
def look(media_id):
        media = Media.query.get_or_404(media_id)

        if not media.is_global:
            if session.get("can_delete") is not True and media.owner_id != current_user.id:
                abort(403)

        obj = s3.get_object(
            Bucket=R2_BUCKET,
            Key=media.r2_key
        )

        return Response(
            obj["Body"].read(),
            headers={
                "Content-Type": "application/octet-stream"
            }
        )

@bp.route("/delete/<int:file_id>", methods=["POST"],subdomain="infinitecloud")
@login_required
def delete_file(file_id):
        media = Media.query.get_or_404(file_id)

        if media.owner_id != current_user.id and not session.get("can_delete"):
            abort(403)

        # R2’den sil
        response = s3.delete_object(
            Bucket=R2_BUCKET,
            Key=media.r2_key
        )


        # DB’den sil
        db.session.delete(media)
        db.session.commit()
        print("SİLİNEN KEY:", media.r2_key)
        print("DELETE RESPONSE:", response)
        return redirect(url_for("infinitecloud.files"))
@bp.route("/logout",subdomain="infinitecloud")
@login_required
def logout_ic():
        logout_user()
        return redirect(url_for("infinitecloud.login_ic"))
@bp.route("/login", methods=["GET", "POST"], subdomain="infinitecloud")
def login_ic():
    if request.method == "POST":
        name = request.form.get("username")
        password = request.form.get("password")

        user = Account.query.filter_by(name=name).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get("next")
            redirect_url = next_page if next_page else url_for("infinitecloud.cloud")
            return jsonify({"success": True, "redirect": redirect_url})

        return jsonify({"success": False, "message": "Kullanıcı adı veya şifre yanlış"})

    return render_template("login_ic.html")
@bp.route("/register", methods=["GET", "POST"],subdomain="infinitecloud")
def register_ic():
        if request.method == "POST":
            name = request.form.get("username")
            password = request.form.get("password")

            # Kullanıcı var mı kontrol
            existing = Account.query.filter_by(name=name).first()
            if existing:
                return "Bu kullanıcı adı zaten var"

            new_user = Account(
                id=str(uuid.uuid4()),
                name=name,
                password=generate_password_hash(password)
            )

            db.session.add(new_user)
            db.session.commit()

            return redirect(url_for("infinitecloud.login_ic"))

        return render_template("register_ic.html")
@bp.route("/reset", methods=["POST"],subdomain="infinitecloud")
def reset_files():
        if not session.get("can_reset"):
            abort(403)
        try:
            print("BEFORE DELETE COUNT:",
                s3.list_objects_v2(Bucket=R2_BUCKET).get("KeyCount"))
            continuation_token = None

            while True:
                if continuation_token:
                    objects = s3.list_objects_v2(
                        Bucket=R2_BUCKET,
                        ContinuationToken=continuation_token
                    )
                else:
                    objects = s3.list_objects_v2(Bucket=R2_BUCKET)

                if "Contents" in objects:

                    s3.delete_objects(
                        Bucket=R2_BUCKET,
                        Delete={
                            "Objects": [
                                {"Key": obj["Key"]} for obj in objects["Contents"]
                            ]
                        }
                    )

                if objects.get("IsTruncated"):
                    continuation_token = objects.get("NextContinuationToken")
                else:
                    break
            medias = Media.query.all()
            for media in medias:

                db.session.delete(media)

            db.session.commit()

            print("AFTER DELETE COUNT:",
                s3.list_objects_v2(Bucket=R2_BUCKET).get("KeyCount"))
            return redirect(url_for("infinitecloud.files"))
        except Exception as e:
            print(f"ERROR DELETE ALL: {e}")
            return "Bir hata oluştu"
@bp.route("/files",subdomain="infinitecloud")
@login_required
def files():
        if "uploader_id" not in session:
            session["uploader_id"] = str(uuid.uuid4())
        uploader_id = session.get("uploader_id")
        is_admin = session.get("can_delete", False)

        try:
            if is_admin:
                medias = Media.query.all()
            else:
                medias = Media.query.filter(Media.is_global == True).all()
        except Exception as e:
            print("DB HATA:", e)
            return "DB hatası oluştu", 500

        files_count = len(medias)
        pa_files = []

        try:
            r = requests.get(PYANYWHERE_LIST_URL, headers={"X-SECRET": PYANYWHERE_SECRET}, timeout=5)
            if r.status_code == 200:
                pa_files = r.json().get("files", [])
        except Exception as e:
            print("PA LIST HATA:", e)

        return render_template(
            "files.html",
            files=medias,
            files_count=files_count,
            can_reset=session.get("can_reset", False),
            can_delete=is_admin,
            pa_files=pa_files,
            active_page="files"
        )


@bp.route("/files/download_all",subdomain="infinitecloud")
@login_required
def download_all():
        medias = Media.query.all()
        if not medias:
            return "Hiç dosya yok."

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for media in medias:
                obj = s3.get_object(
                Bucket=R2_BUCKET,
                Key=media.r2_key
            )

                zip_file.writestr(media.original_name, obj["Body"].read())

        zip_buffer.seek(0)

        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name="all_files.zip",
            mimetype="application/zip"
        )
@bp.route("/myfiles",subdomain="infinitecloud")
@login_required
def myfiles():
        
        uploader_id = session["uploader_id"]
        # Veritabanından dosyaları çekiyoruz

        medias = Media.query.filter_by(owner_id=current_user.id)\
                            .order_by(Media.created_at.desc())\
                            .all()
        
        # EĞER DOSYA YOKSA: Hata mesajı döndürmek yerine, 
        # boş liste ile HTML şablonuna (template) gönderiyoruz.
        # HTML içindeki {% else %} bloğu devreye girecek.
        return render_template(
            "myfiles.html",
            files=medias,
            files_count=len(medias),
            can_reset=False,
            active_page="myfiles" # Veya senin yetki kontrolün
        )
@bp.route("/myfiles/<int:media_id>/delete",subdomain="infinitecloud")
@login_required
def delete_myfile(media_id):
        media=Media.query.get_or_404(media_id)
        if session.get("can_delete") is not True and media.owner_session != session.get("uploader_id"):
            abort(403)
        response = s3.delete_object(
            Bucket=R2_BUCKET,
            Key=media.r2_key
            )
        print(response)
        db.session.delete(media)
        db.session.commit()
        return redirect(url_for("infinitecloud.myfiles"))
@bp.route("/lookmy/<int:file_id>",subdomain="infinitecloud")
@login_required
def lookmy(file_id):
        media = Media.query.get_or_404(file_id)

        if media.owner_session != session.get("uploader_id"):
            abort(403)

        obj = s3.get_object(
            Bucket=R2_BUCKET,
            Key=media.r2_key
        )

        return Response(
            obj["Body"].read(),
            mimetype=media.mimetype
        )
@bp.route("/download/<int:file_id>",subdomain="infinitecloud")
@login_required
def download(file_id):
        media = Media.query.get_or_404(file_id)

        if media.owner_session != session.get("uploader_id"):
            abort(403)

        obj = s3.get_object(
            Bucket=R2_BUCKET,
            Key=media.r2_key
        )

        return Response(
            obj["Body"].read(),
            headers={
                "Content-Disposition": f'attachment; filename="{media.original_name}"'
            },
            mimetype=media.mimetype
        )
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