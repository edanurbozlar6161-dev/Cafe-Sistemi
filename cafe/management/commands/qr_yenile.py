"""Tüm masaların QR kodlarını güncel SITE_URL ile yeniden üretir.

Canlıya alındığında SITE_URL gerçek adrese ayarlanınca (örn. Render URL'si)
bu komut QR'ların doğru adrese işaret etmesini sağlar.

Kullanım: python manage.py qr_yenile
"""
from django.core.management.base import BaseCommand

from cafe.models import Masa
from cafe.qr import qr_olustur


class Command(BaseCommand):
    help = "Tüm masaların QR kodlarını güncel SITE_URL ile yeniden üretir."

    def handle(self, *args, **opts):
        for masa in Masa.objects.all():
            qr_olustur(masa)
        self.stdout.write(
            self.style.SUCCESS(f"{Masa.objects.count()} masa icin QR yenilendi.")
        )
