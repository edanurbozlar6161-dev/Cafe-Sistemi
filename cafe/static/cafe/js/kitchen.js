/* Manuçak — mutfak paneli (canlı sipariş takibi) */
(function () {
  "use strict";

  function getCookie(n){const m=document.cookie.match("(^|;)\\s*"+n+"\\s*=\\s*([^;]+)");return m?m.pop():"";}
  const csrf = () => { const i=document.querySelector("[name=csrfmiddlewaretoken]"); return i?i.value:getCookie("csrftoken"); };

  const grid = document.getElementById("siparisGrid");

  // sonraki durum ve buton metni
  const AKIS = {
    beklemede:    { sonraki: "hazirlaniyor", etiket: "🔥 Hazırlamaya Başla", renk: "#9e9e9e", btn: "#c8884f" },
    hazirlaniyor: { sonraki: "hazir",        etiket: "✅ Hazır",            renk: "#e0a458", btn: "#4caf50" },
    hazir:        { sonraki: "teslim",       etiket: "📦 Teslim Et",         renk: "#4caf50", btn: "#1565c0" },
  };

  async function durumGuncelle(id, yeni) {
    await fetch(`/api/kitchen/${id}/update/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
      body: JSON.stringify({ status: yeni }),
    });
    yukle();
  }

  function kartHtml(s) {
    const akis = AKIS[s.status];
    const kalemler = s.kalemler
      .map((k) => `<li><span>${k.name}</span><span class="adet">×${k.qty}</span></li>`)
      .join("");
    const not = s.note ? `<div class="not">📝 ${s.note}</div>` : "";
    const odeme = `<span class="odeme-rozet ${s.is_paid ? "odendi" : "bekliyor"}">${s.is_paid ? "💳 Ödendi" : "⏳ Ödeme bekliyor"}</span>`;
    const buton = akis
      ? `<button class="aksiyon" style="background:${akis.btn};" data-id="${s.id}" data-next="${akis.sonraki}">${akis.etiket}</button>`
      : "";
    return `<div class="siparis-kart ${s.status}">
        <div class="ust">
          <span class="masa-no">Masa ${s.masa}</span>
          <span class="durum" style="background:${akis ? akis.renk : "#555"};">${s.status_label}</span>
        </div>
        <div class="kart-meta"><span class="saat">#${s.id} · ${s.created}</span>${odeme}</div>
        <ul>${kalemler}</ul>
        ${not}
        <div class="ust" style="margin-top:6px;">
          <span class="text-muted2" style="color:#b59c86;">Toplam</span>
          <b style="color:#fff;">${s.total} ₺</b>
        </div>
        ${buton}
      </div>`;
  }

  async function yukle() {
    try {
      const r = await fetch("/api/kitchen/orders/");
      const d = await r.json();
      if (!d.orders.length) {
        grid.innerHTML = '<div class="kitchen-bos">Şu an aktif sipariş yok ☕<br>Yeni siparişler otomatik görünecek.</div>';
        return;
      }
      grid.innerHTML = d.orders.map(kartHtml).join("");
    } catch (e) {
      // bağlantı hatasında mevcut görünümü koru
    }
  }

  grid.addEventListener("click", (e) => {
    const b = e.target.closest(".aksiyon");
    if (b) durumGuncelle(b.dataset.id, b.dataset.next);
  });

  yukle();
  setInterval(yukle, 4000); // 4 saniyede bir tazele
})();
