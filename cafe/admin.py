from django.contrib import admin
from django.utils.html import format_html

from .models import Kategori, Masa, Siparis, SiparisKalemi, Urun
from .qr import qr_olustur

admin.site.site_header = "Manuçak Yönetim Paneli"
admin.site.site_title = "Manuçak"
admin.site.index_title = "Akıllı Kafe Yönetimi"


@admin.register(Kategori)
class KategoriAdmin(admin.ModelAdmin):
    list_display = ("name", "emoji", "sira", "urun_sayisi")
    list_editable = ("sira",)
    search_fields = ("name",)

    @admin.display(description="Ürün Sayısı")
    def urun_sayisi(self, obj):
        return obj.urunler.count()


@admin.register(Urun)
class UrunAdmin(admin.ModelAdmin):
    list_display = ("onizleme", "name", "category", "price", "stock_count", "stock_status", "sira")
    list_display_links = ("onizleme", "name")
    list_editable = ("price", "stock_count", "stock_status", "sira")
    list_filter = ("category", "stock_status")
    search_fields = ("name", "description")

    @admin.display(description="Görsel")
    def onizleme(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:42px;width:42px;'
                'object-fit:cover;border-radius:8px;" />',
                obj.image.url,
            )
        return "—"


@admin.register(Masa)
class MasaAdmin(admin.ModelAdmin):
    list_display = ("table_number", "is_occupied", "qr_onizleme")
    readonly_fields = ("uuid", "qr_onizleme")
    actions = ("qr_kodlari_uret",)

    @admin.display(description="QR")
    def qr_onizleme(self, obj):
        if obj.qr_code:
            return format_html(
                '<img src="{}" style="height:90px;width:90px;" />', obj.qr_code.url
            )
        return "QR yok — 'QR kodları üret' aksiyonunu çalıştırın"

    @admin.action(description="Seçili masalar için QR kodu üret")
    def qr_kodlari_uret(self, request, queryset):
        for masa in queryset:
            qr_olustur(masa)
        self.message_user(request, f"{queryset.count()} masa için QR kodu üretildi.")


class SiparisKalemiInline(admin.TabularInline):
    model = SiparisKalemi
    extra = 0
    readonly_fields = ("ara_toplam",)


@admin.register(Siparis)
class SiparisAdmin(admin.ModelAdmin):
    list_display = ("id", "table", "durum_rozeti", "odeme_rozeti", "total_price", "created_at")
    list_filter = ("status", "is_paid", "table")
    readonly_fields = ("total_price", "is_paid", "paid_at", "created_at", "updated_at")
    inlines = (SiparisKalemiInline,)
    date_hierarchy = "created_at"

    @admin.display(description="Mutfak Durumu")
    def durum_rozeti(self, obj):
        renkler = {
            Siparis.BEKLEMEDE: "#9e9e9e",
            Siparis.HAZIRLANIYOR: "#e08a00",
            Siparis.HAZIR: "#2e7d32",
            Siparis.TESLIM: "#1565c0",
        }
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;'
            'border-radius:10px;font-size:12px;">{}</span>',
            renkler.get(obj.status, "#555"),
            obj.durum_etiketi,
        )

    @admin.display(description="Ödeme")
    def odeme_rozeti(self, obj):
        renk = "#2e7d32" if obj.is_paid else "#c0392b"
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;'
            'border-radius:10px;font-size:12px;">{}</span>',
            renk,
            obj.odeme_etiketi,
        )
