// Halaman katalog: ambil data dari /api/latihan lalu tampilkan sebagai kartu.
const daftar = document.getElementById("daftar");
const info = document.getElementById("info");
const kontrol = ["level", "alat", "otot"].map((id) => document.getElementById(id));

function buatKartu(item) {
  const kartu = document.createElement("article");
  kartu.className = "kartu";
  const judul = document.createElement("h3");
  judul.textContent = item.name;               // textContent: aman dari kode berbahaya
  kartu.appendChild(judul);
  [[item.level, ""], [item.category, ""], [item.equipment, "emas"]].forEach(([teks, kelas]) => {
    if (!teks) return;
    const chip = document.createElement("span");
    chip.className = "chip " + kelas;
    chip.textContent = teks;
    kartu.appendChild(chip);
  });
  const deskripsi = document.createElement("p");
  const teks = (item.description || "Belum ada deskripsi.").trim();
  deskripsi.textContent = teks.length > 220 ? teks.slice(0, 220).trimEnd() + "..." : teks;
  kartu.appendChild(deskripsi);
  return kartu;
}

async function muat() {
  const params = new URLSearchParams({ limit: "20" });
  kontrol.forEach((el) => { if (el.value) params.set(el.id, el.value); });
  info.textContent = "Memuat...";
  try {
    const res = await fetch("/api/latihan?" + params.toString());
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Gagal memuat data.");
    daftar.replaceChildren(...data.latihan.map(buatKartu));
    info.textContent = data.count ? `Menampilkan ${data.count} latihan.` : "Tidak ada latihan yang cocok dengan filter.";
  } catch (err) {
    daftar.replaceChildren();
    info.textContent = "";
    const pesan = document.createElement("p");
    pesan.className = "galat";
    pesan.textContent = err.message;
    daftar.appendChild(pesan);
  }
}

kontrol.forEach((el) => el.addEventListener("change", muat));
document.getElementById("filter").addEventListener("submit", (e) => e.preventDefault());
muat();
