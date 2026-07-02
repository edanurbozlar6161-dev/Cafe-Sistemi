from django.urls import path

from . import views

app_name = "cafe"

urlpatterns = [
    # Sayfalar
    path("", views.home, name="home"),
    path("masa/<uuid:masa_uuid>/", views.masa_giris, name="masa_giris"),
    path("menu/", views.menu, name="menu"),
    path("siparis/<int:order_id>/", views.takip, name="takip"),
    path("odeme/<int:order_id>/", views.odeme, name="odeme"),
    path("tesekkurler/<int:order_id>/", views.tesekkurler, name="tesekkurler"),
    path("mutfak/", views.kitchen, name="kitchen"),
    # Yönetim paneli (özel, tema uyumlu)
    path("yonetim/giris/", views.panel_login, name="panel_login"),
    path("yonetim/cikis/", views.panel_logout, name="panel_logout"),
    path("yonetim/", views.panel, name="panel"),
    path("yonetim/urun/ekle/", views.panel_urun_ekle, name="panel_urun_ekle"),
    path("yonetim/urun/<int:urun_id>/duzenle/", views.panel_urun_duzenle, name="panel_urun_duzenle"),
    path("yonetim/urun/<int:urun_id>/sil/", views.panel_urun_sil, name="panel_urun_sil"),
    path("yonetim/urun/<int:urun_id>/stok/", views.panel_urun_stok, name="panel_urun_stok"),
    path("yonetim/kategori/ekle/", views.panel_kategori_ekle, name="panel_kategori_ekle"),
    path("yonetim/kasa/", views.panel_kasa, name="panel_kasa"),
    path("yonetim/satis/<int:order_id>/tahsil/", views.panel_tahsil, name="panel_tahsil"),
    # API (doküman)
    path("api/menu/", views.api_menu, name="api_menu"),
    path("api/table/<int:masa_id>/", views.api_table, name="api_table"),
    path("api/order/create/", views.api_order_create, name="api_order_create"),
    path(
        "api/order/<int:order_id>/status/",
        views.api_order_status,
        name="api_order_status",
    ),
    path("api/payment/confirm/", views.api_payment_confirm, name="api_payment_confirm"),
    # Mutfak paneli
    path("api/kitchen/orders/", views.api_kitchen_orders, name="api_kitchen_orders"),
    path(
        "api/kitchen/<int:order_id>/update/",
        views.kitchen_update,
        name="kitchen_update",
    ),
]
