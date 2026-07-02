/* Manuçak — menü & sepet mantığı (oturum bazlı, JS sepeti) */
(function () {
  "use strict";

  const SEPET_KEY = "manucak_sepet";
  let sepet = JSON.parse(sessionStorage.getItem(SEPET_KEY) || "{}"); // { urunId: adet }
  const urunler = {}; // DOM'dan kurulan ürün kataloğu

  // --- yardımcılar ---
  const fmt = (n) => `${n} ₺`;
  const kaydet = () => sessionStorage.setItem(SEPET_KEY, JSON.stringify(sepet));

  function getCookie(name) {
    const m = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return m ? m.pop() : "";
  }
  function csrf() {
    const inp = document.querySelector("[name=csrfmiddlewaretoken]");
    return inp ? inp.value : getCookie("csrftoken");
  }

  // --- ürün kataloğunu DOM'dan kur ---
  document.querySelectorAll(".urun-aksiyon").forEach((el) => {
    const id = el.dataset.id;
    const btn = el.querySelector("button");
    urunler[id] = {
      name: btn.dataset.name || "",
      price: parseInt(btn.dataset.price || "0", 10),
      available: !btn.disabled,
    };
  });

  function toplamlar() {
    let adet = 0, tutar = 0;
    for (const id in sepet) {
      const u = urunler[id];
      if (!u) continue;
      adet += sepet[id];
      tutar += sepet[id] * u.price;
    }
    return { adet, tutar };
  }

  // --- ürün kartındaki +/adet kontrolü ---
  function kontrolCiz(el) {
    const id = el.dataset.id;
    const u = urunler[id];
    const qty = sepet[id] || 0;
    if (!u.available) {
      el.innerHTML = '<button class="ekle-btn" disabled>+</button>';
      return;
    }
    if (qty > 0) {
      el.innerHTML =
        `<div class="adet-kontrol">
           <button data-act="eksi" data-id="${id}">−</button>
           <span class="adet">${qty}</span>
           <button data-act="arti" data-id="${id}">+</button>
         </div>`;
    } else {
      el.innerHTML = '<button class="ekle-btn">+</button>';
    }
  }

  function barGuncelle() {
    const { adet, tutar } = toplamlar();
    document.getElementById("sepetSayac").textContent = adet;
    document.getElementById("sepetToplam").textContent = fmt(tutar);
    document.getElementById("modalToplam").textContent = fmt(tutar);
    document.getElementById("sepetBar").classList.toggle("gorunur", adet > 0);
    document.querySelectorAll(".urun-aksiyon").forEach(kontrolCiz);
  }

  function sepetCiz() {
    const cont = document.getElementById("sepetIcerik");
    const ids = Object.keys(sepet).filter((id) => sepet[id] > 0 && urunler[id]);
    if (!ids.length) {
      cont.innerHTML =
        '<div class="sepet-bos">Sepetiniz boş 🛒<br>Menüden ürün ekleyebilirsiniz.</div>';
      return;
    }
    cont.innerHTML = ids
      .map((id) => {
        const u = urunler[id];
        const qty = sepet[id];
        return `<div class="sepet-satir">
            <div class="adet-kontrol">
              <button data-act="eksi" data-id="${id}">−</button>
              <span class="adet">${qty}</span>
              <button data-act="arti" data-id="${id}">+</button>
            </div>
            <div class="ad">${u.name}</div>
            <div class="tutar">${qty * u.price} ₺</div>
          </div>`;
      })
      .join("");
  }

  function guncelle() {
    kaydet();
    barGuncelle();
    sepetCiz();
  }

  // --- tıklama olayları (delegasyon) ---
  document.addEventListener("click", (e) => {
    const act = e.target.closest("[data-act]");
    const ekle = e.target.closest(".ekle-btn:not([disabled])");
    if (act) {
      const id = act.dataset.id;
      if (act.dataset.act === "arti") sepet[id] = (sepet[id] || 0) + 1;
      else {
        sepet[id] = (sepet[id] || 0) - 1;
        if (sepet[id] <= 0) delete sepet[id];
      }
      guncelle();
    } else if (ekle) {
      const el = ekle.closest(".urun-aksiyon");
      const id = el.dataset.id;
      sepet[id] = (sepet[id] || 0) + 1;
      guncelle();
    }
  });

  // --- kategori sekmeleri ---
  const tabs = document.querySelectorAll(".kategori-tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const hedef = document.getElementById(tab.dataset.target);
      if (hedef) hedef.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
  // kaydırınca aktif sekme
  const bolumler = [...document.querySelectorAll(".kategori-baslik")];
  window.addEventListener(
    "scroll",
    () => {
      let aktif = bolumler[0];
      for (const b of bolumler) {
        if (b.getBoundingClientRect().top <= 140) aktif = b;
      }
      if (!aktif) return;
      tabs.forEach((t) =>
        t.classList.toggle("active", t.dataset.target === aktif.id)
      );
    },
    { passive: true }
  );

  // --- siparişi gönder ---
  document.getElementById("siparisVerBtn").addEventListener("click", async () => {
    const ids = Object.keys(sepet).filter((id) => sepet[id] > 0);
    if (!ids.length) {
      alert("Sepetiniz boş.");
      return;
    }
    const items = ids.map((id) => ({
      product_id: parseInt(id, 10),
      quantity: sepet[id],
    }));
    const note = document.getElementById("siparisNotu").value;
    const btn = document.getElementById("siparisVerBtn");
    btn.disabled = true;
    btn.textContent = "Gönderiliyor...";
    try {
      const r = await fetch("/api/order/create/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
        body: JSON.stringify({ items, note }),
      });
      const d = await r.json();
      if (d.ok) {
        sessionStorage.removeItem(SEPET_KEY);
        window.location.href = d.redirect;
      } else {
        alert(d.error || "Bir hata oluştu.");
        btn.disabled = false;
        btn.textContent = "Siparişi Ver →";
      }
    } catch (err) {
      alert("Bağlantı hatası. Lütfen tekrar deneyin.");
      btn.disabled = false;
      btn.textContent = "Siparişi Ver →";
    }
  });

  // başlangıç
  barGuncelle();
  sepetCiz();
})();
