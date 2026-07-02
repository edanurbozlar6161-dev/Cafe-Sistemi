"""Teslim öncesi veritabanı temizliği.

Siparişleri ve ürünleri (görselleriyle) siler; MASALAR (+QR), KATEGORİLER ve
YÖNETİCİ hesabı korunur. Böylece işletme sahibi temiz bir menüyle başlar.

Güvenlik: --onayla verilmezse hiçbir şey silinmez, sadece özet gösterilir.

Kullanım:
    python manage.py teslim_temizle            # kuru çalışma (silmez, gösterir)
    python manage.py teslim_temizle --onayla    # gerçekten siler
    python manage.py teslim_temizle --onayla --kategoriler   # kategorileri de siler
"""
from django.core.management.base import BaseCommand

from cafe.models import Kategori, Masa, Siparis, SiparisKalemi, Urun


class Command(BaseCommand):
    help = "Teslim öncesi: siparişleri ve ürünleri siler, masaları/kategorileri korur."

    def add_arguments(self, parser):
        parser.add_argument(
            "--onayla", action="store_true",
            help="Silmeyi onaylar. Verilmezse yalnızca ne yapılacağını gösterir.",
        )
        parser.add_argument(
            "--kategoriler", action="store_true",
            help="Kategorileri de siler (varsayılan: korunur).",
        )

    def handle(self, *args, **opts):
        for akis in (self.stdout, self.stderr):
            try:
                akis._out.reconfigure(encoding="utf-8")
            except Exception:
                pass

        siparis_n = Siparis.objects.count()
        urun_n = Urun.objects.count()
        kategori_n = Kategori.objects.count()
        masa_n = Masa.objects.count()

        self.stdout.write("Mevcut durum:")
        self.stdout.write(f"  Siparis : {siparis_n}")
        self.stdout.write(f"  Urun    : {urun_n}")
        self.stdout.write(f"  Kategori: {kategori_n}")
        self.stdout.write(f"  Masa    : {masa_n}")

        if not opts["onayla"]:
            self.stdout.write(self.style.WARNING(
                "\n[KURU CALISMA] Hicbir sey silinmedi."
            ))
            silinecek = "tum siparisler + tum urunler (gorselleriyle)"
            if opts["kategoriler"]:
                silinecek += " + tum kategoriler"
            self.stdout.write(f"Silinecek : {silinecek}")
            self.stdout.write("Korunacak : masalar (+QR kodlari), yonetici hesabi"
                              + ("" if opts["kategoriler"] else ", kategoriler"))
            self.stdout.write(self.style.NOTICE(
                "\nGercekten silmek icin: python manage.py teslim_temizle --onayla"
            ))
            return

        # --- Gercek silme ---
        SiparisKalemi.objects.all().delete()
        Siparis.objects.all().delete()
        # Urun gorsellerini diskten de temizle
        for u in Urun.objects.all():
            if u.image:
                u.image.delete(save=False)
        Urun.objects.all().delete()
        if opts["kategoriler"]:
            Kategori.objects.all().delete()
        Masa.objects.update(is_occupied=False)

        self.stdout.write(self.style.SUCCESS(
            "\nTemizlik tamam. Korunanlar: "
            + f"{Masa.objects.count()} masa (+QR), "
            + f"{Kategori.objects.count()} kategori, yonetici hesabi."
        ))
        self.stdout.write(self.style.NOTICE(
            "Oneri: Django admin'den yonetici sifresini degistirin "
            "ve isletmenin kendi urunlerini /yonetim/ panelinden ekleyin."
        ))
