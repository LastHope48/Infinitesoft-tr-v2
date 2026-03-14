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
bp = Blueprint('app', __name__)
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
with current_app.app_context():
    s3 = boto3.client(
        service_name="s3",
        endpoint_url=f"https://{os.getenv('ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv("ACCESS_KEY"),
        aws_secret_access_key=os.getenv("SECRET_KEY"),
        region_name="auto"
    )
try:
    SUBDOMAIN = os.getenv("SUBDOMAIN")
except:
    print("Bulunamadı")
if SUBDOMAIN:
    UPLOAD_PASSWORD=os.getenv("UPLOAD_PASSWORD")
    ADMIN_PASSWORD_HASH=os.getenv("ADMIN_PASSWORD")
    @bp.route("/projects/<slug>",subdomain=None)
    def project_detail(slug):
        project = Project.query.filter_by(slug=slug).first_or_404()
        return render_template("project_detail.html", project=project)


    @bp.route("/",subdomain=None)
    def projects():
        version=Version.query.get(1)
        try:
            if not version.version!=None:
                return render_template("projects.html")
        except:
            return render_template("projects.html")
        return render_template("projects.html",version=version.version)

    @bp.route("/",subdomain="infinitecloud")
    @login_required
    def cloud():
        total_files=get_total_files_from_r2()
        return render_template("home_cloud.html",total_files=total_files)
    @bp.route("/__reset_db__", methods=["GET"],subdomain=None)
    def reset_db():
        if not session.get("can_delete"):
            abort(403)
        try:
            db.drop_all()
            db.create_all()

            return redirect(url_for("app.projects"))
        except:
            abort(403)
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
        return redirect(url_for("app.home_shop"))
    @bp.route("/sepet_sil", methods=["POST"],subdomain="camsepeti")
    @login_required
    def sepet_sil():
        index = int(request.form["index"])

        sepet = session.get("sepet", [])

        if 0 <= index < len(sepet):
            sepet.pop(index)
            session["sepet"] = sepet

        return redirect(url_for("app.sepet"))
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

            return redirect(url_for("app.login"))
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

                return redirect(url_for("home_shop"))
            else:
                return "Hatalı giriş❌"
        return render_template("login.html")
    @bp.route("/logout",subdomain="camsepeti")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("app.login"))
    @bp.route("/create_db")
    def create_db():
        if not session.get("can_delete"):
            abort(403)
        db.create_all()
        return redirect(url_for("app.projects"))
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

        return render_template("upload.html",can_delete=can_delete)


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
        return redirect(url_for("app.files"))
    @bp.route("/admin", methods=["GET", "POST"],subdomain=None)
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
    @bp.route("/logout",subdomain="infinitecloud")
    @login_required
    def logout_ic():
        logout_user()
        return redirect(url_for("app.login_ic"))
    @bp.route("/login", methods=["GET", "POST"],subdomain="infinitecloud")
    def login_ic():
        if request.method == "POST":
            name = request.form.get("username")
            password = request.form.get("password")

            user = Account.query.filter_by(name=name).first()

            if user and check_password_hash(user.password, password):
                login_user(user)
                next_page = request.args.get("next")

                if next_page:
                    return redirect(next_page)

                return redirect(url_for("app.cloud"))  # varsayılan

            return "Kullanıcı adı veya şifre yanlış"

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

            return redirect(url_for("app.login_ic"))

        return render_template("register_ic.html")
    @bp.route("/reset", methods=["POST"],subdomain="infinitecloud")
    def reset_files():
        if not session.get("can_reset"):
            return redirect("/infinitecloud/reset-login")
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
            return redirect("/infinitecloud/files")
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
            pa_files=pa_files
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
    @bp.route("/infinitecloud/files/pa/download/<filename>")
    def pa_download(filename):
        r = requests.get(
            f"https://wf5528.pythonanywhere.com/download/{filename}",
            headers={"X-SECRET": PYANYWHERE_SECRET},
            stream=True
        )

        if r.status_code != 200:
            return "PA download failed", 404

        return Response(
            r.content,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    @bp.route("/infinitecloud/pa/delete/<filename>", methods=["POST"])
    def pa_delete(filename):
        r = requests.post(
            f"https://wf5528.pythonanywhere.com/delete/{filename}",
            headers={"X-SECRET": PYANYWHERE_SECRET},
            timeout=5
        )

        if r.status_code == 200:
            return redirect("/infinitecloud/files")
        return "Silinemedi", 400
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
    @bp.route("/admins",subdomain=None)
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

    @bp.route("/admin/broadcast-panel",subdomain=None)
    def broadcast_panel():
        if not session.get("can_delete"):
            return "Yetkisiz", 403
        return render_template("admin_broadcast.html")
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
            can_reset=False # Veya senin yetki kontrolün
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
        return redirect(url_for("app.myfiles"))
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
    # PUSH GAME
    @bp.route("/",subdomain="pushgame")
    def gamestart():
        return render_template("pushgame.html")
    @bp.route("/game", methods=["POST"],subdomain="pushgame")
    def game():
        return render_template("pushgame_game.html")
    # YENİLİKLER
    @bp.route("/news",subdomain=None)
    def news():
        updates = SiteUpdate.query.order_by(
            SiteUpdate.created_at.desc()
        ).all()
        return render_template("last_updates.html", updates=updates)

    @bp.route("/admin/news", methods=["GET", "POST"],subdomain=None)
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
    @bp.route("/indir",subdomain=None)
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

    # AI_TOOLS
    @bp.route("/",subdomain="aitools")
    def tools():
        return render_template("ai_tools.html")
    @bp.route("/images",subdomain="aitools")
    def images():
        return render_template("images.html")
    @bp.route("/api/delete/<filename>",subdomain=None)
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
    @bp.route("/backdeleter",methods=["GET","POST"],subdomain="aitools")
    def back_delete():
        return render_template("background_remover.html")
    @bp.route("/backdeleter/remove", methods=["POST"],subdomain="aitools")
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

    # KART
    @bp.route('/',subdomain="cards")
    def index():
        cards=Card.query.order_by(Card.id).all()

        return render_template('index.html',
                            #kartlar = kartlar
                                cards=cards,
                            )
    @bp.route('/card/<int:id>',subdomain="cards")
    def card(id):
        # Görev #2. Id'ye göre doğru kartı görüntüleme
        card=Card.query.get(id)

        return render_template('card.html', card=card)
    @bp.route('/create',subdomain="cards")
    def create():
        return render_template('create_card.html')
    @bp.route('/form_create', methods=['GET','POST'],subdomain="cards")
    def form_create():
        if request.method == 'POST':
            title =  request.form['title']
            subtitle =  request.form['subtitle']
            text =  request.form['text']

            # Görev #2. Verileri DB'de depolamak için bir yol oluşturma
            card=Card(title=title,subtitle=subtitle,text=text)
            db.session.add(card)
            db.session.commit()
            return redirect(url_for("app.index"))
        else:
            return render_template('create_card.html')
    # TEXT EDITOR
    @bp.route("/text_editor",subdomain=None)
    def editor():
        return render_template("text_editor.html")
    # GUIDES
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
        return redirect(url_for("app.guides_home"))


    @bp.route("/add", methods=["GET","POST"],subdomain="guides")
    def add():
        if request.method == "POST":
            file = request.files["image"]
            filename = secure_filename(file.filename)

            # Klasör yoksa oluştur
            upload_folder = current_app.config["UPLOAD_FOLDER_GUIDES"]
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            path = os.path.join(upload_folder, filename)
            file.save(path)

            # image_url başına / koyarak tarayıcıya doğru yol ver
            r = Recipe(
                title=request.form["title"],
                image_url="/static/uploads/" + filename,
                desc=request.form["desc"],
                ingredients=request.form["ingredients"],
                steps=request.form["steps"]
            )
            db.session.add(r)
            db.session.commit()
            return redirect(url_for("app.guides_home"))

        return render_template("add_guide.html")

    # ZAMAN YOLCULUĞU BİLİMİ KURTAR
    @bp.route("/bilim-oyunu",subdomain=None)
    def bilim_game():
        return render_template("bilimgame.html")
    # MEKAPUS
    @bp.route("/mekapus",subdomain=None)
    def home_mekapus():
        return render_template("mekapus.html")
    # DİJİTAL OYKU | EN GÜÇLÜ KULE
    @bp.route("/dijital_oyku",subdomain=None)
    def dijital_oyku():
        return render_template("dijital_oyku.html")
    @bp.route("/admin/update-version",subdomain=None, endpoint="bp_update_version")
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
    @bp.route("/admin/update-version/version",methods=["POST"],subdomain=None)
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
    # HATALAR
    @bp.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"),404
    @bp.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"),403
    @bp.errorhandler(405)
    def wrong_direction_to_come(e):
        return render_template("405.html"),405
    @bp.errorhandler(500)
    def internal_error(e):
        return render_template("500.html"), 500

else:
    UPLOAD_PASSWORD="yukle"
    ADMIN_PASSWORD_HASH="admin"
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
    @bp.route("/infinitecloud")
    @login_required
    def cloud():
        total_files=get_total_files_from_r2()
        return render_template("home_cloud.html",total_files=total_files)
    @bp.route("/__reset_db__", methods=["GET"])
    def reset_db():

        if not session.get("can_delete"):
            abort(403)

        db.drop_all()
        db.create_all()

        return "DB sıfırlandı ✅"

    @bp.route("/camsepeti/home")
    @login_required
    def home_shop():
        return render_template("home.html")
    @bp.route("/camsepeti/sepete_ekle",methods=["POST"])
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
        return redirect("/camsepeti/home")
    @bp.route("/camsepeti/sepet_sil", methods=["POST"])
    @login_required
    def sepet_sil():
        index = int(request.form["index"])

        sepet = session.get("sepet", [])

        if 0 <= index < len(sepet):
            sepet.pop(index)
            session["sepet"] = sepet

        return redirect("/camsepeti/sepet")
    @bp.route("/camsepeti/buy_success",methods=["POST"])
    @login_required
    def buy_success():
        return render_template("buy_success.html")
    @bp.route("/camsepeti/sepet")
    @login_required
    def sepet():
        return render_template("sepet.html",sepet=session.get("sepet"))
    @bp.route("/camsepeti/buy")
    @login_required
    def buy():
        return render_template("buy.html")

    @bp.route("/camsepeti/register",methods=["GET","POST"])
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

            return redirect("/camsepeti")
        return render_template("register.html")

    @bp.route("/camsepeti",methods=["GET","POST"])
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

                return redirect(url_for("app.home_shop"))
            else:
                return "Hatalı giriş❌"
        return render_template("login.html")
    @bp.route("/camsepeti/logout")
    @login_required
    def logout():
        logout_user()
        return redirect("/camsepeti")
    @bp.route("/create_db")
    def create_db():
        if not session.get("can_delete"):
            abort(403)
        db.create_all()
        return redirect("/")
    @bp.route("/infinitecloud/upload", methods=["GET","POST"])
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

        return render_template("upload.html",can_delete=can_delete)


    @bp.route("/infinitecloud/files/<int:media_id>/download")
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

    @bp.route("/infinitecloud/files/<int:media_id>")
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

    @bp.route("/infinitecloud/delete/<int:file_id>", methods=["POST"])
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
        return redirect(url_for("app.files"))
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
    @bp.route("/infinitecloud/logout")
    @login_required
    def logout_ic():
        logout_user()
        return redirect(url_for("app.login_ic"))
    @bp.route("/infinitecloud/login", methods=["GET", "POST"])
    def login_ic():
        if request.method == "POST":
            name = request.form.get("username")
            password = request.form.get("password")

            user = Account.query.filter_by(name=name).first()

            if user and check_password_hash(user.password, password):
                login_user(user)
                next_page = request.args.get("next")

                if next_page:
                    return redirect(next_page)

                return redirect(url_for("app.cloud"))  # varsayılan

            return "Kullanıcı adı veya şifre yanlış"

        return render_template("login_ic.html")
    @bp.route("/infinitecloud/register", methods=["GET", "POST"])
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

            return redirect("/infinitecloud/login")

        return render_template("register_ic.html")
    @bp.route("/infinitecloud/reset", methods=["POST"])
    def reset_files():
        if not session.get("can_reset"):
            return redirect("/infinitecloud/reset-login")
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
            return redirect("/infinitecloud/files")
        except Exception as e:
            print(f"ERROR DELETE ALL: {e}")
            return "Bir hata oluştu"
    @bp.route("/infinitecloud/files")
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
            pa_files=pa_files
        )


    @bp.route("/infinitecloud/files/download_all")
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
    @bp.route("/infinitecloud/files/pa/download/<filename>")
    def pa_download(filename):
        r = requests.get(
            f"https://wf5528.pythonanywhere.com/download/{filename}",
            headers={"X-SECRET": PYANYWHERE_SECRET},
            stream=True
        )

        if r.status_code != 200:
            return "PA download failed", 404

        return Response(
            r.content,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    @bp.route("/infinitecloud/pa/delete/<filename>", methods=["POST"])
    def pa_delete(filename):
        r = requests.post(
            f"https://wf5528.pythonanywhere.com/delete/{filename}",
            headers={"X-SECRET": PYANYWHERE_SECRET},
            timeout=5
        )

        if r.status_code == 200:
            return redirect("/infinitecloud/files")
        return "Silinemedi", 400
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

        return redirect("/admin/broadcast-panel")
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

    @bp.route("/admin/broadcast-panel")
    def broadcast_panel():
        if not session.get("can_delete"):
            return "Yetkisiz", 403
        return render_template("admin_broadcast.html")
    @bp.route("/infinitecloud/myfiles")
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
            can_reset=False # Veya senin yetki kontrolün
        )
    @bp.route("/infinitecloud/myfiles/<int:media_id>/delete")
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
        return redirect("/infinitecloud/myfiles")
    @bp.route("/infinitecloud/lookmy/<int:file_id>")
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
    @bp.route("/infinitecloud/download/<int:file_id>")
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
    # PUSH GAME
    @bp.route("/pushgame")
    def gamestart():
        return render_template("pushgame.html")
    @bp.route("/pushgame/game", methods=["POST"])
    def game():
        return render_template("pushgame_game.html")
    # YENİLİKLER
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

            return redirect("/news")

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

    # AI_TOOLS
    @bp.route("/ai_tools")
    def tools():
        return render_template("ai_tools.html")
    @bp.route("/ai_tools/images")
    def images():
        return render_template("images.html")
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
    @bp.route("/ai_tools/backdeleter",methods=["GET","POST"])
    def back_delete():
        return render_template("background_remover.html")
    @bp.route("/ai_tools/backdeleter/remove", methods=["POST"])
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

    # KART
    @bp.route('/cards')
    def index():
        cards=Card.query.order_by(Card.id).all()

        return render_template('index.html',
                            #kartlar = kartlar
                                cards=cards,
                            )
    @bp.route('/cards/card/<int:id>')
    def card(id):
        # Görev #2. Id'ye göre doğru kartı görüntüleme
        card=Card.query.get(id)

        return render_template('card.html', card=card)
    @bp.route('/cards/create')
    def create():
        return render_template('create_card.html')
    @bp.route('/cards/form_create', methods=['GET','POST'])
    def form_create():
        if request.method == 'POST':
            title =  request.form['title']
            subtitle =  request.form['subtitle']
            text =  request.form['text']

            # Görev #2. Verileri DB'de depolamak için bir yol oluşturma
            card=Card(title=title,subtitle=subtitle,text=text)
            db.session.add(card)
            db.session.commit()
            return redirect('/cards')
        else:
            return render_template('create_card.html')
    # TEXT EDITOR
    @bp.route("/text_editor")
    def editor():
        return render_template("text_editor.html")
    # GUIDES
    @bp.route("/guides")
    def guides_home():
        recipes=Recipe.query.all()
        return render_template("guides.html",recipes=recipes)
    @bp.route("/recipes/<int:id>")
    def recipe_detail(id):
        recipe = Recipe.query.get_or_404(id)
        return render_template("recipe.html", recipe=recipe)
    @bp.route("/recipes/<int:id>/delete", methods=["POST"])
    def delete_recipe(id):
        if not session.get("can_delete"):
            abort(403)
        
        recipe = Recipe.query.get_or_404(id)
        db.session.delete(recipe)
        db.session.commit()
        return redirect("/guides")


    @bp.route("/guides/add", methods=["GET","POST"])
    def add():
        if request.method == "POST":
            file = request.files["image"]
            filename = secure_filename(file.filename)

            # Klasör yoksa oluştur
            upload_folder = current_app.config["UPLOAD_FOLDER_GUIDES"]
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            path = os.path.join(upload_folder, filename)
            file.save(path)

            # image_url başına / koyarak tarayıcıya doğru yol ver
            r = Recipe(
                title=request.form["title"],
                image_url="/static/uploads/" + filename,
                desc=request.form["desc"],
                ingredients=request.form["ingredients"],
                steps=request.form["steps"]
            )
            db.session.add(r)
            db.session.commit()
            return redirect("/guides")

        return render_template("add_guide.html")
    @bp.route("/admin/update-version")
    def update_version_not_sub():
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
    # ZAMAN YOLCULUĞU BİLİMİ KURTAR
    @bp.route("/bilim-oyunu")
    def bilim_game():
        return render_template("bilimgame.html")
    # MEKAPUS
    @bp.route("/mekapus")
    def home_mekapus():
        return render_template("mekapus.html")
    # DİJİTAL OYKU | EN GÜÇLÜ KULE
    @bp.route("/dijital_oyku")
    def dijital_oyku():
        return render_template("dijital_oyku.html")
    # HATALAR
    @bp.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"),404
    @bp.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"),403
    @bp.errorhandler(405)
    def wrong_direction_to_come(e):
        return render_template("405.html"),405
    @bp.errorhandler(500)
    def internal_error(e):
        return render_template("500.html"), 500
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
def get_total_files_from_r2():
    # R2 için S3 istemcisi oluşturma
    s3 = boto3.client(
        service_name='s3',
        endpoint_url=f'https://{os.getenv("ACCOUNT_ID")}.r2.cloudflarestorage.com',
        aws_access_key_id=os.getenv("ACCESS_KEY"),
        aws_secret_access_key=os.getenv("SECRET_KEY"),
        config=Config(signature_version='s3v4'),
        region_name='auto' # Cloudflare R2 için 'auto' kullanılır
    )
    
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
