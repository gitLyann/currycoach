const chat = document.getElementById("chat");
const form = document.getElementById("form");
const input = document.getElementById("pesan");
const tombol = form.querySelector("button");

// Tambah satu gelembung. textContent dipakai (bukan innerHTML) agar aman dari kode berbahaya.
function tambah(teks, pengirim, kelasTambahan = "") {
  const baris = document.createElement("div");
  baris.className = "baris " + pengirim + " " + kelasTambahan;
  const g = document.createElement("div");
  g.className = "gelembung";
  g.textContent = teks;
  baris.appendChild(g);
  chat.appendChild(baris);
  chat.scrollTop = chat.scrollHeight;
  return baris;
}

// Kirim pesan ke Flask (/chat) lalu tampilkan balasan.
async function kirim(pesan) {
  tambah(pesan, "user");
  tombol.disabled = true;
  const sedang = tambah("CurryCoach sedang mengetik...", "bot", "mengetik");
  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: pesan }),
    });
    const data = await res.json();
    sedang.remove();
    tambah(res.ok ? data.reply : data.error, "bot");
  } catch (e) {
    sedang.remove();
    tambah("Koneksi ke server gagal. Pastikan server Flask masih berjalan.", "bot");
  } finally {
    tombol.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const pesan = input.value.trim();
  if (!pesan) return;
  input.value = "";
  kirim(pesan);
});

document.querySelectorAll(".topik button").forEach((b) =>
  b.addEventListener("click", () => kirim(b.dataset.pesan)));

// Sapaan awal diambil dari "greeting" di currycoach.json.
tambah(chat.dataset.greeting, "bot");
