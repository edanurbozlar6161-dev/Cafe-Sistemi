import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.db.models import ProtectedError, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .forms import KategoriForm, UrunForm
from .models import Kategori, Masa, Siparis, SiparisKalemi, Urun

# Yönetim paneli erişimi: yalnızca staff kullanıcılar
staff_required = user_passes_test(
    lambda u: u.is_active and u.is_staff, login_url="cafe:panel_login"
)


# --------------------------------------------------------------------------- #
#  Yardımcılar
# --------------------------------------------------------------------------- #
def _aktif_masa(request):
    """Oturumdaki aktif masayı döndürür (yoksa None)."""
    masa_id = request.session.get("masa_id")
    if not masa_id:
        return None
    return Masa.objects.filter(id=masa_id).first()


def _json_body(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return None


# --------------------------------------------------------------------------- #
#  Sayfa görünümleri
# --------------------------------------------------------------------------- #
def home(request):
    """Demo/yönlendirme sayfası: masaları listeler (QR yerine hızlı test için)."""
    return render(request, "cafe/home.html", {"masalar": Masa.objects.all()})


def masa_giris(request, masa_uuid):
    """QR okutulduğunda gelinen sayfa: masayı tanır, oturuma yazar, karşılar."""
    masa = get_object_or_404(Masa, uuid=masa_uuid)
    masa.is_occupied = True
    masa.save(update_fields=["is_occupied"])
    request.session["masa_id"] = masa.id
    return render(request, "cafe/welcome.html", {"masa": masa})


@ensure_csrf_cookie
def menu(request):
    """Dijital menü ekranı."""
    masa = _aktif_masa(request)
    if not masa:
        return render(request, "cafe/qr_gerekli.html")
    kategoriler = Kategori.objects.prefetch_related("urunler").all()
    return render(request, "cafe/menu.html", {"masa": masa, "kategoriler": kategoriler})


@ensure_csrf_cookie
def takip(request, order_id):
    """Sipariş takip ekranı: mutfak durumu canlı izlenir, yemek sonunda ödenir."""
    siparis = get_object_or_404(Siparis, id=order_id)
    return render(request, "cafe/takip.html", {"siparis": siparis})


@ensure_csrf_cookie
def odeme(request, order_id):
    """Ödeme ekranı (sahte/mock ödeme) — yalnızca sipariş 'Hazır' olunca açılır."""
    siparis = get_object_or_404(Siparis, id=order_id)
    if siparis.is_paid:
        return redirect("cafe:tesekkurler", order_id=siparis.id)
    # Stok güvenliği: sipariş hazır değilken ödeme ekranına girilmesin
    if siparis.status not in (Siparis.HAZIR, Siparis.TESLIM):
        return redirect("cafe:takip", order_id=siparis.id)
    return render(request, "cafe/payment.html", {"siparis": siparis})


def tesekkurler(request, order_id):
    siparis = get_object_or_404(Siparis, id=order_id)
    return render(request, "cafe/success.html", {"siparis": siparis})


@ensure_csrf_cookie
def kitchen(request):
    """Mutfak paneli — siparişleri canlı gösterir."""
    return render(request, "cafe/kitchen.html")


# --------------------------------------------------------------------------- #
#  API uçları (dokümandaki tablo)
# --------------------------------------------------------------------------- #
@require_GET
def api_menu(request):
    """GET /api/menu/ — menüyü listele."""
    kategoriler = []
    for kat in Kategori.objects.prefetch_related("urunler"):
        kategoriler.append(
            {
                "id": kat.id,
                "name": kat.name,
                "emoji": kat.emoji,
                "urunler": [
                    {
                        "id": u.id,
                        "name": u.name,
                        "description": u.description,
                        "price": float(u.price),
                        "image": u.image.url if u.image else None,
                        "stock_status": u.satista,
                        "stock_count": u.stock_count,
                    }
                    for u in kat.urunler.all()
                ],
            }
        )
    return JsonResponse({"kategoriler": kategoriler})


@require_GET
def api_table(request, masa_id):
    """GET /api/table/<id>/ — masa bilgisini çek."""
    masa = get_object_or_404(Masa, id=masa_id)
    return JsonResponse(
        {
            "id": masa.id,
            "table_number": masa.table_number,
            "is_occupied": masa.is_occupied,
            "uuid": str(masa.uuid),
        }
    )


@require_POST
def api_order_create(request):
    """POST /api/order/create/ — yeni sipariş oluştur."""
    masa = _aktif_masa(request)
    if not masa:
        return JsonResponse(
            {"ok": False, "error": "Masa bulunamadı. Lütfen QR kodunu okutun."},
            status=400,
        )

    payload = _json_body(request)
    if payload is None:
        return JsonResponse({"ok": False, "error": "Geçersiz veri."}, status=400)

    items = payload.get("items", [])
    note = (payload.get("note") or "")[:255]
    if not items:
        return JsonResponse({"ok": False, "error": "Sepetiniz boş."}, status=400)

    siparis = Siparis.objects.create(table=masa, note=note)
    toplam = Decimal("0")
    for it in items:
        urun = Urun.objects.filter(id=it.get("product_id"), stock_status=True).first()
        if not urun or urun.stock_count <= 0:
            continue
        try:
            istenen = max(1, int(it.get("quantity", 1)))
        except (TypeError, ValueError):
            istenen = 1
        # Stoktan fazlası sipariş edilemez
        adet = min(istenen, urun.stock_count)
        SiparisKalemi.objects.create(
            order=siparis, product=urun, quantity=adet, unit_price=urun.price
        )
        # Stoğu düş
        urun.stock_count -= adet
        urun.save(update_fields=["stock_count"])
        toplam += urun.price * adet

    if not siparis.kalemler.exists():
        siparis.delete()
        return JsonResponse(
            {"ok": False, "error": "Geçerli ürün bulunamadı."}, status=400
        )

    siparis.total_price = toplam
    siparis.save(update_fields=["total_price"])
    # Sipariş mutfağa düştü; müşteri takip ekranına gider (ödeme yemek sonunda)
    return JsonResponse(
        {
            "ok": True,
            "order_id": siparis.id,
            "total": float(toplam),
            "redirect": reverse("cafe:takip", args=[siparis.id]),
        }
    )


@require_GET
def api_order_status(request, order_id):
    """GET /api/order/<id>/status/ — sipariş durumunu sorgula."""
    siparis = get_object_or_404(Siparis, id=order_id)
    return JsonResponse(
        {
            "order_id": siparis.id,
            "status": siparis.status,
            "status_label": siparis.durum_etiketi,
            "is_paid": siparis.is_paid,
            "payment_label": siparis.odeme_etiketi,
            "total": float(siparis.total_price),
        }
    )


@require_POST
def api_payment_confirm(request):
    """POST /api/payment/confirm/ — ödemeyi onayla (mock).

    Sadece ödeme durumunu işaretler; mutfak (hazırlık) durumuna dokunmaz.
    """
    payload = _json_body(request)
    if payload is None:
        return JsonResponse({"ok": False, "error": "Geçersiz veri."}, status=400)

    siparis = get_object_or_404(Siparis, id=payload.get("order_id"))
    # Stok güvenliği: yalnızca mutfak 'Hazır' (veya Teslim) işaretlediyse ödeme alınır
    if siparis.status not in (Siparis.HAZIR, Siparis.TESLIM):
        return JsonResponse(
            {
                "ok": False,
                "error": "Siparişiniz henüz hazır değil. Hazır olunca ödeyebilirsiniz.",
            },
            status=400,
        )
    if not siparis.is_paid:
        siparis.is_paid = True
        siparis.paid_at = timezone.now()
        siparis.save(update_fields=["is_paid", "paid_at", "updated_at"])

    # Ödeme = ziyaret sonu: masayı boşalt ve oturumu temizle
    masa = siparis.table
    masa.is_occupied = False
    masa.save(update_fields=["is_occupied"])
    request.session.pop("masa_id", None)

    return JsonResponse(
        {"ok": True, "redirect": reverse("cafe:tesekkurler", args=[siparis.id])}
    )


# --------------------------------------------------------------------------- #
#  Mutfak paneli uçları
# --------------------------------------------------------------------------- #
@require_GET
def api_kitchen_orders(request):
    """Teslim edilmemiş (aktif) siparişleri mutfak paneli için döndürür.

    Sipariş, ödenmiş olsa bile 'Teslim Edildi' olana kadar panelde kalır.
    """
    aktif = (
        Siparis.objects.exclude(status=Siparis.TESLIM)
        .select_related("table")
        .prefetch_related("kalemler__product")
        .order_by("created_at")
    )
    orders = []
    for s in aktif:
        orders.append(
            {
                "id": s.id,
                "masa": s.table.table_number,
                "status": s.status,
                "status_label": s.durum_etiketi,
                "is_paid": s.is_paid,
                "payment_label": s.odeme_etiketi,
                "total": float(s.total_price),
                "note": s.note,
                "created": timezone.localtime(s.created_at).strftime("%H:%M"),
                "kalemler": [
                    {"name": k.product.name, "qty": k.quantity}
                    for k in s.kalemler.all()
                ],
            }
        )
    return JsonResponse({"orders": orders})


@require_POST
def kitchen_update(request, order_id):
    """Mutfaktan sipariş (hazırlık) durumunu güncelle."""
    siparis = get_object_or_404(Siparis, id=order_id)
    payload = _json_body(request) or {}
    yeni = payload.get("status")
    if yeni in dict(Siparis.DURUM_SECENEKLERI):
        siparis.status = yeni
        siparis.save(update_fields=["status", "updated_at"])
        return JsonResponse({"ok": True, "status": siparis.status})
    return JsonResponse({"ok": False, "error": "Geçersiz durum."}, status=400)


# --------------------------------------------------------------------------- #
#  Özel Yönetim Paneli (tema uyumlu, görselli ürün yönetimi)
# --------------------------------------------------------------------------- #
@ensure_csrf_cookie
def panel_login(request):
    """Yönetim paneli girişi."""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("cafe:panel")
    hata = ""
    if request.method == "POST":
        kullanici = authenticate(
            request,
            username=request.POST.get("username"),
            password=request.POST.get("password"),
        )
        if kullanici and kullanici.is_staff:
            login(request, kullanici)
            return redirect("cafe:panel")
        hata = "Kullanıcı adı veya şifre hatalı."
    return render(request, "cafe/panel/login.html", {"hata": hata})


def panel_logout(request):
    logout(request)
    return redirect("cafe:panel_login")


@staff_required
def panel(request):
    """Yönetim paneli ana ekranı: ürünleri kategoriye göre listeler."""
    kategoriler = Kategori.objects.prefetch_related("urunler").all()
    return render(
        request,
        "cafe/panel/dashboard.html",
        {
            "kategoriler": kategoriler,
            "urun_sayisi": Urun.objects.count(),
            "kategori_sayisi": Kategori.objects.count(),
            "masa_sayisi": Masa.objects.count(),
            "stokta_yok": Urun.objects.filter(stock_status=False).count(),
        },
    )


@staff_required
def panel_urun_ekle(request):
    form = UrunForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Ürün başarıyla eklendi.")
        return redirect("cafe:panel")
    return render(
        request,
        "cafe/panel/urun_form.html",
        {"form": form, "baslik": "Yeni Ürün Ekle", "urun": None},
    )


@staff_required
def panel_urun_duzenle(request, urun_id):
    urun = get_object_or_404(Urun, id=urun_id)
    form = UrunForm(request.POST or None, request.FILES or None, instance=urun)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Ürün güncellendi.")
        return redirect("cafe:panel")
    return render(
        request,
        "cafe/panel/urun_form.html",
        {"form": form, "baslik": "Ürünü Düzenle", "urun": urun},
    )


@staff_required
@require_POST
def panel_urun_sil(request, urun_id):
    urun = get_object_or_404(Urun, id=urun_id)
    ad = urun.name
    gorsel = urun.image
    try:
        urun.delete()  # veritabanından kalıcı (hard) silme
    except ProtectedError:
        # Geçmiş siparişlerde geçen ürün, sipariş geçmişini korumak için silinemez
        messages.error(
            request,
            f"“{ad}” geçmiş siparişlerde yer aldığı için tamamen silinemez. "
            "Menüden kaldırmak için “Satışta” anahtarını kapatabilirsiniz.",
        )
        return redirect("cafe:panel")
    # Silme başarılı → görsel dosyasını da diskten temizle
    if gorsel:
        gorsel.delete(save=False)
    messages.success(request, f"“{ad}” tamamen silindi (veritabanı + görsel).")
    return redirect("cafe:panel")


@staff_required
@require_POST
def panel_urun_stok(request, urun_id):
    """Ürünün stok durumunu tersine çevir (AJAX)."""
    urun = get_object_or_404(Urun, id=urun_id)
    urun.stock_status = not urun.stock_status
    urun.save(update_fields=["stock_status"])
    return JsonResponse({"ok": True, "stock_status": urun.stock_status})


@staff_required
def panel_kategori_ekle(request):
    form = KategoriForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Kategori eklendi.")
        return redirect("cafe:panel")
    return render(
        request,
        "cafe/panel/kategori_form.html",
        {"form": form, "baslik": "Yeni Kategori Ekle"},
    )


@staff_required
def panel_kasa(request):
    """Kasa / Satışlar: tüm siparişler + ciro özeti."""
    tum = (
        Siparis.objects.select_related("table")
        .prefetch_related("kalemler__product")
        .order_by("-created_at")
    )
    odenmis = Siparis.objects.filter(is_paid=True)
    bugun = timezone.localdate()
    return render(
        request,
        "cafe/panel/kasa.html",
        {
            "siparisler": tum[:100],
            "bugun_ciro": odenmis.filter(paid_at__date=bugun).aggregate(t=Sum("total_price"))["t"] or 0,
            "toplam_ciro": odenmis.aggregate(t=Sum("total_price"))["t"] or 0,
            "bekleyen": Siparis.objects.filter(is_paid=False).aggregate(t=Sum("total_price"))["t"] or 0,
            "siparis_sayisi": tum.count(),
            "odenen_sayisi": odenmis.count(),
        },
    )


@staff_required
@require_POST
def panel_tahsil(request, order_id):
    """Kasadan elden/nakit tahsilat: siparişi ödendi işaretler, masayı boşaltır."""
    siparis = get_object_or_404(Siparis, id=order_id)
    if not siparis.is_paid:
        siparis.is_paid = True
        siparis.paid_at = timezone.now()
        siparis.save(update_fields=["is_paid", "paid_at", "updated_at"])
        siparis.table.is_occupied = False
        siparis.table.save(update_fields=["is_occupied"])
        messages.success(
            request,
            f"Sipariş #{siparis.id} tahsil edildi ({siparis.total_price:.0f} ₺).",
        )
    return redirect("cafe:panel_kasa")
