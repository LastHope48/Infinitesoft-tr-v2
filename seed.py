from app import app, db
from app import Project

with app.app_context():

    projects = [
        Project(
            slug="infinitecloud",
            title="InfiniteCloud",
            short_desc="Dosya yükleme servisi",
            description="InfiniteCloud, dosyalarınızı güvenle yükleyip paylaşmanızı sağlayan bir bulut uygulamasıdır.",
            icon="upload-icon-4.png"
        ),
        Project(
            slug="camsepeti",
            title="Çamsepeti",
            short_desc="Cam ürünleri e-ticaret sitesi",
            description="Çamsepeti, cam dekorasyon ürünlerinin sergilendiği modern bir e-ticaret projesidir.",
            icon="camsepeti.png"
        ),
        Project(
            slug="pushgame",
            title="Push Game",
            short_desc="Refleks oyunu",
            description="Push Game, hız ve refleks üzerine kurulu eğlenceli bir web oyunudur.",
            icon="mouse_pushgame.png"
        ),
        Project(
            slug="aitools",
            title="AI Tools",
            short_desc="Yapay zeka araçları koleksiyonu",
            description="AI Tools, çeşitli yapay zeka tabanlı araçları tek panelde sunar.",
            icon="AI_tools.png"
        ),
        Project(
            slug="guides",
            title="Tarifler",
            short_desc="Rehber & tarif platformu",
            description="Kullanıcıların rehber ve tarif paylaştığı mini bir içerik platformu.",
            icon="guides.png"
        ),
        Project(
            slug="notes",
            title="Notes",
            short_desc="Not alma uygulaması",
            description="Basit, hızlı ve minimal bir not alma aracı.",
            icon="post_icon.png"
        ),
        Project(
            slug="texteditor",
            title="Text Editor",
            short_desc="Online metin editörü",
            description="Tarayıcı üzerinden çalışan sade bir text editör.",
            icon="note.png"
        ),
        Project(
            slug="mekapus",
            title="Mekapus",
            short_desc="Oyun projesi",
            description="Geliştirme aşamasında olan deneysel bir oyun projesi.",
            icon="mekapus.png"
        ),
    ]

    for p in projects:
        db.session.add(p)

    db.session.commit()
    print("Tüm projeler eklendi 🚀")
