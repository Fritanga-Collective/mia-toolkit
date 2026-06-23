---
title: Cara Berkongsi Imbasan Anda pada Satu USB dengan Doktor atau Ahli Radiologi Anda
slug: share-scans-one-usb
date: 2026-07-02
summary: Panduan langkah demi langkah dalam bahasa biasa untuk meletakkan semua pengimejan anda pada satu USB yang boleh dibuka oleh doktor — apa yang patut ada padanya, cara ahli radiologi membacanya, dan apa yang patut dikatakan.
languages: [en, es, zh, ms, ta, de, fr]
status: published
tags: [guides, usb, sharing]
translation: machine
---

Jika anda mempunyai temu janji atau pendapat kedua yang akan datang, mungkin anda tertanya-tanya bagaimana untuk membawa semua pengimejan anda bersama. Mungkin anda mempunyai satu longgokan CD daripada hospital yang berlainan. Mungkin sesetengahnya tercalar, salah label, atau anda sendiri tidak pasti apa kandungannya. Berita baiknya: anda boleh meletakkan segala-galanya pada satu pemacu USB yang boleh dibuka dan disemak oleh doktor atau ahli radiologi.

Panduan ini menunjukkan kepada anda dengan tepat apa yang perlu dilakukan, apa yang patut ada pada USB itu, dan apa yang patut dikatakan apabila anda menyerahkannya. Ia ditulis untuk orang biasa, bukan pakar komputer. Lakukannya satu langkah pada satu masa.

## Mengapa Satu USB Lebih Baik Daripada Sekumpulan CD

Kebanyakan komputer baharu tidak lagi mempunyai pemacu CD. Walaupun ada, memuatkan beberapa cakera satu demi satu adalah lambat, dan cakera mudah tercalar atau rosak. Satu pemacu USB menyelesaikan semua itu. Segala-galanya berada di satu tempat, ia mudah dibawa, dan seorang doktor boleh memalamkannya dan mula bekerja dalam beberapa saat.

Tetapi ada satu masalah. Anda tidak boleh sekadar menyeret fail ke dalam USB dan mengharapkan sistem hospital memahaminya. Imej perubatan menggunakan format khas yang dipanggil DICOM, dan sistem tontonan hospital (selalunya dipanggil PACS) mengharapkan imej tersebut diatur dengan cara piawai yang khusus. Jika pengaturannya salah, sistem itu mungkin langsung tidak melihat kajian anda. (Jika istilah ini baharu bagi anda, penjelasan kami tentang [DICOM, DICOMDIR, dan PACS](/ms/blog/dicom-dicomdir-pacs-explained/) menghuraikannya dalam bahasa biasa.)

Itulah masalah yang menjadi sebab MIA Toolkit dibina.

## Apa yang Patut Ada pada USB

USB yang disediakan dengan baik mempunyai beberapa bahagian yang jelas. Berikut ialah apa setiap satunya dan mengapa ia penting.

**1. Satu arkib DICOMDIR yang mematuhi piawaian.** Bayangkan DICOMDIR sebagai isi kandungan yang menyenaraikan setiap imej dan kajian pada pemacu, dalam format tepat yang diharapkan oleh sistem perubatan. Apabila ahli radiologi memalamkan USB anda, perisian mereka mencari fail ini dahulu. Jika ia dibina dengan betul, sistem boleh mencari dan memuatkan semua kajian anda. Inilah item yang paling penting, dan membuatnya betul secara manual benar-benar sukar. MIA Toolkit membinanya untuk anda.

**2. Inventori setiap kajian dalam bahasa biasa.** Ini ialah hamparan atau senarai mudah, dalam perkataan harian, tentang apa yang ada pada pemacu: jenis imbasan (contohnya, CT dada atau MRI lutut), tarikh, dan bahagian badan. Anda dan doktor anda boleh membacanya sekali pandang, tanpa sebarang perisian khas. Ia membantu semua orang mengesahkan bahawa tiada yang tertinggal.

**3. Satu nota muka surat sehelai pilihan.** Nota ringkas boleh menjimatkan masa. Anda mungkin menulis nama dan tarikh lahir anda, sebab lawatan, dan satu baris seperti "Semua pengimejan dari 2022 hingga 2026, tiga hospital." Ringkaskan sahaja. Ini untuk dibaca oleh mata manusia, bukan komputer.

**4. Satu penonton DICOM mudah alih percuma pilihan.** Kebanyakan ahli radiologi akan mengimport DICOMDIR anda terus ke dalam sistem mereka sendiri. Tetapi kadangkala anda menyerahkan pemacu kepada doktor yang tidak mempunyai PACS penuh, atau anda mahu mampu menunjukkan imej itu sendiri. Dalam keadaan itu anda boleh menyalin penonton percuma dan mudah alih ke dalam USB supaya penerima boleh membuka imej pada hampir mana-mana komputer, tanpa perlu memasang apa-apa.

Dua penonton mudah alih percuma yang sering digunakan orang ialah **Weasis** (tersedia untuk Windows, macOS, dan Linux) dan **MicroDicom** (Windows). Kedua-duanya percuma dan berjalan tanpa pemasangan. Sentiasa semak sendiri pautan muat turun dan syarat pelesenan semasa sebelum anda bergantung kepadanya, dan ingat bahawa menambah penonton adalah pilihan. Kami tidak menyokong mana-mana produk tertentu. (Kami membandingkannya dalam panduan kami tentang [penonton DICOM percuma dan mudah alih](/ms/blog/free-portable-dicom-viewers/).)

## Cara MIA Toolkit Membina USB untuk Anda

Anda tidak perlu menghimpunkan semua ini secara manual. MIA Toolkit ialah aplikasi desktop percuma untuk macOS dan Windows yang melakukan kerja berat:

- Ia menyalin CD pengimejan hospital anda, satu demi satu, ke dalam komputer anda.
- Ia membina inventori biasa setiap kajian yang ditemuinya, supaya anda boleh melihat dengan tepat apa yang anda ada.
- Ia menghimpunkan satu arkib DICOMDIR yang mematuhi piawaian pada pemacu USB anda.
- Jika anda mempunyai **laporan radiologi atau PDF makmal** yang bertulis, ia juga boleh memasukkannya — disimpan sebagai fail yang boleh dibuka oleh doktor anda dan diserapkan ke dalam arkib — supaya imbasan anda dan laporannya bergerak bersama.
- Ia membuat **salinan yang disahkan**, memeriksa bahawa apa yang masuk ke USB sepadan dengan yang asal, supaya anda tidak tertanya-tanya sama ada pemindahan itu berjaya. Ini juga mengesan pemacu USB tiruan atau yang rosak yang sebaliknya akan merosakkan fail anda secara senyap (lebih lanjut mengenainya dalam panduan kami tentang [mengesan USB palsu atau yang rosak](/ms/blog/spotting-a-fake-or-failing-usb/)).

Hasilnya ialah satu pemacu USB kemas dengan semua kajian anda, diatur mengikut cara yang diharapkan oleh sistem perubatan, ditambah dengan inventori yang boleh anda baca sendiri dan log ringkas tentang apa yang disalin dengan tepat. Jika anda mahu, anda juga boleh meletakkan penonton mudah alih pada pemacu dalam langkah yang sama.

## Cara Ahli Radiologi Biasanya Membuka USB Anda

Berikut ialah apa yang biasanya berlaku di hujung sana, supaya anda tahu apa yang dijangkakan.

Kebanyakan sistem PACS hospital boleh mengimport DICOMDIR terus dari pemacu USB. Kakitangan memalamkan pemacu, mengarahkan sistem mereka untuk mengimport, dan kajian dimuatkan ke dalam rekod anda. Kerana DICOMDIR mengikut piawaian, sistem tahu cara membacanya.

Jika penerima tidak mempunyai PACS, atau hanya mahu melihat sekilas, mereka boleh membuka imej dalam penonton DICOM sebaliknya, seperti penonton mudah alih yang anda salin secara pilihan ke dalam pemacu. Walau apa cara sekalipun, format piawai itulah yang menjadikan imej anda boleh dibuka.

## Petua Praktikal Sebelum Temu Janji Anda

Beberapa tabiat kecil menjadikan keseluruhannya berjalan lancar:

- **Labelkan pemacu.** Sekeping pita pelekat dengan nama dan tarikh lahir anda sudah memadai. Ia mengelakkan kekeliruan di kaunter hadapan yang sibuk.
- **Simpan salinan sandaran.** Buat USB kedua, atau simpan fail yang disalin pada komputer anda. Pemacu boleh hilang atau rosak. Salinan yang disahkan MIA Toolkit memberi anda ketenangan fikiran, tetapi sandaran tetap bijak.
- **Serahkannya secara peribadi.** Imej anda adalah peribadi. Memberikan USB terus kepada kakitangan atau doktor anda memastikan anda mengawal ke mana ia pergi. Tiada keperluan untuk memuat naik apa-apa ke mana-mana.
- **Tahu apa yang patut dikatakan di kaunter hadapan.** Cuba sesuatu yang mudah: "Saya mempunyai semua pengimejan terdahulu saya pada pemacu USB ini. Ia DICOMDIR yang boleh anda import ke dalam sistem anda, dan ada senarai bercetak kajian-kajian itu." Jika mereka ada soalan, satu ayat itu biasanya menunjukkan arah yang betul.

## Nota tentang Privasi

MIA Toolkit berfungsi sepenuhnya di luar talian. Tiada akaun untuk dicipta, tiada apa-apa dimuat naik ke awan, dan tiada penjejakan. Imej anda kekal pada komputer dan pemacu USB anda, di bawah kawalan anda. Apabila anda bersedia untuk berkongsi, anda hanya menyerahkan pemacu kepada doktor anda secara peribadi. Itulah cara yang paling peribadi untuk melakukannya.

## Percuma, dan Akan Sentiasa Begitu

MIA Toolkit percuma dan sumber terbuka, dan ia akan sentiasa percuma untuk digunakan. Tiada naik taraf untuk dibeli dan tiada kos tersembunyi.

## Satu Nota Ringkas yang Penting

MIA Toolkit membantu anda mengatur dan menyampaikan imej perubatan anda sendiri. Ia bukan peranti perubatan, dan ia tidak mentafsir atau mendiagnosis apa-apa dalam imej anda. Ia bukan pengganti ahli radiologi atau doktor yang berkelayakan, iaitu orang yang betul untuk membaca imbasan anda dan menjawab soalan perubatan. Perisian ini disediakan tanpa sebarang waranti. Untuk apa-apa berkaitan kesihatan anda, sentiasa bergantung pada pasukan penjagaan anda.

## Mulakan

Apabila anda bersedia, anda boleh [muat turun MIA Toolkit secara percuma](/ms/?utm_campaign=bsh) dan menyediakan USB anda sebelum lawatan seterusnya. Untuk panduan langkah demi langkah penuh dengan tangkapan skrin setiap skrin, lihat [panduan langkah demi langkah](/ms/help.html). Jika anda mempunyai soalan tentang penggunaan aplikasi, anda boleh menghubungi kami di [support@miatools.tech](mailto:support@miatools.tech).

## Soalan Lazim

**Adakah hospital mampu membukanya?**
Dalam kebanyakan kes, ya. MIA Toolkit membina arkib DICOMDIR yang mematuhi piawaian, iaitu format yang sistem PACS hospital direka untuk mengimport. Kebanyakan sistem memuatkannya terus dari USB. Jika penerima tertentu tidak menggunakan PACS, mereka boleh membuka imej dalam penonton DICOM percuma sebaliknya. Kerana format itu mengikut piawaian, ia berfungsi merentas banyak sistem.

**Adakah saya perlu mahir dengan komputer?**
Tidak. Aplikasi ini membimbing anda menyalin CD dan membina USB, dan ia mencipta senarai kajian anda dalam bahasa biasa supaya anda boleh melihat apa yang anda ada. Jika anda boleh memalamkan CD dan pemacu USB, anda boleh melakukan ini.

**Bagaimana jika sesetengah cakera saya lama atau sukar dibaca?**
MIA Toolkit menyalin setiap cakera dan kemudian membuat salinan yang disahkan, memeriksa bahawa fail dipindahkan dengan betul. Jika cakera rosak dan sesetengah imej tidak boleh dibaca, inventori akan membantu anda melihat apa yang berjaya masuk ke pemacu dan apa yang mungkin hilang, supaya anda boleh menghubungi hospital yang menyimpan yang asal.

**Adakah maklumat saya dihantar ke mana-mana?**
Tidak. Aplikasi ini berjalan di luar talian tanpa akaun, tanpa awan, dan tanpa penjejakan. Imej anda kekal pada komputer dan pemacu USB anda. Anda berkongsinya dengan menyerahkan pemacu kepada doktor anda secara peribadi.
