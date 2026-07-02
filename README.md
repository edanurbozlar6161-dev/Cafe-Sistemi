# ☕ Manuçak — QR Tabanlı Sipariş ve Ödeme Yönetim Sistemi

Restoran ve kafelerde **personel eksikliği, hatalı sipariş alımı ve ödeme kuyrukları**
sorununa çözüm getiren akıllı kafe sistemi. Müşteri masadaki **QR kodu** okutur,
dijital menüden siparişini verir ve ödemesini yerinden tamamlar. Siparişler anlık
olarak **mutfak paneline** düşer.


---

## 🚀 Hızlı Başlangıç

```bash
# 1) Bağımlılıkları kur (sanal ortam opsiyonel ama önerilir)
pip install -r requirements.txt

# 2) Veritabanını oluştur
python manage.py migrate

# 3) Örnek menü, görseller, masalar ve QR kodlarını yükle
python manage.py seed_data

# 4) Sunucuyu başlat
python manage.py runserver
```

Ardından tarayıcıdan:

| Sayfa | Adres |
|-------|-------|
| 🏠 Demo Giriş (masa seç) | http://127.0.0.1:8000/ |
| 👨‍🍳 Mutfak Paneli | http://127.0.0.1:8000/mutfak/ |
| ⚙️ Yönetim Paneli (özel) | http://127.0.0.1:8000/yonetim/ |
| 💰 Kasa / Satışlar | http://127.0.0.1:8000/yonetim/kasa/ |
| 🛠️ Django Admin | http://127.0.0.1:8000/admin/ |

**Yönetici girişi:** kullanıcı `admin` · şifre `admin123`
(seed sırasında otomatik oluşturulur · hem özel panel hem Django admin için geçerli)

**Özel yönetim paneli** (`/yonetim/`): tema uyumlu, görselli **ürün ekle / düzenle / sil**,
stok aç-kapa ve kategori ekleme — değişiklikler menüye anında yansır.

**Kasa / Satışlar** (`/yonetim/kasa/`): tüm siparişler satır satır (masa, saat, ürünler, tutar,
mutfak durumu, ödeme durumu) + ciro özeti (bugünkü/toplam/ödeme bekleyen). Teslim edilen
siparişler de kayıtlı kalır; ödenmemiş siparişler kasadan **"Tahsil Et"** ile kapatılabilir.

---

## 🚀 Canlıya Alma (Render)

Proje Render için hazırdır: `render.yaml`, `requirements.txt`, WhiteNoise (statik) ve gunicorn dahil.

**1) GitHub'a açık (public) repo olarak yükle:**
```bash
cd Manucak
git init
git add .
git commit -m "Manucak - QR tabanli kafe siparis sistemi"
git branch -M main
git remote add origin https://github.com/<KULLANICI>/manucak.git
git push -u origin main
```

**2) Render'da yayınla:**
- render.com → **New → Blueprint** → repoyu seç (`render.yaml` otomatik okunur), veya
- **New → Web Service** → repo seç → ayarlar:
  - Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py qr_yenile`
  - Start: `gunicorn manucak.wsgi:application --bind 0.0.0.0:$PORT`
  - Ortam değişkenleri: `DEBUG=False` · `SECRET_KEY=<rastgele>` · `PYTHON_VERSION=3.12.8`
- Deploy sonrası oluşan adresi (örn. `https://manucak.onrender.com`) **`SITE_URL`** env değişkenine yaz → QR kodları canlı adrese işaret eder.

**Notlar:**
- Ücretsiz katman 15 dk hareketsizlikte uykuya geçer; ilk istek ~30 sn sürebilir.
- Menü, görseller ve yönetici hesabı depoya dahil olduğu için canlıda hazır gelir.
  Ziyaretçi siparişleri servis yeniden başlayınca sıfırlanır (demo için yeterli).
- Yönetici: `admin / admin123` — canlıda şifreyi Django admin'den değiştirin.

---

## 📱 Telefonla QR Testi (opsiyonel)

QR kodlarını gerçek telefonla okutmak için:

1. Bilgisayarın yerel IP'sini öğren (`ipconfig`), örn. `192.168.1.20`.
2. `manucak/settings.py` içindeki `SITE_URL` değerini güncelle:
   ```python
   SITE_URL = "http://192.168.1.20:8000"
   ```
3. QR'ları yeniden üret: Yönetim paneli → **Masalar** → tümünü seç →
   *"Seçili masalar için QR kodu üret"* aksiyonu.
4. Sunucuyu ağa aç: `python manage.py runserver 0.0.0.0:8000`
5. Telefon, bilgisayarla **aynı Wi-Fi ağında** olmalı. QR'ı okut → menü açılır.

---

## 🧩 Kullanılan Teknolojiler

- **Arka Uç:** Python · Django 6
- **Ön Uç:** HTML5 · CSS3 · Bootstrap 5 · Vanilla JS (responsive, mobil öncelikli)
- **Veritabanı:** SQLite (geliştirme) — PostgreSQL'e kolayca taşınabilir
- **QR:** `qrcode` (UUID tabanlı benzersiz masa linkleri)
- **Görseller:** `Pillow`

---

## 🗄️ Veritabanı Şeması

| Model | Alanlar |
|-------|---------|
| **Kategori** | name, emoji, sira |
| **Urun** | category, name, description, price, image, **stock_count** (stok adedi), stock_status (satışta mı), sira (görünüm sırası) |
| **Masa** | table_number, uuid, is_occupied, qr_code |
| **Siparis** | table, total_price, **status** = mutfak durumu (Beklemede→Hazırlanıyor→Hazır→Teslim Edildi), **is_paid** + paid_at = ödeme durumu (mutfaktan bağımsız), note, created_at |
| **SiparisKalemi** | order, product, quantity, unit_price |

---

## 🔌 API Uçları

| Metot | Adres | Açıklama |
|-------|-------|----------|
| GET  | `/api/menu/` | Menüyü listele |
| GET  | `/api/table/<id>/` | Masa bilgisini çek |
| POST | `/api/order/create/` | Yeni sipariş oluştur |
| GET  | `/api/order/<id>/status/` | Sipariş durumunu sorgula |
| POST | `/api/payment/confirm/` | Ödemeyi onayla (mock) |
| GET  | `/api/kitchen/orders/` | Aktif siparişler (mutfak) |
| POST | `/api/kitchen/<id>/update/` | Sipariş durumunu güncelle |

---

## 🔄 Kullanıcı Akışı

Ödeme **yemek sonunda** alınır; mutfak hazırlığından bağımsızdır.

```
QR okut → Karşılama → Menü → Sepet → Sipariş Takip ──(yemek sonunda)──► Ödeme → Teşekkürler
                                          │
                                          ▼
                                   Mutfak Paneli (canlı)
        Beklemede → Hazırlanıyor → Hazır → Teslim Edildi   (ödemeden bağımsız)
```

1. **Karşılama:** Masa otomatik tanınır, hoş geldiniz ekranı.
2. **Menü:** Kategori sekmeleri, görselli ürün kartları, canlı sepet.
3. **Sepet:** Adet kontrolü, sipariş notu, tek tıkla sipariş.
4. **Sipariş Takip:** Sipariş mutfağa düşer; müşteri durumu canlı izler
   (Beklemede→Hazırlanıyor→Hazır→Teslim). **"Hesabı Öde" butonu yalnızca sipariş
   "Hazır" olunca aktifleşir** — böylece stokta olmayan/yapılamayan bir ürüne ödeme alınmaz.
5. **Ödeme:** Sipariş özeti + sahte kart ekranı (gerçek tahsilat yok).
   Ödeme yalnızca *ödeme durumunu* işaretler; sipariş **Teslim Edilene** kadar mutfakta kalır.
6. **Mutfak:** Siparişler renk kodlu kartlarda + **ödeme rozetiyle** (Ödendi / Ödeme bekliyor)
   anlık görünür, durum ilerletilir (4 saniyede bir otomatik yenilenir).

---

## 📁 Proje Yapısı

```
Manucak/
├── manage.py
├── requirements.txt
├── manucak/              # proje ayarları
│   ├── settings.py
│   └── urls.py
├── cafe/                 # ana uygulama
│   ├── models.py         # Kategori, Urun, Masa, Siparis, SiparisKalemi
│   ├── views.py          # sayfalar + API uçları + mutfak + yönetim paneli
│   ├── forms.py          # ürün/kategori formları (görsel yükleme)
│   ├── urls.py
│   ├── admin.py          # Django admin özelleştirmesi
│   ├── qr.py             # QR üretim yardımcısı
│   ├── management/commands/seed_data.py   # örnek veri + görsel indirme
│   ├── templates/cafe/   # welcome, menu, takip, payment, success, kitchen, home
│   │   └── panel/        # özel yönetim paneli (login, dashboard, urun_form, kategori_form)
│   └── static/cafe/      # style.css, menu.js, kitchen.js
└── media/                # ürün görselleri + QR kodları (seed üretir)
```

---

## 📝 Notlar

- **Sahte ödeme:** `/api/payment/confirm/` sadece siparişin `is_paid` alanını işaretler;
  mutfak durumuna dokunmaz. Gerçek bir ödeme ağ geçidi entegre edilmemiştir (final demo kapsamı).
- **Görseller:** `seed_data` ürün görsellerini internetten indirir; indirme başarısız
  olursa Pillow ile şık bir yer tutucu üretilir (hiçbir ürün görselsiz kalmaz).
- **Gelecek çalışmalar (dokümandaki gibi):** "Garson Çağır" butonu ve
  "Yapay Zeka Destekli Ürün Önerisi".

### 🧹 Teslim öncesi temizlik

İşletmeye teslim ederken örnek verileri silmek için (masalar, QR'lar, kategoriler ve
yönetici **korunur**; sipariş ve ürünler silinir):

```bash
python manage.py teslim_temizle            # önce göster (silmez)
python manage.py teslim_temizle --onayla    # gerçekten temizle
```

Ardından işletme `/yonetim/` panelinden kendi ürünlerini ekler.
**Öneri:** Django admin'den `admin` şifresini değiştirin.
