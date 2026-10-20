
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# ==================================================
# 1. TFF'DEN MAÇ VERİLERİNİ ÇEK
# ==================================================

mac_listesi = []

for hafta in range(1, 39):
    url = f"https://www.tff.org/Default.aspx?hafta={hafta}&pageId=1730"

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    maclar = soup.find_all("tr", class_="haftaninMaclariTr")

    print(f"{hafta}. hafta: {len(maclar)} maç bulundu")

    for mac in maclar:
        tarih = mac.find("td", class_="haftaninMaclariTarih")
        ev = mac.find("td", class_="haftaninMaclariEv")
        skor = mac.find("td", class_="haftaninMaclariSkor")
        deplasman = mac.find("td", class_="haftaninMaclariDeplasman")

        if tarih and ev and skor and deplasman:
            mac_listesi.append({
                "Hafta": hafta,
                "Tarih": tarih.get_text(" ", strip=True),
                "Ev_Sahibi": ev.get_text(" ", strip=True),
                "Skor": skor.get_text(" ", strip=True),
                "Deplasman": deplasman.get_text(" ", strip=True)
            })

    time.sleep(1)


# ==================================================
# 2. HAM VERİYİ KAYDET
# ==================================================

df = pd.DataFrame(mac_listesi)

df.to_csv(
    "super_lig_2024_2025_ham.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\nToplam çekilen maç kaydı:", len(df))


# ==================================================
# 3. VERİNİN KOPYASINI OLUŞTUR VE TEMİZLE
# ==================================================

df_temiz = df.copy()

# Takım isimlerindeki boşlukları temizle
for sutun in ["Ev_Sahibi", "Deplasman"]:
    df_temiz[sutun] = (
        df_temiz[sutun]
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
        .str.upper()
    )

# Takım adlarını standartlaştır
takim_adi_duzeltme = {
    "ANTALYASPOR A.Ş.": "ANTALYASPOR",
    "ONVO ANTALYASPOR": "ANTALYASPOR",
    "SAMSUNSPOR A.Ş.": "SAMSUNSPOR",
    "REEDER SAMSUNSPOR": "SAMSUNSPOR"
}

for sutun in ["Ev_Sahibi", "Deplasman"]:
    df_temiz[sutun] = df_temiz[sutun].replace(takim_adi_duzeltme)


# ==================================================
# 4. SKORLARI AYIR
# ==================================================

skorlar = df_temiz["Skor"].str.extract(r"(\d+)\s*-\s*(\d+)")

df_temiz["Ev_Gol"] = pd.to_numeric(skorlar[0], errors="coerce")
df_temiz["Dep_Gol"] = pd.to_numeric(skorlar[1], errors="coerce")


# ==================================================
# 5. TARİHLERİ VE MAÇ SONUÇLARINI DÜZENLE
# ==================================================

df_temiz["Tarih"] = pd.to_datetime(
    df_temiz["Tarih"],
    format="%d.%m.%Y %H:%M",
    errors="coerce"
)

df_temiz["Toplam_Gol"] = (
    df_temiz["Ev_Gol"] + df_temiz["Dep_Gol"]
)

df_temiz["Sonuc"] = "Beraberlik"

df_temiz.loc[
    df_temiz["Ev_Gol"] > df_temiz["Dep_Gol"],
    "Sonuc"
] = "Ev sahibi galibiyeti"

df_temiz.loc[
    df_temiz["Ev_Gol"] < df_temiz["Dep_Gol"],
    "Sonuc"
] = "Deplasman galibiyeti"


# ==================================================
# 6. İŞLENMİŞ VERİYİ KAYDET
# ÖNEMLİ: Takım isimleri bu noktadan önce düzeltildi.
# ==================================================

df_temiz.to_csv(
    "super_lig_2024_2025_islenmis.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\nİşlenmiş CSV dosyası kaydedildi.")


# ==================================================
# 7. VERİ KALİTESİ KONTROLÜ
# ==================================================

print("\n--- VERİ KALİTESİ ---")

print("Toplam kayıt:", len(df_temiz))
print("Tamamen aynı kayıt:", df_temiz.duplicated().sum())

print("\nEksik değerler:")
print(df_temiz.isnull().sum())

print("\nHafta başına maç sayısı:")
print(df_temiz["Hafta"].value_counts().sort_index())

print("\nMaç sonuçlarının dağılımı:")
print(df_temiz["Sonuc"].value_counts())


# ==================================================
# 8. TAKIM SAYISI KONTROLÜ
# ==================================================

ham_takimlar = (
    set(df["Ev_Sahibi"].astype(str).str.strip().str.upper())
    | set(df["Deplasman"].astype(str).str.strip().str.upper())
)

temiz_takimlar = (
    set(df_temiz["Ev_Sahibi"])
    | set(df_temiz["Deplasman"])
)

print("\n--- TAKIM SAYISI KONTROLÜ ---")
print("Ham takım adı sayısı:", len(ham_takimlar))
print("Standartlaştırılmış takım sayısı:", len(temiz_takimlar))

print("\nStandartlaştırılmış takım isimleri:")
for takim in sorted(temiz_takimlar):
    print(takim)


# ==================================================
# 9. MAÇ VE SKOR KONTROLLERİ
# ==================================================

ayni_takim = df_temiz[
    df_temiz["Ev_Sahibi"] == df_temiz["Deplasman"]
]

print("\nKendiyle oynuyor görünen maç:", len(ayni_takim))

print(
    "Skoru okunamayan maç:",
    df_temiz[["Ev_Gol", "Dep_Gol"]].isnull().any(axis=1).sum()
)

print("Tarihi okunamayan maç:", df_temiz["Tarih"].isnull().sum())

haftalik_kayitlar = []

for hafta, grup in df_temiz.groupby("Hafta"):
    takim_listesi = list(grup["Ev_Sahibi"]) + list(grup["Deplasman"])
    tekrar = len(takim_listesi) - len(set(takim_listesi))

    haftalik_kayitlar.append({
        "Hafta": hafta,
        "Mac_Sayisi": len(grup),
        "Takim_Tekrari": tekrar
    })

print("\n--- HAFTALIK KONTROL ---")
print(pd.DataFrame(haftalik_kayitlar).to_string(index=False))


# ==================================================
# 10. TARİH KONTROLÜ
# ==================================================

print("\n--- TARİH KONTROLÜ ---")
print("İlk maç:", df_temiz["Tarih"].min())
print("Son maç:", df_temiz["Tarih"].max())

print("\nYıllara göre maç sayısı:")
print(df_temiz["Tarih"].dt.year.value_counts().sort_index())

print("\nİşlem tamamlandı.")
