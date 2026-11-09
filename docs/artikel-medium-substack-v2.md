# Artikel Medium / Substack — v2
# v2: ditambah pembaruan app v6.1 (label warga dilunakkan, kebijakan privasi UU PDP, optimasi loading) agar selaras versi terbaru di semua permukaan.
# Susulan 9 Nov 2026 (selaras v6.1.6): lacak laporan kini memakai kode acak 8 karakter (bukan nomor urut); daftar triase terurut skor tidak lagi ditampilkan di app (hanya jumlah total).
# Satu naskah, bisa tayang di Medium maupun Substack (Bahasa Indonesia).
# Sumber angka: Laporan Lengkap Proyek Edisi v3.3 (CI Wilson 95%, vonis tiga status).
# CTA tunggal sesuai Standar Publikasi v1: coba app / laporkan satu pesan.

---

## Judul (pilih satu)

Utama: **Model AI Saya Gagal Membuktikan Klaimnya Sendiri — dan Kegagalan Itu Justru Hasil Terbaiknya**

Alternatif:
- "9 dari 10" yang Tidak Pernah Terjadi: Catatan Jujur Membangun Pendeteksi Smishing Indonesia
- Gerbangnya Tetap, Modelnya Berganti: Cara Saya Menilai Model Fraud Tanpa Menipu Diri Sendiri

## Subjudul

*Membangun pendeteksi SMS penipuan (smishing) untuk Indonesia: arena model, gerbang evaluasi yang dikunci sebelum hasil diketahui, satu klaim yang gugur — dan layanan publik yang lahir dari kegagalan itu.*

---

Setiap proyek machine learning punya momen godaan. Momen saya datang dalam bentuk satu angka: **88,7%**.

Itu akurasi model saya menangkap pesan smishing berbahasa Indonesia pada set uji terakhir. Sedikit lagi menuju 90%. Kalau dibulatkan dengan "kreatif", saya bisa menulis di mana-mana: *"model ini menangkap 9 dari 10 pesan penipuan."* Kalimat yang bagus untuk portofolio. Kalimat yang akan dibaca orang sebagai janji.

Masalahnya: sebelum angka itu ada, saya sudah mengunci gerbangnya. Dan menurut gerbang itu, klaimnya **gagal**.

Tulisan ini cerita lengkapnya — termasuk bagian yang biasanya tidak dipublikasikan orang.

## Berawal dari pertanyaan sederhana

Pesan penipuan lewat SMS dan WhatsApp adalah keseharian di Indonesia: paket tertahan, akun akan diblokir, undian berhadiah, lowongan kerja palsu. Layanan resmi yang ada — cekrekening.id, aduannomor.id, IASC dari OJK — bekerja di level nomor dan rekening: memeriksa atau melaporkan nomor, lalu memblokir. Tidak ada yang menilai **isi pesannya**: tempel teksnya, dan dapatkan vonis apakah ini pola penipuan.

Saya sedang berlatih risk analytics, dan pertanyaan saya sederhana: bisakah model machine learning memilah pesan masuk seperti petugas triase — mana yang aman, mana yang perlu diperiksa manusia, mana yang harus segera dieskalasi?

Jawabannya dibangun sebagai proyek terpimpin bernama **Fraud Triage**. Yang tidak saya sangka: bagian tersulitnya bukan modelnya. Bagian tersulitnya adalah jujur soal hasilnya.

## Arena: model tidak dipilih karena terasa bagus

Kandidat model tidak dipilih berdasarkan kesan. Semuanya diadu di arena yang sama: model klasik (TF-IDF + logistic regression dan kawan-kawannya), deep learning, dan sebuah model bahasa dwibahasa yang saya fine-tune sendiri — saya memanggilnya **Laya**, DistilBERT yang dilatih pada korpus rakitan Inggris–Indonesia.

Pemenangnya: **ensemble tiga model terbaik, dikalibrasi temperaturnya**, dioperasikan dengan kebijakan dua ambang — skor sangat rendah masuk band risiko rendah, skor tinggi dieskalasi, dan di tengahnya ada antrean peninjauan manusia yang diurutkan waktu masuk, bukan skor, supaya urutan tidak membocorkan risiko sebelum manusia memutuskan (daftar terurut skor dulu ada terpisah untuk perencanaan kapasitas, tetapi sejak v6.1.5 tidak lagi ditampilkan — yang tampil hanya jumlah total laporan menunggu — supaya urutan skor tidak menjadi sinyal sebelum pelabelan). Prinsipnya saya pegang sejak awal: **mesin menyaring, manusia memutuskan.**

Pada data uji berbahasa Inggris, ensemble ini mencetak PR-AUC **0,986**. Angka yang menyenangkan. Dan angka yang tidak berarti apa-apa untuk pertanyaan sebenarnya: bagaimana kinerjanya pada pesan Indonesia?

## Gerbang yang dikunci sebelum hasil diketahui

Di sinilah proyek ini mengambil keputusan yang paling menentukan — bukan keputusan teknis, melainkan keputusan etika evaluasi.

Saya menetapkan empat gerbang **sebelum** melihat satu pun hasil pada data Indonesia:

1. Pesan sah yang dikenali benar: **≥ 85%**
2. Pesan smishing yang tertangkap: **≥ 95%**
3. Pesan smishing yang lolos sebagai "aman" (auto-close): **harus 0**
4. PR-AUC pada data uji Inggris: **≥ 0,98**

Pengujinya: **300 pesan Indonesia** (150 sah, 150 smishing) yang tidak pernah dipakai melatih model apa pun — set hakim lama yang bersih, kini pensiun sebagai hakim klaim (penilai berikutnya memakai set baru ≥600 pesan yang disegel sampai Fase 4). Gerbang tidak boleh digeser setelah hasil keluar. Kalau gagal, gagal, dan ditulis apa adanya.

Kenapa repot-repot? Karena cara paling umum "membuktikan" model fraud itu bagus adalah cara yang paling tidak jujur: bagi data secara acak, latih dan uji pada distribusi yang sama, lalu laporkan akurasi 97–99%. Angka seperti itu mengukur kemiripan data uji dengan data latih — bukan kemampuan menghadapi pesan penipuan sungguhan yang belum pernah dilihat, dalam bahasa yang berbeda, dari era yang berbeda.

## Hasilnya: gagal, dan kegagalannya terukur persis

Tahap terakhir evaluasi (disebut Tahap 2D) memberi hasil ini:

- Pesan sah: **92,7%** — gerbang 85% terlampaui.
- Pesan smishing tertangkap: **88,7%** — gerbangnya 95%. Kurang.
- Smishing yang lolos sebagai aman: **2 pesan** — gerbangnya 0. Gagal.
- PR-AUC Inggris: **0,988** — lolos.

Dua dari empat gerbang gugur. Klaim "9 dari 10" **tidak terbukti**, dan model di aplikasi tidak saya tukar dengan model yang "kelihatan lebih bagus" — karena menala model berulang-ulang ke set hakim yang sama sampai angkanya lewat gerbang, namanya bukan perbaikan. Namanya menghafal kunci jawaban.

Satu pelajaran metodologis yang saya petik belakangan — setelah laporan saya dikritik secara eksternal dan kritik itu benar: dengan 150 pesan per kelas, satu angka persen saja tidak cukup. Selang kepercayaan Wilson 95% untuk angka smishing 88,7% itu membentang dari **82,6% sampai 92,8%** — seluruhnya di bawah gerbang 95%, jadi vonisnya *gagal jelas*, bukan "gagal tipis". Sebaliknya angka sah 92,7% (selang 87,3–95,9%) berada sepenuhnya di atas gerbangnya: *lolos jelas*. Sejak itu semua vonis proyek ini memakai tiga status — **lolos jelas / tidak meyakinkan / gagal jelas** — karena vonis biner pada sampel kecil adalah cara lain untuk berbohong dengan statistik.

Laya, model andalan saya sendiri, juga kalah — dan kekalahannya dicatat dengan peringatan kejujuran: diskriminasi mentahnya dekat (PR-AUC validasi 0,982 vs 0,986), tetapi kalibrasinya buruk (ECE 0,094 vs 0,026) dan latensinya 2,81 detik per pesan, terlalu lambat untuk layanan warga. Namun Laya dinilai **tanpa** kalibrasi pasca-latih yang diterima lawannya — perlakuan yang tidak sepenuhnya setara. Vonisnya berlaku untuk Laya sebagaimana ia bisa dilatih saat itu, bukan untuk kelas modelnya. Pertandingan ulang yang adil sudah dijadwalkan, dengan syarat: perlakuan setara, set hakim baru, gerbang dikunci di muka.

## Akar masalahnya bukan model. Datanya yang tidak ada

Diagnosisnya akhirnya jelas dan struktural: di seluruh internet, korpus SMS Indonesia asli yang bisa dipakai publik hanya **satu** — 1.143 baris, tiga kelas, dari era sekitar 2012–2016. Dataset smishing Indonesia yang berlabel manusia: **nol**. Model saya belajar dari SMS Inggris era 2011, lalu diminta menilai pesan penipuan Indonesia tahun 2026. Bahwa ia mencapai 88,7% saja sebenarnya mengejutkan; bahwa ia gagal mencapai 95% adalah hal yang paling bisa diprediksi di dunia.

Tidak ada arsitektur yang memperbaiki ketiadaan data. Yang bisa memperbaiki hanya satu hal: **membangun korpusnya.**

## Maka lahirlah Siskamling Digital

Jadi proyek ini berbelok dari "membangun model" menjadi "membangun sumber datanya" — sebuah layanan publik bernama **Siskamling Digital**, hidup di aplikasi yang sama:

- **Lapor & Cek**: warga menempel pesan mencurigakan (atau mengunggah tangkapan layar; teksnya dibaca OCR dan bisa diedit dulu) dan menerima vonis bahasa awam — sangat mencurigakan (kombinasi tanda bahaya terkuat) / mencurigakan / risiko rendah menurut pemeriksa — plus kartu langkah darurat sesuai keadaan: belum mengeklik tautan, atau uang sudah terlanjur terkirim.
- **Bersih secara desain**: teks laporan otomatis dibersihkan dari nomor/email/tautan sebelum disimpan — nama bebas dan OTP masih bisa lolos, jadi ditinjau manusia sebelum tayang; pengirim hanya disimpan sebagai hash satu arah; setiap laporan punya kode lacak acak 8 karakter untuk mengecek status pemeriksaannya.
- **Label akhir selalu manusia.** Model hanya menyaring dan menyarankan. Model yang melabeli data latih masa depannya sendiri adalah lingkaran setan — dan meracuni korpus yang justru sedang dibangun untuk memperbaiki model.
- **Perlindungan dari hari pertama**: verifikasi Cloudflare Turnstile siaga (aktif bila kunci terpasang), batas laju, deteksi duplikat, dan anti-racun korpus (batasan per teks yang sama, jejak audit label, tinjauan kedua secara buta atas sampel terverifikasi) — karena korpus dari laporan publik adalah korpus yang bisa diserang.

Setiap laporan warga yang terverifikasi manusia adalah satu baris korpus smishing Indonesia berlabel — korpus yang riset saya buktikan belum ada.


**Pembaruan (Oktober 2026) — kritik yang membuat layanannya lebih jujur.** Setelah laporan proyek ini dikritik reviewer eksternal, tiga hal berubah di app v6.1. Pertama, label vonis untuk warga dilunakkan: skor model saja kini berbunyi "polanya sangat mirip penipuan" — label tegas hanya muncul bila aturan keras terpicu, karena skor bukan kepastian. Kedua, kebijakan privasi dan retensi data sesuai UU PDP kini tertulis terbuka di dalam layanan — termasuk kejujuran bahwa gambar tangkapan layar tidak disimpan sama sekali (teksnya dibaca OCR di memori, lalu gambarnya dibuang). Ketiga, vonis evaluasi di tab perjalanan riset kini memakai bingkai tiga status berbasis selang kepercayaan yang sama dengan Laporan Edisi v3.3. Bonus teknis: waktu siap aplikasi turun dari 41,6 menjadi 7,2 detik karena mesin model kini dibangun saat analisis pertama, bukan saat halaman dimuat.

## Arena terbuka: gerbangnya tetap, modelnya berganti

Rencana tahap berikutnya sudah dikunci prosedurnya sebelum datanya terkumpul: latih kandidat baru di korpus warga, nilai di **set hakim baru** dengan gerbang yang sama dan dikunci di muka. Laya boleh bertanding ulang dengan perlakuan setara. Model lain — termasuk model bahasa Indonesia yang lebih baru — juga boleh masuk.

Yang dipertahankan dari proyek ini bukan modelnya. **Standarnya.**

Karena di bidang fraud, model selalu menua: pola penipuan bermutasi, dan riset drift menunjukkan detektor yang dilatih pada data lama bisa kehilangan belasan poin recall hanya dalam beberapa tahun. Evaluasi ulang berkala dengan gerbang yang jujur bukan pengakuan kekalahan — itu satu-satunya cara klaim apa pun tetap layak dipercaya.

## Yang saya pelajari

1. **Kunci gerbang sebelum melihat hasil.** Evaluasi yang bisa digeser setelah hasil keluar bukan evaluasi; itu negosiasi.
2. **Laporkan selang kepercayaan, bukan hanya angka.** Pada sampel kecil, "88,7%" tanpa selang adalah setengah kebenaran.
3. **Hasil negatif yang rigor lebih berharga daripada hasil positif yang bocor.** Yang pertama bisa dibangun di atasnya; yang kedua hanya bisa runtuh.
4. **Kalau datanya tidak ada, bangun alat yang menciptakannya** — dengan manusia sebagai pemegang label, dan perlindungan dari upaya meracuninya sejak hari pertama.

---

**Coba layanannya**: [Siskamling Digital — Lapor & Cek Smishing](https://fraud-triage-demo.streamlit.app) — tempel satu pesan mencurigakan yang pernah Anda terima, lihat vonisnya, dan laporkan agar warga lain terlindungi.

Kode & dokumentasi lengkap: [github.com/rwnliwan/fraud-triage](https://github.com/rwnliwan/fraud-triage) · Model: [Hugging Face — rwnliwan/fraud-triage-smishing](https://huggingface.co/rwnliwan/fraud-triage-smishing) · Laporan lengkap proyek (PDF, Bahasa Indonesia): tersedia di repo.

*Septian Panjaya — [LinkedIn](https://www.linkedin.com/in/septian-panjaya). Proyek pembelajaran terpimpin di bidang risk analytics; dibangun dengan bantuan AI sebagai pair engineer — arsitektur, gerbang evaluasi, dan setiap keputusan akhir dipegang dan diverifikasi oleh penulis.*
