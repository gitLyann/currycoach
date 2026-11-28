// Dashboard latihan pribadi. Token diambil dari ?t=... pada alamat halaman,
// lalu dikirim ke /api/progres. Grafik digambar sendiri dengan SVG (tanpa library luar).
const NS = "http://www.w3.org/2000/svg";
const $ = (id) => document.getElementById(id);

function el(nama, atribut, teks) {
  const e = document.createElementNS(NS, nama);
  Object.entries(atribut || {}).forEach(([k, v]) => e.setAttribute(k, v));
  if (teks !== undefined) e.textContent = teks;
  return e;
}

function gambarBatang(data) {
  const svg = $("grafik");
  svg.replaceChildren();
  const maks = Math.max(10, ...data.map((d) => d.menit));
  const lebarKolom = 560 / data.length, tinggi = 140, dasar = 160;
  svg.appendChild(el("line", { x1: 0, y1: dasar, x2: 560, y2: dasar, stroke: "#94a3b8" }));
  svg.appendChild(el("text", { x: 4, y: 12, "font-size": 11, fill: "#4b5563" }, maks + " mnt"));
  data.forEach((d, i) => {
    const h = Math.round((d.menit / maks) * tinggi);
    const x = i * lebarKolom + lebarKolom * 0.2;
    const batang = el("rect", { x, y: dasar - h, width: lebarKolom * 0.6, height: h, rx: 3, fill: d.menit ? "#1D428A" : "#dbe1ee" });
    batang.appendChild(el("title", {}, `${d.tanggal}: ${d.menit} menit`));
    svg.appendChild(batang);
    if (d.menit) svg.appendChild(el("text", { x: x + lebarKolom * 0.3, y: dasar - h - 4, "text-anchor": "middle", "font-size": 10, fill: "#1c2128" }, d.menit));
    if (i % 2 === 0) {
      const [, bulan, hari] = d.tanggal.split("-");
      svg.appendChild(el("text", { x: x + lebarKolom * 0.3, y: 178, "text-anchor": "middle", "font-size": 10, fill: "#4b5563" }, `${hari}/${bulan}`));
    }
  });
}

function isiKategori(peta) {
  const wadah = $("kategori");
  wadah.replaceChildren();
  const entri = Object.entries(peta);
  if (!entri.length) { wadah.textContent = "Belum ada data latihan."; return; }
  const total = entri.reduce((a, [, v]) => a + v, 0);
  entri.forEach(([nama, menit]) => {
    const baris = document.createElement("div"); baris.className = "batang";
    const label = document.createElement("span"); label.textContent = nama;
    const jalur = document.createElement("div"); jalur.className = "jalur";
    const isi = document.createElement("div"); isi.className = "isi"; isi.style.width = Math.round(menit / total * 100) + "%";
    jalur.appendChild(isi);
    const nilai = document.createElement("span"); nilai.textContent = menit + " mnt";
    baris.append(label, jalur, nilai);
    wadah.appendChild(baris);
  });
}

function isiSesi(daftar) {
  const badan = $("sesi");
  badan.replaceChildren();
  if (!daftar.length) {
    const baris = badan.insertRow(); const sel = baris.insertCell(); sel.colSpan = 5; sel.textContent = "Belum ada sesi tercatat. Ketik /catat di Telegram."; return;
  }
  daftar.forEach((s) => {
    const baris = badan.insertRow();
    [[(s.created_at || "").replace("T", " ").slice(0, 16), "Waktu"], [s.exercise_name, "Latihan"], [s.category, "Kategori"], [s.duration_min, "Menit"], [s.shots_made, "Tembakan masuk"]]
      .forEach(([nilai, label]) => { const sel = baris.insertCell(); sel.textContent = nilai; sel.dataset.label = label; });
  });
}

async function muat() {
  const token = new URLSearchParams(location.search).get("t") || "";
  if (!token) { $("status").textContent = "Tautan tidak lengkap. Ketik /dashboard di Telegram untuk mendapat tautanmu."; $("status").className = "galat"; return; }
  try {
    const res = await fetch("/api/progres?t=" + encodeURIComponent(token));
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Gagal memuat data.");
    const r = data.ringkasan_7;
    $("a-sesi").textContent = r.total_sesi; $("a-menit").textContent = r.total_menit;
    $("a-rata").textContent = r.rata_rata_menit; $("a-tembakan").textContent = r.total_tembakan;
    gambarBatang(data.harian); isiKategori(data.kategori); isiSesi(data.sesi_terbaru);
    const daftarSaran = $("saran"); daftarSaran.replaceChildren();
    data.saran.saran.forEach((teks) => { const li = document.createElement("li"); li.textContent = teks; daftarSaran.appendChild(li); });
    $("pendukung").textContent = data.saran.latihan.length ? "Latihan pendukung: " + data.saran.latihan.join(", ") + "." : "";
    $("status").hidden = true; $("isi").hidden = false;
  } catch (err) {
    $("status").textContent = err.message; $("status").className = "galat";
  }
}
muat();
