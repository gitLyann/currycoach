// Halaman Kelola Data (admin): CRUD katalog latihan dan pola tambahan chatbot.
// Semua permintaan membawa header X-Admin-Key. Data ditulis ke DOM dengan textContent.
const $ = (id) => document.getElementById(id);
const TEMA = document.body.dataset.tema;
const PER_HALAMAN = 10;
let offset = 0, total = 0, tagIntent = [];

function status(id, teks, ok = false) {
  const e = $(id); e.textContent = teks; e.className = "status" + (ok ? " ok" : " galat");
}

async function api(url, metode = "GET", badan) {
  const opsi = { method: metode, headers: { "X-Admin-Key": $("kunci").value } };
  if (badan !== undefined) { opsi.headers["Content-Type"] = "application/json"; opsi.body = JSON.stringify(badan); }
  const res = await fetch(url, opsi);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(data.detail) ? " " + data.detail.join(" ") : "";
    throw new Error((data.error || "Permintaan gagal.") + detail);
  }
  return data;
}

function tombol(teks, kelas, aksi) {
  const b = document.createElement("button"); b.type = "button"; b.textContent = teks;
  if (kelas) b.className = kelas; b.addEventListener("click", aksi); return b;
}
function sel(baris, teks, label) { const c = baris.insertCell(); c.textContent = teks; c.dataset.label = label; return c; }

// ---------------- Pola tambahan ----------------
async function muatPola() {
  const [pola, stat] = await Promise.all([api("/api/admin/pola"), api(`/api/stats/${TEMA}`)]);
  tagIntent = pola.tag;
  const badan = $("daftar-pola"); badan.replaceChildren();
  pola.pola.forEach((p) => {
    const b = badan.insertRow(); sel(b, p.tag, "Intent"); sel(b, p.pattern, "Pola");
    sel(b, "", "Aksi").append(tombol("Hapus", "bahaya", async () => {
      try { await api(`/api/admin/pola/${p.id}`, "DELETE"); status("status-pola", "Pola dihapus.", true); await muatPola(); }
      catch (e) { status("status-pola", e.message); } }));
  });
  if (!pola.pola.length) { const b = badan.insertRow(); const c = b.insertCell(); c.colSpan = 3; c.textContent = "Belum ada pola tambahan."; }

  const tak = $("tak-dikenal"); tak.replaceChildren();
  (stat.unrecognized_questions || []).forEach((q) => {
    const b = tak.insertRow(); sel(b, q.text, "Pertanyaan"); sel(b, q.total, "Frekuensi");
    const pilih = document.createElement("select"); pilih.setAttribute("aria-label", "Intent untuk: " + q.text);
    tagIntent.forEach((t) => { const o = document.createElement("option"); o.value = t; o.textContent = t; pilih.appendChild(o); });
    const wadah = sel(b, "", "Intent"); wadah.append(pilih, tombol("Tambahkan", "", async () => {
      try { await api("/api/admin/pola", "POST", { tag: pilih.value, pattern: q.text });
            status("status-pola", `Pola ditambahkan ke ${pilih.value}.`, true); await muatPola(); }
      catch (e) { status("status-pola", e.message); } }));
  });
  if (!(stat.unrecognized_questions || []).length) { const b = tak.insertRow(); const c = b.insertCell(); c.colSpan = 3; c.textContent = "Belum ada pertanyaan yang tidak dikenali."; }
}

$("form-pola").addEventListener("submit", async (e) => {
  e.preventDefault();
  try { await api("/api/admin/pola", "POST", { tag: $("pola-tag").value, pattern: $("pola-teks").value });
        $("pola-teks").value = ""; status("status-pola", "Pola ditambahkan.", true); await muatPola(); }
  catch (err) { status("status-pola", err.message); }
});

// ---------------- Katalog latihan ----------------
function isiForm(item) {
  $("l-id").value = item ? item.id : "";
  ["name", "category", "equipment", "muscles", "description"].forEach((k) => { $("l-" + k).value = item ? (item[k] || "") : ""; });
  $("l-level").value = item && item.level ? item.level : "pemula";
  $("l-simpan").textContent = item ? "Simpan perubahan" : "Tambah latihan";
  $("l-batal").hidden = !item;
}

async function muatLatihan() {
  const q = encodeURIComponent($("cari").value.trim());
  const data = await api(`/api/admin/latihan?limit=${PER_HALAMAN}&offset=${offset}&q=${q}`);
  total = data.total;
  const badan = $("daftar-latihan"); badan.replaceChildren();
  data.items.forEach((item) => {
    const b = badan.insertRow();
    sel(b, item.name, "Nama"); sel(b, item.category, "Kategori"); sel(b, item.level, "Level");
    sel(b, item.equipment, "Alat"); sel(b, item.source, "Sumber");
    sel(b, "", "Aksi").append(
      tombol("Ubah", "sekunder", () => { isiForm(item); window.scrollTo({ top: $("form-latihan").offsetTop - 80, behavior: "smooth" }); }),
      tombol("Hapus", "bahaya", async () => {
        if (!confirm(`Hapus latihan "${item.name}"?`)) return;
        try { await api(`/api/admin/latihan/${item.id}`, "DELETE"); status("status-latihan", "Latihan dihapus.", true); await muatLatihan(); }
        catch (e) { status("status-latihan", e.message); } }));
  });
  if (!data.items.length) { const b = badan.insertRow(); const c = b.insertCell(); c.colSpan = 6; c.textContent = "Tidak ada latihan."; }
  const halaman = Math.floor(offset / PER_HALAMAN) + 1, maks = Math.max(1, Math.ceil(total / PER_HALAMAN));
  $("halaman").textContent = `Halaman ${halaman} / ${maks} (${total} latihan)`;
  $("sebelumnya").disabled = offset <= 0; $("berikutnya").disabled = offset + PER_HALAMAN >= total;
}

$("form-latihan").addEventListener("submit", async (e) => {
  e.preventDefault();
  const badan = { name: $("l-name").value, category: $("l-category").value, level: $("l-level").value,
                  equipment: $("l-equipment").value, muscles: $("l-muscles").value, description: $("l-description").value };
  const id = $("l-id").value;
  try {
    if (id) await api(`/api/admin/latihan/${id}`, "PUT", badan); else await api("/api/admin/latihan", "POST", badan);
    status("status-latihan", id ? "Perubahan disimpan." : "Latihan ditambahkan.", true);
    isiForm(null); offset = 0; await muatLatihan();
  } catch (err) { status("status-latihan", err.message); }
});
$("l-batal").addEventListener("click", () => isiForm(null));
$("sebelumnya").addEventListener("click", () => { offset = Math.max(0, offset - PER_HALAMAN); muatLatihan(); });
$("berikutnya").addEventListener("click", () => { offset += PER_HALAMAN; muatLatihan(); });
let tunda; $("cari").addEventListener("input", () => { clearTimeout(tunda); tunda = setTimeout(() => { offset = 0; muatLatihan(); }, 300); });

$("muat").addEventListener("click", async () => {
  try {
    await Promise.all([muatPola(), muatLatihan()]);
    $("bagian-pola").hidden = false; $("bagian-latihan").hidden = false;
    status("status-umum", "Data dimuat.", true);
  } catch (e) { status("status-umum", e.message); }
});
