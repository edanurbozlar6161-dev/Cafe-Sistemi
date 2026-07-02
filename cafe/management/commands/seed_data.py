"""Örnek kategori, ürün, masa ve QR verisini veritabanına yükler.

Görseller önce internetten (loremflickr) indirilir; başarısız olursa
Pillow ile şık bir yer tutucu görsel üretilir. Böylece her ürünün görseli olur.

Kullanım:
    python manage.py seed_data
    python manage.py seed_data --temizle   # önce mevcut menüyü siler
"""
import random
import urllib.request
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from cafe.models import Kategori, Masa, Urun
from cafe.qr import qr_olustur

# --------------------------------------------------------------------------- #
#  Menü içeriği:  (kategori, emoji, [ürünler])
#  ürün: (ad, açıklama, fiyat, görsel anahtar kelimeleri, stokta_mı)
# --------------------------------------------------------------------------- #
MENU = [
    ("Kahvaltı", "🍳", [
        ("Serpme Kahvaltı", "İki kişilik zengin kahvaltı tabağı", 320, "turkish,breakfast", True),
        ("Menemen", "Domates, biber ve yumurta", 110, "shakshuka,eggs", True),
        ("Sahanda Yumurta", "Tereyağında çift yumurta", 80, "fried,eggs", True),
        ("Simit & Peynir", "Susamlı simit, beyaz peynir", 65, "sesame,bagel", True),
        ("Bal & Kaymak", "Süzme bal ve taze kaymak", 95, "honey,cream", True),
    ]),
    ("Sıcak İçecekler", "☕", [
        ("Türk Kahvesi", "Közde pişmiş, lokumla", 50, "turkish,coffee", True),
        ("Latte", "Espresso ve buharlı süt", 60, "latte,coffee", True),
        ("Cappuccino", "Yoğun köpüklü espresso", 60, "cappuccino", True),
        ("Filtre Kahve", "Günün demlemesi", 55, "filter,coffee", True),
        ("Çay", "Demlik çay, ince belli bardak", 25, "turkish,tea", True),
        ("Sıcak Çikolata", "Bol kakaolu, kremalı", 65, "hot,chocolate", True),
    ]),
    ("Soğuk İçecekler", "🧊", [
        ("Ice Latte", "Buzlu sütlü kahve", 70, "iced,latte", True),
        ("Limonata", "Taze sıkım naneli limonata", 55, "lemonade", True),
        ("Milkshake", "Çilekli / çikolatalı", 80, "milkshake", True),
        ("Soğuk Çay", "Şeftalili ice tea", 50, "iced,tea", True),
        ("Portakal Suyu", "Taze sıkım", 45, "orange,juice", True),
    ]),
    ("Tatlılar", "🍰", [
        ("Cheesecake", "Frambuazlı New York usulü", 100, "cheesecake", True),
        ("Brownie", "Sıcak, dondurma topuyla", 90, "brownie,chocolate", True),
        ("Sufle", "Akışkan çikolatalı", 95, "chocolate,souffle", True),
        ("Tiramisu", "Mascarpone ve kahve", 95, "tiramisu", True),
        ("San Sebastian", "Bask usulü yanık cheesecake", 110, "basque,cheesecake", False),
    ]),
    ("Ana Yemekler", "🍔", [
        ("Hamburger", "180 gr köfte, cheddar, patates", 185, "hamburger,burger", True),
        ("Makarna", "Kremalı tavuklu fettuccine", 145, "pasta,creamy", True),
        ("Tost", "Karışık kaşarlı tost", 80, "toast,sandwich", True),
        ("Kızarmış Tavuk", "Çıtır tavuk, soslar", 165, "fried,chicken", True),
        ("Pizza Margherita", "Mozzarella ve fesleğen", 180, "pizza,margherita", True),
    ]),
    ("Atıştırmalık", "🍟", [
        ("Patates Kızartması", "Çıtır, baharatlı", 70, "french,fries", True),
        ("Nachos", "Cheddar soslu mısır cipsi", 95, "nachos", True),
        ("Soğan Halkası", "Çıtır soğan halkaları", 80, "onion,rings", True),
        ("Sigara Böreği", "Peynirli, 6 adet", 75, "spring,rolls", True),
    ]),
]

# Kategori bazlı yer tutucu görsel renkleri (üst, alt) — sıcak kafe tonları
RENKLER = {
    "Kahvaltı": ((255, 209, 102), (244, 162, 97)),
    "Sıcak İçecekler": ((123, 79, 54), (62, 39, 25)),
    "Soğuk İçecekler": ((137, 207, 240), (72, 149, 196)),
    "Tatlılar": ((247, 178, 200), (214, 113, 152)),
    "Ana Yemekler": ((231, 111, 81), (188, 71, 47)),
    "Atıştırmalık": ((244, 211, 94), (230, 162, 60)),
}


class Command(BaseCommand):
    help = "Örnek menü, masa ve QR verisini yükler."

    def add_arguments(self, parser):
        parser.add_argument(
            "--temizle",
            action="store_true",
            help="Yüklemeden önce mevcut kategori ve ürünleri siler.",
        )
        parser.add_argument(
            "--masa-sayisi", type=int, default=8, help="Oluşturulacak masa sayısı."
        )

    # ----------------------------- yardımcılar ----------------------------- #
    def _font(self, boyut):
        for yol in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
            try:
                return ImageFont.truetype(yol, boyut)
            except OSError:
                continue
        return ImageFont.load_default()

    def _yer_tutucu(self, ad, kategori):
        """Pillow ile gradyanlı, ürün adlı şık bir yer tutucu görsel üretir."""
        w, h = 640, 480
        ust, alt = RENKLER.get(kategori, ((180, 150, 120), (90, 70, 55)))
        img = Image.new("RGB", (w, h))
        px = img.load()
        for y in range(h):
            t = y / h
            r = int(ust[0] + (alt[0] - ust[0]) * t)
            g = int(ust[1] + (alt[1] - ust[1]) * t)
            b = int(ust[2] + (alt[2] - ust[2]) * t)
            for x in range(w):
                px[x, y] = (r, g, b)
        # hafif doku için yumuşak daireler
        draw = ImageDraw.Draw(img, "RGBA")
        for _ in range(6):
            cx, cy = random.randint(0, w), random.randint(0, h)
            rad = random.randint(40, 120)
            draw.ellipse(
                [cx - rad, cy - rad, cx + rad, cy + rad], fill=(255, 255, 255, 18)
            )
        img = img.filter(ImageFilter.GaussianBlur(1))
        draw = ImageDraw.Draw(img)
        # ürün adı (ortalı, çok satırlı)
        font = self._font(46)
        kelimeler = ad.split()
        satirlar, satir = [], ""
        for k in kelimeler:
            deneme = (satir + " " + k).strip()
            if draw.textlength(deneme, font=font) > w - 80:
                satirlar.append(satir)
                satir = k
            else:
                satir = deneme
        satirlar.append(satir)
        toplam_h = len(satirlar) * 56
        y = (h - toplam_h) // 2
        for s in satirlar:
            tw = draw.textlength(s, font=font)
            x = (w - tw) // 2
            draw.text((x + 2, y + 2), s, font=font, fill=(0, 0, 0, 120))  # gölge
            draw.text((x, y), s, font=font, fill=(255, 255, 255))
            y += 56
        # alt şerit "Manuçak"
        kf = self._font(22)
        draw.text((20, h - 40), "Manuçak", font=kf, fill=(255, 255, 255))
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=88)
        return buf.getvalue()

    def _indir(self, anahtar, lock):
        url = f"https://loremflickr.com/640/480/{anahtar}?lock={lock}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        Image.open(BytesIO(data)).verify()  # geçerli görsel mi?
        return data

    def _gorsel_al(self, ad, anahtar, kategori, lock):
        try:
            data = self._indir(anahtar, lock)
            kaynak = "indirildi"
        except Exception:
            data = self._yer_tutucu(ad, kategori)
            kaynak = "yer tutucu"
        return ContentFile(data), kaynak

    # ------------------------------- ana akış ------------------------------ #
    def handle(self, *args, **opts):
        # Windows konsolu (cp1254) emoji yazamadığı için stdout'u utf-8'e çevir
        for akis in (self.stdout, self.stderr):
            try:
                akis._out.reconfigure(encoding="utf-8")
            except Exception:
                pass

        if opts["temizle"]:
            Urun.objects.all().delete()
            Kategori.objects.all().delete()
            self.stdout.write(self.style.WARNING("Mevcut menü silindi."))

        lock = 1
        for sira, (kat_ad, emoji, urunler) in enumerate(MENU, start=1):
            kategori, _ = Kategori.objects.get_or_create(
                name=kat_ad, defaults={"emoji": emoji, "sira": sira}
            )
            kategori.emoji = emoji
            kategori.sira = sira
            kategori.save()

            for u_sira, (ad, aciklama, fiyat, anahtar, stok) in enumerate(urunler, 1):
                adet = random.randint(15, 60) if stok else 0
                urun, yeni = Urun.objects.get_or_create(
                    category=kategori,
                    name=ad,
                    defaults={
                        "description": aciklama,
                        "price": fiyat,
                        "stock_status": stok,
                        "stock_count": adet,
                        "sira": u_sira,
                    },
                )
                urun.description = aciklama
                urun.price = fiyat
                urun.stock_status = stok
                if not yeni and urun.stock_count == 0:
                    urun.stock_count = adet
                urun.sira = u_sira
                if not urun.image:
                    icerik, kaynak = self._gorsel_al(ad, anahtar, kat_ad, lock)
                    urun.image.save(f"urun_{lock}.jpg", icerik, save=False)
                    self.stdout.write(f"  • {ad}: görsel {kaynak}")
                urun.save()
                lock += 1
            self.stdout.write(self.style.SUCCESS(f"[OK] {kat_ad} kategorisi yuklendi."))

        # Masalar + QR
        for n in range(1, opts["masa_sayisi"] + 1):
            masa, _ = Masa.objects.get_or_create(table_number=n)
            if not masa.qr_code:
                qr_olustur(masa)
        self.stdout.write(
            self.style.SUCCESS(f"{opts['masa_sayisi']} masa ve QR kodları hazır.")
        )

        # Kolaylık için varsayılan yönetici
        User = get_user_model()
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser("admin", "admin@manucak.local", "admin123")
            self.stdout.write(
                self.style.WARNING("Yönetici oluşturuldu → kullanıcı: admin  şifre: admin123")
            )

        self.stdout.write(self.style.SUCCESS("\n[BITTI] Seed tamamlandi."))
