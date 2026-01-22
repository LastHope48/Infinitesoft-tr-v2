import os,uuid
from flask import Flask,render_template,render_template_string,request,send_from_directory,send_file,redirect,session,url_for,Response,abort,jsonify
import requests
from werkzeug.security import check_password_hash,generate_password_hash
from sqlalchemy import func,text
import io,zipfile
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
app=Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
PYANYWHERE_UPLOAD_URL = "https://wf5528.pythonanywhere.com/upload"
PYANYWHERE_LIST_URL   = "https://wf5528.pythonanywhere.com/list"
PYANYWHERE_SECRET     = "aa"
HF_URL="https://wf5528-infinitesoft-tr.hf.space/remove-bg"
PA_EXE_URL = "https://wf5529.pythonanywhere.com/static/uygulama/infinitesoft-tr.exe"
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    UPLOAD_PASSWORD=os.getenv("UPLOAD_PASSWORD")
    ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD")
else:
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
db=SQLAlchemy(app )
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key=os.urandom(32)
UPLOAD_FOLDER = "/home/wf5528/infinitecloud_api/uploads"
app.config["UPLOAD_FOLDER"]="uploads"
ALLOWED={"png","jpg","jpeg","mp4","mov","pdf","webp","mp3","pptx","zip"}
app.config["MAX_CONTENT_LENGTH"]=50*1024*1024
if DATABASE_URL:
    class Account(db.Model):
        __tablename__ = "accounts_table"
        __table_args__ = {"schema": "auth"}

        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(20), nullable=False, unique=True)
        password = db.Column(db.String(100), nullable=False)

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
        data = db.Column(db.LargeBinary)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        download_count = db.Column(db.Integer, default=0)
        is_global = db.Column(db.Boolean, default=False)
        high_lighted = db.Column(db.Boolean, default=False)
        owner_session = db.Column(db.String(100))

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

else:
    class Account(db.Model):
        __tablename__ = "accounts_table"

        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(20), nullable=False, unique=True)
        password = db.Column(db.String(100), nullable=False)

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
        data = db.Column(db.LargeBinary)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        download_count = db.Column(db.Integer, default=0)
        is_global = db.Column(db.Boolean, default=False)
        high_lighted = db.Column(db.Boolean, default=False)
        owner_session = db.Column(db.String(100))

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


def allowed(filename):
    return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED
@app.route("/")
def projects():
    return render_template("projects.html")
@app.route("/infinitecloud")
def cloud():
    return render_template("home_cloud.html")
@app.route("/__reset_db__")
def reset_db():
    if not session.get("can_delete"):
        abort(403)
    
    with app.app_context():
        db.drop_all()
        db.create_all()
        db.create_all(bind_key="accounts")
        db.create_all(bind_key="cards")
        db.create_all(bind_key="medias")
    
    return "DB sıfırlandı ✅"

@app.route("/camsepeti/home")
def home_shop():
    if "user_id" not in session:
        return redirect("/camsepeti")
    return render_template("home.html")
@app.route("/camsepeti/sepete_ekle",methods=["POST"])
def sepete_ekle():
    if "user_id" not in session:
        return redirect("/camsepeti")
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
@app.route("/camsepeti/sepet_sil", methods=["POST"])
def sepet_sil():
    if "user_id" not in session:
        return redirect("/camsepeti")
    index = int(request.form["index"])

    sepet = session.get("sepet", [])

    if 0 <= index < len(sepet):
        sepet.pop(index)
        session["sepet"] = sepet

    return redirect("/camsepeti/sepet")
@app.route("/camsepeti/buy_success",methods=["POST"])
def buy_success():
    if "user_id" not in session:
        return redirect("/camsepeti")
    return render_template("buy_success.html")
@app.route("/camsepeti/sepet")
def sepet():
    if "user_id" not in session:
        return redirect("/camsepeti")
    return render_template("sepet.html",sepet=session.get("sepet"))
@app.route("/camsepeti/buy")
def buy():
    if "user_id" not in session:
        return redirect("camsepeti")
    return render_template("buy.html")
@app.route("/camsepeti/register",methods=["GET","POST"])
def register():
    if request.method=="POST":
        try:
            name=request.form["name"]
            password=request.form["password"]

            hashed_pw=generate_password_hash(password)
            new_user=Account(name=name,password=hashed_pw)
            db.session.add(new_user)
            db.session.commit()
        except:
            return "Bu kullanıcı adı zaten var"
        return redirect("/camsepeti")
    return render_template("register.html")
@app.route("/camsepeti",methods=["GET","POST"])
def login():
    if request.method=="POST":
        name=request.form["name"]
        password=request.form["password"]
        user=Account.query.filter_by(name=name).first()
        if user and check_password_hash(user.password,password):
            session["user_id"]=user.id
            return redirect("/camsepeti/home")
        else:
            return "Hatalı giriş❌"
    return render_template("login.html")
@app.route("/camsepeti/logout")
def logout():
    session.clear()
    return redirect("/camsepeti")
@app.route("/infinitecloud/upload", methods=["GET","POST"])
def upload():
    if request.method=="POST":
        if UPLOAD_PASSWORD != request.form.get("password"):
            return jsonify(success=False, message="❌ Şifre yanlış")

        file = request.files.get("file")
        if not file or not allowed(file.filename):
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

        media = Media(
            original_name=original_name,
            stored_name=stored_name,
            data=file_bytes,
            is_global=is_global,
            high_lighted=high_lighted,
            owner_session=session["uploader_id"]
        )

        db.session.add(media)
        db.session.commit()
        send_to_pythonanywhere(original_name, file_bytes)
        print("UPLOAD OK:", original_name)
        return jsonify(success=True, message="✅ Dosya yüklendi")

    return render_template("upload.html")


@app.route("/infinitecloud/files/<int:media_id>/download")
def download_file(media_id):
    media = Media.query.get_or_404(media_id)

    if not media.is_global:
        if session.get("can_delete") is not True and media.owner_session != session.get("uploader_id"):
            return "❌ Bu dosya gizli", 403

    media.download_count += 1
    db.session.commit()

    return send_file(
        io.BytesIO(media.data),
        as_attachment=True,
        download_name=media.original_name
    )

@app.route("/infinitecloud/files/<int:media_id>")
def look(media_id):
    media = Media.query.get_or_404(media_id)
    if not media.is_global:
        if session.get("can_delete") is not True and media.owner_session != session.get("uploader_id"):
            abort(403)
    return send_file(
        io.BytesIO(media.data),
        as_attachment=False,
        download_name=media.original_name
    )

@app.route("/infinitecloud/files/<int:media_id>/delete")
def delete_file(media_id):
    media = Media.query.get_or_404(media_id)

    is_admin = session.get("can_delete") is True
    is_owner = media.owner_session == session.get("uploader_id")

    if not (is_admin or is_owner):
        abort(403)

    db.session.delete(media)
    db.session.commit()
    return redirect("/infinitecloud/files")

@app.route("/admin", methods=["GET", "POST"])
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

@app.route("/infinitecloud/reset", methods=["POST"])
def reset_files():
    if not session.get("can_reset"):
        return redirect("/infinitecloud/reset-login")

    medias = Media.query.all()
    for media in medias:
        db.session.delete(media)
    db.session.commit()

    session.pop("can_reset")
    return "✅ Tüm dosyalar silindi."

@app.route("/infinitecloud/files")
def files():
    if "uploader_id" not in session:
        session["uploader_id"] = str(uuid.uuid4())
    uploader_id = session.get("uploader_id")
    is_admin = session.get("can_delete", False)
    if not is_admin:
        medias = Media.query.filter(Media.is_global== True).all()
    elif is_admin:
        medias = Media.query.all()
    print("SESSION uploader_id:", uploader_id)
    print("DB owner_session:", [m.owner_session for m in Media.query.all()])


    files_count = len(medias)

    pa_files = []
    try:
        r = requests.get(
            os.getenv("PYANYWHERE_LIST_URL"),
            headers={"X-SECRET": os.getenv("PYANYWHERE_SECRET")},
            timeout=5
        )
        pa_files = r.json().get("files", [])
    except:
         pass

    return render_template(
        "files.html",
        files=medias,
        files_count=files_count,
        can_reset=session.get("can_reset", False),
        can_delete=is_admin,
        pa_files=pa_files,
    )


@app.route("/infinitecloud/files/download_all")
def download_all():
    medias = Media.query.all()
    if not medias:
        return "Hiç dosya yok."

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for media in medias:
            zip_file.writestr(media.original_name, media.data)

    zip_buffer.seek(0)

    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name="all_files.zip",
        mimetype="application/zip"
    )
# Sistemler
@app.route('/sitemap.xml', methods=['GET'])
def sitemap():
    sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://www.infinitesoft-tr.com/</loc>
  </url>
</urlset>
"""
    return Response(sitemap_xml, mimetype='application/xml')
@app.route("/infinitecloud/files/pa/download/<filename>")
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
@app.route("/infinitecloud/pa/delete/<filename>", methods=["POST"])
def pa_delete(filename):
    r = requests.post(
        f"https://wf5528.pythonanywhere.com/delete/{filename}",
        headers={"X-SECRET": PYANYWHERE_SECRET},
        timeout=5
    )

    if r.status_code == 200:
        return redirect("/infinitecloud/files")
    return "Silinemedi", 400
@app.route("/admin/broadcast", methods=["POST"])
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
@app.route("/admins")
def admin_panel():
    if not session.get("can_delete"):
        abort(403)
    return render_template("admins.html")
@app.context_processor
def inject_broadcast():
    now = datetime.utcnow()

    # Süresi dolanları temizle
    expired = SiteMessage.query.filter(
        SiteMessage.expires_at < now
    ).all()

    for msg in expired:
        db.session.delete(msg)

    if expired:
        db.session.commit()

    # Aktif mesaj (en son girilen)
    active = SiteMessage.query.filter(
        SiteMessage.expires_at > now
    ).order_by(SiteMessage.created_at.desc()).first()

    return {
        "broadcast_message": active.message if active else None
    }

@app.route("/admin/broadcast-panel")
def broadcast_panel():
    if not session.get("can_delete"):
        return "Yetkisiz", 403
    return render_template("admin_broadcast.html")
@app.route("/infinitecloud/myfiles")
def myfiles():
    uploader_id=session.get("uploader_id")
    if "uploader_id" not in session:
        session["uploader_id"] = str(uuid.uuid4())
    medias=Media.query.filter(
        (Media.is_global==False) &
        (Media.owner_session==uploader_id)
    ).all()
    return render_template("myfiles.html",files=medias)
@app.route("/infinitecloud/myfiles/<int:media_id>/delete")
def delete_myfile(media_id):
    media=Media.query.get_or_404(media_id)
    if session.get("can_delete") is not True and media.owner_session != session.get("uploader_id"):
        abort(403)

    db.session.delete(media)
    db.session.commit()
    return redirect("/infinitecloud/myfiles")
@app.route("/infinitecloud/myfiles/<int:media_id>")
def lookmy(media_id):
    media = Media.query.get_or_404(media_id)
    if not media.is_global:
        if session.get("can_delete") is not True and media.owner_session != session.get("uploader_id"):
            abort(403)
    return send_file(
        io.BytesIO(media.data),
        as_attachment=False,
        download_name=media.original_name
    )
@app.route("/infinitecloud/myfiles/<int:media_id>/download")
def download_myfile(media_id):
    media = Media.query.get_or_404(media_id)

    if not media.is_global:
        if session.get("can_delete") is not True and media.owner_session != session.get("uploader_id"):
            return "❌ Bu dosya gizli", 403

    media.download_count += 1
    db.session.commit()

    return send_file(
        io.BytesIO(media.data),
        as_attachment=True,
        download_name=media.original_name,
        files_count=media.download_count
    )
# PUSH GAME
@app.route("/pushgame")
def gamestart():
    return render_template("pushgame.html")
@app.route("/pushgame/game", methods=["POST"])
def game():
    return render_template("pushgame_game.html")
# YENİLİKLER
@app.route("/news")
def news():
    updates = SiteUpdate.query.order_by(
        SiteUpdate.created_at.desc()
    ).all()
    return render_template("last_updates.html", updates=updates)

@app.route("/admin/news", methods=["GET", "POST"])
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
@app.route("/indir")
def uygulama():
    return render_template("indir.html")
@app.route("/infinitesoft-tr.exe")
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

# BACKGROUND REMOVER
@app.route("/backdeleter",methods=["GET","POST"])
def back_delete():
  return render_template("background_remover.html")
@app.route("/backdeleter/remove", methods=["POST"])
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
@app.route('/cards')
def index():
    cards=Card.query.order_by(Card.id).all()

    return render_template('index.html',
                           #kartlar = kartlar
                            cards=cards,
                           )
@app.route('/cards/card/<int:id>')
def card(id):
    # Görev #2. Id'ye göre doğru kartı görüntüleme
    card=Card.query.get(id)

    return render_template('card.html', card=card)
@app.route('/cards/create')
def create():
    return render_template('create_card.html')
@app.route('/cards/form_create', methods=['GET','POST'])
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
@app.route("/text_editor")
def editor():
    return render_template("text_editor.html")
# HATALAR
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

with app.app_context():
    db.create_all()
if __name__=="__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
