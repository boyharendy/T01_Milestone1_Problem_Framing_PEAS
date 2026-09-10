"""Demonstrasi Penggunaan AI Service (Dual Mode: Dengan & Tanpa API Key).

Jalankan skrip ini dengan:
    uv run python run_ai.py
"""

from src.ai_service import AIService

def main():
    print("=" * 60)
    print("DEMO 1: Uji Coba Mode Saat Ini (Mendeteksi file .env)")
    print("=" * 60)
    
    ai_default = AIService()
    status = ai_default.get_status()
    print(f"Mode Terdeteksi : {status['mode']}")
    print(f"Status API Key  : {status['api_key_status']} {status['api_key_preview']}")
    print(f"SDK Terpasang   : {status['genai_sdk_installed']}")
    
    prompt = "Bagaimana perbandingan algoritma UCS dan A* dalam optimasi rute bisnis?"
    print(f"\nPrompt: {prompt}\n")
    response = ai_default.generate(prompt)
    print("--- RESPONS SISTEM ---")
    print(response)
    print("-" * 60)

    print("\n" + "=" * 60)
    print("DEMO 2: Simulasi Rekan Tim yang Clone Repo (TANPA API KEY)")
    print("=" * 60)
    
    # Mensimulasikan kondisi kawan yang tidak memiliki API Key sama sekali
    ai_tanpa_key = AIService(api_key="")
    print(f"Mode Rekan Tim  : {ai_tanpa_key.get_status()['mode']}")
    
    # Uji analisis hasil algoritma pencarian (Search Graph)
    evaluasi = ai_tanpa_key.analyze_search(
        algorithm="A* Search",
        path=["Gudang_Pusat", "Hub_Regional_A", "Toko_Cabang_05"],
        total_cost=42.5,
        expanded_nodes=7
    )
    print("\n--- HASIL EVALUASI BISNIS TANPA API KEY ---")
    print(evaluasi)
    print("=" * 60)

if __name__ == "__main__":
    main()
