import uuid

from django.db import models
from django.urls import reverse


class Kategori(models.Model):
    """Menü kategorisi (Kahvaltı, Sıcak İçecekler, Tatlılar ...)."""

    name = models.CharField("Kategori Adı", max_length=80, unique=True)
    emoji = models.CharField("Emoji", max_length=8, blank=True, default="")
    sira = models.PositiveIntegerField("Sıra", default=0)

    class Meta:
        verbose_name = "Kategori"
        verbose_name_plural = "Kategoriler"
        ordering = ["sira", "name"]

    def __str__(self):
        return self.name


class Urun(models.Model):
    """Menüdeki ürün."""

    category = models.ForeignKey(
        Kategori,
        verbose_name="Kategori",
        on_delete=models.CASCADE,
        related_name="urunler",
    )
    name = models.CharField("Ürün Adı", max_length=120)
    description = models.CharField("Açıklama", max_length=255, blank=True, default="")
    price = models.DecimalField("Fiyat (₺)", max_digits=7, decimal_places=2)
    image = models.ImageField("Görsel", upload_to="products/", blank=True, null=True)
    stock_status = models.BooleanField("Satışta (menüde aktif)", default=True)
    stock_count = models.PositiveIntegerField("Stok Adedi", default=0)
    sira = models.PositiveIntegerField("Görünüm Sırası", default=0)

    class Meta:
        verbose_name = "Ürün"
        verbose_name_plural = "Ürünler"
        ordering = ["category__sira", "sira", "name"]

    def __str__(self):
        return f"{self.name} ({self.price} ₺)"

    @property
    def satista(self):
        """Müşteri menüsünde sipariş edilebilir mi? (aktif ve stokta var)."""
        return self.stock_status and self.stock_count > 0


class Masa(models.Model):
    """Kafe masası. Her masanın benzersiz bir UUID'si ve QR kodu vardır."""

    table_number = models.PositiveIntegerField("Masa Numarası", unique=True)
    uuid = models.UUIDField("UUID", default=uuid.uuid4, editable=False, unique=True)
    is_occupied = models.BooleanField("Dolu mu?", default=False)
    qr_code = models.ImageField("QR Kodu", upload_to="qr/", blank=True, null=True)

    class Meta:
        verbose_name = "Masa"
        verbose_name_plural = "Masalar"
        ordering = ["table_number"]

    def __str__(self):
        return f"Masa {self.table_number}"

    def get_absolute_url(self):
        return reverse("cafe:masa_giris", kwargs={"masa_uuid": self.uuid})


class Siparis(models.Model):
    """Bir masadan verilen sipariş."""

    # Mutfak (hazırlık) durumu — ödemeden bağımsızdır
    BEKLEMEDE = "beklemede"
    HAZIRLANIYOR = "hazirlaniyor"
    HAZIR = "hazir"
    TESLIM = "teslim"

    DURUM_SECENEKLERI = [
        (BEKLEMEDE, "Beklemede"),
        (HAZIRLANIYOR, "Hazırlanıyor"),
        (HAZIR, "Hazır"),
        (TESLIM, "Teslim Edildi"),
    ]

    table = models.ForeignKey(
        Masa,
        verbose_name="Masa",
        on_delete=models.CASCADE,
        related_name="siparisler",
    )
    total_price = models.DecimalField(
        "Toplam Tutar (₺)", max_digits=9, decimal_places=2, default=0
    )
    status = models.CharField(
        "Mutfak Durumu", max_length=20, choices=DURUM_SECENEKLERI, default=BEKLEMEDE
    )
    is_paid = models.BooleanField("Ödendi mi?", default=False)
    paid_at = models.DateTimeField("Ödeme Zamanı", blank=True, null=True)
    note = models.CharField("Sipariş Notu", max_length=255, blank=True, default="")
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)
    updated_at = models.DateTimeField("Güncellenme", auto_now=True)

    class Meta:
        verbose_name = "Sipariş"
        verbose_name_plural = "Siparişler"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Sipariş #{self.pk} - Masa {self.table.table_number}"

    def hesapla_toplam(self):
        """Kalemlerden toplam tutarı hesaplayıp kaydeder."""
        toplam = sum((kalem.ara_toplam for kalem in self.kalemler.all()), 0)
        self.total_price = toplam
        self.save(update_fields=["total_price", "updated_at"])
        return toplam

    @property
    def durum_etiketi(self):
        return dict(self.DURUM_SECENEKLERI).get(self.status, self.status)

    @property
    def odeme_etiketi(self):
        return "Ödendi" if self.is_paid else "Ödeme Bekliyor"


class SiparisKalemi(models.Model):
    """Bir siparişteki tek bir ürün satırı."""

    order = models.ForeignKey(
        Siparis,
        verbose_name="Sipariş",
        on_delete=models.CASCADE,
        related_name="kalemler",
    )
    product = models.ForeignKey(
        Urun, verbose_name="Ürün", on_delete=models.PROTECT
    )
    quantity = models.PositiveIntegerField("Adet", default=1)
    unit_price = models.DecimalField("Birim Fiyat (₺)", max_digits=7, decimal_places=2)

    class Meta:
        verbose_name = "Sipariş Kalemi"
        verbose_name_plural = "Sipariş Kalemleri"

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def ara_toplam(self):
        return self.quantity * self.unit_price
