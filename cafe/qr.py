"""Masalar için UUID tabanlı QR kodu üretimi."""

from io import BytesIO

import qrcode
from django.conf import settings
from django.core.files.base import ContentFile


def masa_linki(masa):
    """Masaya ait, QR'a gömülecek tam adresi döndürür."""
    base = settings.SITE_URL.rstrip("/")
    return f"{base}/masa/{masa.uuid}/"


def qr_olustur(masa, kaydet=True):
    """Verilen masa için QR kodu görseli üretir ve qr_code alanına yazar."""
    link = masa_linki(masa)

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#3b2417", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    dosya_adi = f"masa_{masa.table_number}.png"

    masa.qr_code.save(dosya_adi, ContentFile(buffer.getvalue()), save=kaydet)
    return masa.qr_code
