---
title: Cara Membuka CD Pengimejan Hospital Apabila Tiada Penonton (atau Ia Tidak Mahu Dibuka pada Mac)
slug: open-hospital-cd-no-viewer-mac
date: 2026-07-07
summary: CD hospital anda tidak mahu dibuka? Imej itu hampir pasti baik-baik sahaja — berikut ialah cara melihat melepasi penonton yang rosak dan membuka imbasan anda pada Mac atau PC Windows.
languages: [en, es, zh, ms, ta, de, fr]
status: published
tags: [guides, dicom, mac]
translation: machine
---

Anda pulang dari hospital dengan CD imbasan anda. Anda memasukkannya ke dalam komputer, dan... tiada apa-apa. Mungkin sebuah tetingkap muncul lalu membeku. Mungkin ia meminta anda memasang sesuatu yang tidak pernah berjaya. Mungkin anda menggunakan Mac dan cakera itu seolah-olah langsung tidak melakukan apa-apa.

Tarik nafas. Ini ialah salah satu kekecewaan yang paling biasa dihadapi orang, dan berita baiknya, imej sebenar anda hampir pasti baik-baik sahaja. Masalahnya biasanya program penonton kecil yang dibungkus pada cakera, bukan gambar itu sendiri. Mari kita teliti cara untuk sampai ke imej anda, dengan tenang dan langkah demi langkah.

## Cakera itu mempunyai dua perkara berbeza padanya

Inilah bahagian yang tiada siapa jelaskan di hospital. CD pengimejan hampir selalu mengandungi dua perkara berasingan:

1. **Sebuah program penonton** yang cuba dilancarkan oleh cakera secara automatik. Ini ialah aplikasi kecil yang terbuka (atau cuba terbuka) apabila anda memasukkan cakera.
2. **Imej perubatan sebenar anda**, disimpan sebagai fail piawai dalam format yang dipanggil DICOM.

Penonton dan imej adalah berasingan. Apabila cakera anda "tidak mahu dibuka", ia hampir selalu *penonton* yang menjadi masalah, bukan imej anda. Mungkin penonton itu dibina hanya untuk Windows dan anda menggunakan Mac. Mungkin ia lama, atau rosak, atau tetapan keselamatan komputer anda menyekatnya.

Keleganya mudah: anda langsung tidak memerlukan penonton itu. Imej anda ialah fail piawai, dan banyak program percuma dan moden boleh membukanya secara terus.

## Langkah 1: Lihat apa yang sebenarnya ada pada cakera

Daripada membiarkan cakera menjalankan programnya sendiri, mari kita buka ia seperti folder biasa dan lihat di dalamnya.

- **Pada Mac:** Masukkan cakera. Sebuah ikon untuknya sepatutnya muncul pada desktop anda atau dalam tetingkap Finder di sebelah kiri. Klik dua kali ikon itu untuk melihat fail, bukannya menjalankan sebarang tetingkap timbul yang muncul.
- **Pada Windows:** Masukkan cakera. Jika sebuah tetingkap bertanya apa yang anda ingin lakukan, pilih "Open folder to view files" (Buka folder untuk melihat fail). Jika tiada apa-apa muncul, buka **File Explorer**, kemudian klik pada pemacu cakera (selalunya berlabel D: atau E:) di sebelah kiri.

Sekarang lihat nama fail. Anda sedang mencari dua perkara:

- Sebuah fail bernama **DICOMDIR** (tanpa sambungan fail). Ini seperti isi kandungan untuk semua imej anda.
- Sebuah folder, selalunya dipanggil **DICOM** atau **IMAGES**, penuh dengan fail bernama seperti `IM_0001` atau nombor tanpa sambungan yang biasa.

Jika anda nampak semua itu, tahniah. Imej anda ada di situ dan utuh. Penonton cakera yang rosak itu tidak pernah menjadi halangan sebenar.

## Langkah 2: Buka imej anda dengan penonton percuma

Anda tidak membuka fail ini dengan mengklik dua kali padanya. Sebaliknya, anda memasang penonton percuma, kemudian halakannya ke fail **DICOMDIR** atau folder imej. Berikut ialah pilihan percuma, dikumpulkan mengikut komputer. Sila semak laman web setiap program untuk pautan muat turun dan pelesenan semasa sebelum memasang. (Untuk perbandingan yang lebih penuh, lihat panduan kami tentang [penonton DICOM percuma dan mudah alih](/ms/blog/free-portable-dicom-viewers/).)

**Jika anda mempunyai Mac:**

- **Weasis** berfungsi pada Mac, Windows, dan Linux. Ia percuma dan sumber terbuka, membuka DICOMDIR, dan juga mempunyai versi mudah alih yang boleh berjalan dari USB. Satu pilihan keseluruhan yang baik.
- **Horos** ialah khusus Mac sahaja, percuma, dan sumber terbuka. Ia perlu dipasang pada komputer anda (tiada versi mudah alih) dan membuka DICOMDIR.
- **OsiriX Lite** ialah khusus Mac sahaja dan percuma dengan beberapa had. Ia perlu dipasang pada komputer anda.

**Jika anda mempunyai PC Windows:**

- **MicroDicom** ialah khusus Windows sahaja dan percuma untuk kegunaan peribadi. Ia kira-kira pilihan yang paling mudah, mempunyai versi mudah alih, dan membuka DICOMDIR.
- **Weasis** (disebut di atas) juga berjalan pada Windows dan boleh berjalan dari USB.
- **RadiAnt** ialah program Windows yang membuka DICOMDIR. Ia berbayar, dengan percubaan percuma tersedia.

Setelah penonton dipasang, bukanya, cari pilihan menu seperti "Open" (Buka) atau "Import" (Import), dan pilih fail **DICOMDIR** daripada cakera anda. Imej anda sepatutnya dimuatkan. Itu sahaja. Penonton yang datang pada cakera itu tidak pernah penting.

## Apabila anda mempunyai longgokan cakera, perjuangan ini cepat menjemukan

Jika ini cakera anda yang satu-satunya, langkah di atas mungkin sudah cukup untuk selamanya. Tetapi ramai orang, terutamanya mereka yang menguruskan penjagaan selama berbulan atau bertahun, akhirnya mempunyai satu laci penuh dengan cakera daripada hospital yang berlainan. Setiap satu mungkin mempunyai penonton rosak yang berbeza, susun atur folder yang sedikit berbeza, dan perjuangan yang sama setiap kali. Dan seorang ahli radiologi baharu mungkin meminta anda membawa "semua pengimejan terdahulu anda".

Itulah sakit kepala tepat yang menjadi sebab **MIA Toolkit** dicipta. Ia aplikasi desktop percuma untuk Mac dan Windows yang menyalin cakera pengimejan anda ke dalam komputer anda, membina inventori mudah supaya anda boleh melihat apa yang anda ada, dan menghimpunkan segala-galanya menjadi **satu** arkib bersih yang mematuhi piawaian pada pemacu USB. Hasilnya ialah satu USB yang sistem ahli radiologi atau mana-mana penonton piawai boleh membuka, bukannya satu longgokan cakera dan perjuangan berbeza setiap kali. (Berikut ialah cara [berkongsi satu USB itu dengan doktor anda](/ms/blog/share-scans-one-usb/).)

Kerana segala-galanya disatukan menjadi satu arkib DICOMDIR yang betul, anda mengelak masalah penonton-rosak sepenuhnya pada masa hadapan.

## Privasi anda diutamakan

MIA Toolkit berjalan sepenuhnya **di luar talian**. Tiada akaun untuk dicipta, tiada awan, dan tiada penjejakan. Imej dan maklumat anda tidak pernah lepas dari komputer anda. Aplikasi ini hanya membantu anda mengatur dan membawa imbasan anda sendiri. Ia percuma untuk digunakan, dan ia akan sentiasa begitu.

## Beberapa perkataan jujur tentang apa ini

MIA Toolkit membantu anda **mengatur dan membawa imej perubatan anda sendiri**. Ia bukan peranti perubatan. Ia tidak membaca, mentafsir, atau mendiagnosis imej anda, dan ia bukan pengganti ahli radiologi atau doktor anda. Ia datang tanpa waranti. Pembacaan dan jawapan datang daripada profesional perubatan yang berkelayakan, setiap kali.

Jika anda ingin mencubanya, anda boleh [muat turunnya secara percuma](/ms/?utm_campaign=bnv) — dan terdapat [panduan langkah demi langkah](/ms/help.html) dengan tangkapan skrin. Soalan dialu-alukan di [support@miatools.tech](mailto:support@miatools.tech).

## Soalan Lazim

**Adakah selamat untuk membuka fail ini?**
Ya. Fail imej pada cakera anda ialah fail imej perubatan piawai. Membukanya dalam penonton percuma hanya memaparkan gambar, gambar yang sama yang dilihat oleh doktor anda. Perkara yang sering menimbulkan masalah ialah program kecil yang dibungkus pada cakera, bukan imej. Menggunakan penonton percuma yang dipercayai untuk membuka fail secara terus ialah pendekatan yang selamat dan biasa. Seperti biasa, muat turun mana-mana penonton dari laman web rasminya.

**Mengapa CD hospital saya tidak mahu dibuka pada Mac saya?**
Biasanya kerana penonton yang terbina dalam cakera itu dibuat hanya untuk Windows, jadi Mac tidak boleh menjalankannya. Imej anda masih ada di situ dalam format piawai. Cuma buka cakera sebagai folder dan gunakan penonton mesra Mac seperti Weasis atau Horos untuk membukanya secara terus.

**Apa itu DICOM dan apa itu fail DICOMDIR?**
DICOM ialah format piawai yang digunakan di seluruh dunia untuk imej perubatan. Fail DICOMDIR ialah sejenis isi kandungan yang menyenaraikan semua imej pada cakera anda, supaya penonton boleh memuatkannya mengikut urutan. Menghalakan penonton anda ke DICOMDIR sering kali cara yang paling mudah untuk membuka segala-galanya sekali gus.

**Adakah saya perlu membayar untuk apa-apa daripada ini?**
Tidak. Penonton percuma yang disenaraikan di atas adalah percuma untuk digunakan (beberapa daripadanya berbayar dengan percubaan percuma, yang telah kami catatkan). MIA Toolkit juga percuma, tanpa akaun dan tanpa awan. Sentiasa semak semula pelesenan semasa setiap program di laman webnya sendiri sebelum memasang.
