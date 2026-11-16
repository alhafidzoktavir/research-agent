# Research Agent

[English](README.md)

**Asisten riset AI** berbasis command-line.
Ajukan pertanyaan, lalu agent akan merencanakan riset, mencari di web, membaca halaman yang paling relevan,
membandingkan sumber, dan menulis jawaban lengkap dengan sumbernya. Jawaban yang panjang juga disimpan sebagai laporan Markdown.

```text
$ research-agent "Bagaimana industri nikel Indonesia memengaruhi harga baterai mobil listrik?"

[search] produksi nikel Indonesia 2026 baterai EV
[fetch] https://...
...
[save_report] Report saved to reports/nikel-indonesia-baterai-ev.md
```

## Fitur

- **Agent loop otomatis.** Claude sendiri yang memutuskan apa yang dicari, halaman mana yang dibuka, dan kapan informasinya sudah cukup.
- **Web search dan web fetch** sebagai server tool. Tidak perlu API key tambahan untuk pencarian.
- **Tool lokal** (`save_report`) yang menyimpan laporan ke folder `reports/`. Nama file dibersihkan, jadi model tidak bisa menulis ke folder lain.
- **Output streaming.** Jawaban dan setiap pencarian langsung terlihat saat sedang berjalan.
- **Pertanyaan lanjutan** di mode interaktif. Konteks percakapan tetap tersimpan.
- **Prompt caching** supaya riset bertahap lebih hemat biaya.
- **Fallback otomatis** di sisi server kalau model utama menolak permintaan.
- Menjawab dalam bahasa yang Anda pakai.

## Cara kerja

Inti agent ada di [`research_agent/agent.py`](research_agent/agent.py):

1. Percakapan dikirim ke Claude secara streaming.
2. Server tool (search / fetch) dijalankan oleh Anthropic dalam giliran yang sama.
3. Kalau Claude memanggil `save_report`, input dicek dulu, lalu tool dijalankan di komputer Anda dan hasilnya dikirim balik.
4. Langkah ini diulang sampai Claude memberi jawaban akhir, dengan batas maksimal jumlah giliran.

## Mulai

**Kebutuhan:** Python 3.10+ dan [API key Anthropic](https://console.anthropic.com/).

```bash
git clone https://github.com/alhafidzoktavir/research-agent.git
cd research-agent
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -e .
```

Salin `.env.example` menjadi `.env`, lalu isi `ANTHROPIC_API_KEY`. **Jangan pernah commit file `.env`** (file ini sudah ada di `.gitignore`).

## Penggunaan

```bash
research-agent "Apa perbedaan baterai solid-state dan lithium-ion?"
research-agent                 # mode interaktif
research-agent --effort medium --max-searches 4 "..."   # lebih hemat
```

Daftar lengkap opsi ada di [README.md](README.md#usage), atau jalankan `research-agent --help`.

## Biaya

Setiap pertanyaan memakai beberapa panggilan API ditambah pemakaian web search. Turunkan `--effort`,
`--max-searches`, dan `--max-fetches` untuk menghemat biaya.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Lisensi

[MIT](LICENSE)
