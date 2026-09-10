"""Module AI Service (Dual-Mode: Cloud Gemini + Local/Offline Fallback).

Modul ini dirancang agar:
1. Pengguna dengan API Key dapat menggunakan Google Gemini Cloud (gemini-2.5-flash).
2. Pengguna tanpa API Key (rekan tim yang clone repo atau memakai model lokal)
   tetap bisa menjalankan sistem tanpa error (graceful fallback).
"""

import os
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Muat file .env jika ada
load_dotenv()

# Coba import Google GenAI SDK (jika terinstall di env)
try:
    from google import genai
    from google.genai import errors as genai_errors
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class AIService:
    """Service AI fleksibel dengan dukungan Gemini API dan Offline/Local Fallback."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        # Ambil API key dari parameter atau environment variable
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "").strip()
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        self.client = None
        self.mode = "OFFLINE_HEURISTIC"  # Default fallback
        self._init_client()

    def _init_client(self):
        """Inisialisasi klien AI berdasarkan ketersediaan key dan library."""
        # 1. Cek apakah Gemini Cloud bisa digunakan
        if GENAI_AVAILABLE and self.api_key and not self.api_key.startswith("AQ."):
            try:
                self.client = genai.Client(api_key=self.api_key)
                self.mode = "GEMINI_ONLINE"
                return
            except Exception as e:
                print(f"[AI Notice] Gagal inisialisasi Gemini Client: {e}")

        # 2. Cek apakah ada model lokal Ollama berjalan di komputer (biasanya diinstal global)
        if self._check_ollama_alive():
            self.mode = "OLLAMA_LOCAL"
            return

        # 3. Mode Fallback (Bebas error, tidak butuh internet / API key)
        self.mode = "OFFLINE_HEURISTIC"

    def _check_ollama_alive(self) -> bool:
        """Cek apakah server model lokal Ollama (port 11434) aktif."""
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=0.8) as response:
                return response.status == 200
        except Exception:
            return False

    def generate(self, prompt: str, system_instruction: str = "") -> str:
        """Menghasilkan teks respons AI secara adaptif sesuai mode yang aktif."""
        # Prioritas 1: Google Gemini Online
        if self.mode == "GEMINI_ONLINE" and self.client:
            try:
                full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=full_prompt
                )
                return response.text
            except Exception as e:
                print(f"\n[AI Warning] Panggilan Gemini Online gagal ({e}). Beralih otomatis ke Fallback...")

        # Prioritas 2: Ollama Local (Jika teman menginstall model lokal di sistem global)
        if self.mode == "OLLAMA_LOCAL" or self._check_ollama_alive():
            ollama_res = self._call_ollama(prompt, system_instruction)
            if ollama_res:
                return ollama_res

        # Prioritas 3: Heuristic Fallback (Pasti berhasil, zero-dependency)
        return self._fallback_response(prompt)

    def _call_ollama(self, prompt: str, system_instruction: str = "") -> Optional[str]:
        """Panggil model lokal Ollama via REST API bawaan."""
        try:
            payload = {
                "model": "gemma2" if "gemma" in os.getenv("OLLAMA_MODEL", "") else "llama3",
                "prompt": f"{system_instruction}\n{prompt}" if system_instruction else prompt,
                "stream": False
            }
            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data.get("response", "")
        except Exception:
            return None

    def _fallback_response(self, prompt: str) -> str:
        """Respons cerdas berbasis aturan bawaan ketika tidak ada API Key / Model Luar."""
        prompt_lower = prompt.lower()
        
        # Template tanggapan pintar untuk topik Milestone 1 (Search, UCS, A*, PEAS)
        if "ucs" in prompt_lower or "uniform cost search" in prompt_lower:
            return (
                "[MODE LOKAL/FALLBACK]: Analisis Uniform Cost Search (UCS)\n"
                "• Sifat: Optimal dan Lengkap (Complete) pada graf berbobot positif ($c(s, a) \ge \epsilon > 0$).\n"
                "• Mekanisme: Mengekspansi simpul $n$ dengan akumulasi biaya $g(n)$ terkecil menggunakan `heapq`.\n"
                "• Rekomendasi Milestone 1: Cocok sebagai *baseline comparison* terhadap A*."
            )
        elif "a*" in prompt_lower or "astar" in prompt_lower or "heuristic" in prompt_lower:
            return (
                "[MODE LOKAL/FALLBACK]: Analisis A* Search & Heuristik\n"
                "• Fungsi Evaluasi: $f(n) = g(n) + h(n)$.\n"
                "• Syarat Keoptimalan: $h(n)$ wajib *admissible* ($h(n) \le h^*(n)$) untuk tree search dan *consistent* untuk graph search.\n"
                "• Rekomendasi Milestone 1: Gunakan fungsi heuristik berbasis jarak Euclidean / Manhattan atau estimasi biaya optimistik."
            )
        elif "peas" in prompt_lower:
            return (
                "[MODE LOKAL/FALLBACK]: Analisis Formulasi PEAS\n"
                "• Performance Measure: Metrik keberhasilan bisnis (misal: meminimalkan total biaya atau waktu pengiriman).\n"
                "• Environment: Ruang operasional (Fully/Partially Observable, Deterministic, Static/Dynamic).\n"
                "• Actuators: Aksi pengambilan keputusan atau navigasi rute.\n"
                "• Sensors: Input data simpul lokasi, data lalu lintas, atau bobot biaya operasional."
            )
        else:
            return (
                f"[MODE LOKAL/FALLBACK]: Sistem menerima prompt:\n\"{prompt[:120]}...\"\n\n"
                "Catatan: Untuk mendapatkan jawaban penuh dari Gemini AI Cloud, pastikan Anda:\n"
                "1. Mendapatkan API Key resmi (diawali 'AIzaSy...') di https://aistudio.google.com/apikey\n"
                "2. Memasukkannya ke file `.env` sebagai: GEMINI_API_KEY=\"AIzaSy...\""
            )

    def analyze_search(self, algorithm: str, path: list, total_cost: float, expanded_nodes: int) -> str:
        """Fungsi pembantu khusus untuk menganalisis hasil pencarian graf bisnis."""
        prompt = (
            f"Sebagai konsultan AI Bisnis, analisis hasil pencarian berikut:\n"
            f"- Algoritma: {algorithm}\n"
            f"- Jalur Solusi: {' -> '.join(map(str, path))}\n"
            f"- Total Biaya: {total_cost}\n"
            f"- Jumlah Simpul Diekspansi: {expanded_nodes}\n"
            f"Berikan evaluasi efisiensi operasional bisnis dalam 3 poin singkat."
        )
        return self.generate(prompt=prompt, system_instruction="Anda adalah pakar optimasi sistem pencarian rute cerdas.")

    def get_status(self) -> Dict[str, Any]:
        """Menampilkan status konfigurasi AI saat ini."""
        key_masked = f"{self.api_key[:6]}...{self.api_key[-4:]}" if len(self.api_key) > 10 else "(Kosong/Tidak Ada)"
        return {
            "mode": self.mode,
            "api_key_status": "Terpasang" if self.api_key else "Tidak Ada",
            "api_key_preview": key_masked,
            "model_name": self.model_name,
            "genai_sdk_installed": GENAI_AVAILABLE
        }
