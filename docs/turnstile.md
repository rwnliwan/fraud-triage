# Sensus jalur Cloudflare Turnstile — Siskamling Digital

Sensus repo penuh atas semua jalur Turnstile (gap G7 ronde 8, 9 Nov
2026; app v6.1.6). Pertanyaan yang dijawab: di mana Turnstile aktif,
di mana tidak, dan kenapa. Satu-satunya jalur publik yang menulis ke
basis data adalah intake laporan — dan hanya jalur itulah yang
dilindungi Turnstile.

## Jalur 1 — Intake laporan warga (SATU-SATUNYA jalur tulis publik)

- **Aktif bila:** kunci `SISKAMLING_TURNSTILE_SITE_KEY` +
  `SISKAMLING_TURNSTILE_SECRET` terpasang di secrets DAN flag
  `app_config.turnstile_on = '1'`. Keduanya dicek di
  `render_lapor_tab` (`siskamling.py`, `ts_active =
  turnstile_keys_present(cfg) and state["turnstile_on"]`).
- **Mekanisme:** widget `_render_turnstile` (komponen
  `turnstile_component/`, dilayani Worker Cloudflare `siskamling-ts`)
  mengeluarkan token per pengiriman; `_turnstile_passed` memverifikasi
  token itu ke `siteverify` **pada setiap pengiriman** — tidak ada
  lagi cache sesi (ronde 8, M5: token sekali pakai tidak boleh dipakai
  ulang). Sesudah satu submit sukses, nonce widget naik sehingga
  pengiriman berikutnya mendapat token baru.
- **Bila non-aktif:** bila kunci belum terpasang atau flag mati,
  formulir tetap menerima laporan tanpa tantangan — ini mode siaga
  yang disengaja ("aktif bila kunci terpasang"): Turnstile adalah
  eskalasi saat serangan, bukan prasyarat intake. Pertahanan yang
  tetap jalan saat Turnstile mati: gerbang simpan fail-closed
  (`check_storage_gate`), batas global 300/hari, batas teks-sama 3,
  batas per-pengirim 10/hari (bila nomor diisi), cooldown 20 detik
  per sesi, batas 500 antrean.
- **Bila status intake tak terbaca:** `fetch_lapor_state` gagal →
  `intake_unknown=True` → simpan ditahan (fail-closed, ronde 8, M6);
  Turnstile tidak bisa menjadi alasan membuka simpan.

## Jalur 2 — Cek pesan saja (tanpa simpan)

- **Tidak ada Turnstile, dan memang tidak perlu.** "Cek" hanya
  menjalankan model + aturan secara lokal atas teks yang ditempel;
  tidak menulis apa pun ke basis data, tidak menambah korpus, tidak
  mengubah state. Tidak ada yang bisa dibanjiri atau diracuni lewat
  jalur ini — kecuali beban komputasi, yang ditahan oleh fakta bahwa
  model dimuat sekali dan inferensi bersifat lokal.

## Jalur 3 — Lacak laporan (`fetch_report_by_code`)

- **Tidak ada Turnstile.** Jalur ini hanya membaca status/label satu
  baris (tanpa isi pesan) dan dilindungi oleh kode lacak acak 8
  karakter (40 bit, ronde 8, M9) — tebak acak praktis tidak mungkin,
  berbeda dengan nomor urut yang dulu bisa dienumerasi. Menambah
  Turnstile di sini akan membebani warga yang sekadar mengecek
  status laporannya sendiri tanpa menambah perlindungan yang berarti.

## Jalur 4 — Galeri Modus & Analitik publik

- **Tidak ada Turnstile.** Keduanya hanya membaca (galeri: baris
  terverifikasi + `gallery_visible=1`; analitik: agregat). Tidak ada
  tulis, tidak ada state yang bisa diracuni.

## Jalur 5 — Tab Verifikasi / admin (verifikasi, tolak, hapus, tinjauan kedua, adjudikasi, flip flag)

- **Tidak ada Turnstile; dilindungi kata sandi admin** (secret
  `SISKAMLING_ADMIN_PASSWORD`). Ini jalur manusia tepercaya, bukan
  jalur publik anonim — bot tidak punya sandi admin, dan tantangan
  Turnstile tidak menambah apa pun di atas autentikasi itu.
  Termasuk di sini: membalik flag `turnstile_on` / `intake_open`
  dari tab Verifikasi, yang juga hanya bisa dilakukan sesudah
  login admin.

## Jalur 6 — Mode Batch / Analisis Tunggal (app.py)

- **Tidak ada Turnstile.** Kedua mode adalah analisis lokal atas
  teks/file yang diunggah pengguna sendiri; tidak menulis ke Turso
  Siskamling dan tidak menyentuh korpus. Tidak ada permukaan tulis
  untuk dilindungi.

## Fungsi pembantu & catatan

- `turnstile_keys_present(cfg)` — kunci terpasang atau tidak.
- `turnstile_active(cfg)` — kunci terpasang DAN flag `turnstile_on`
  = '1'. **Catatan:** helper ini saat ini tidak dipanggil dari
  `render_lapor_tab` (yang menghitung `ts_active` sebaris dari
  `fetch_lapor_state` supaya status intake + flag Turnstile dibaca
  dalam satu statement); perilakunya identik. Jangan jadikan
  ketidakpakaian ini temuan — ini duplikasi yang disengaja demi
  satu perjalanan HTTP.
- `set_turnstile_on(cfg, on)` — membalik flag (dipakai tab Verifikasi).
- `verify_turnstile(cfg, token)` — `siteverify` server-side.
  `remoteip` TIDAK dikirim: app Streamlit tidak mengekspos IP klien
  ke kode ini (ronde 8, N5); parameter itu opsional di API Cloudflare.
- Teks riwayat di `app.py` ("Baru di v5.9.1") yang menyebut token
  dipakai ulang selama sesi adalah **catatan rilis lama** — perilaku
  itu sudah dihapus ronde 8, M5. Jangan baca sebagai perilaku saat
  ini; perilaku saat ini adalah yang tertulis di bagian Jalur 1 di
  atas dan di docstring `_turnstile_passed`.

## Kesimpulan sensus

Tidak ada jalur tulis publik lain selain intake, dan intake adalah
satu-satunya jalur yang memakai Turnstile. Tidak ada jalur yang
"seharusnya terlindungi tapi tidak": semua jalur tanpa Turnstile
adalah jalur baca-saja atau jalur berotentikasi admin. Sensus ini
menutup gap G7 ronde 8.
