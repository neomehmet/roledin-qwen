"""
couplateV2.py - GIS Spatial Join & Lookup Dictionary Oluşturucu (V2)

couplate.py'nin temizlenmiş ve düzeltilmiş hali.
Bağlantı-Hücre ilişkisi artık bara->hücre üzerinden kurulur (bara touches baglanti).
Tüm lookup dictionary'leri bu yeni yapıya uygun olarak güncellendi.

Çıktılar:
  - 6 adet Excel lookup dosyası (bara_, ayirici_, kesici_, hucre_, merkez_, baglanti_)
  - bara_2_baglanti.xlsx (bara-baglanti spatial join sonucu)
  - ayirici_anahtar_status.xlsx (ayırıcı anahtarlama durumları)
  - baglanti_processed.xlsx (işlenmiş bağlantı verisi)
"""

from geopandas import read_file
import geopandas as gpd
import pandas as pd
import networkx as nx
from shapely import get_point
from shapely.geometry import Point
import os

OUTPUT_DIR = "look-ups"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# =============================================================================
# 1. GIS VERİLERİNİ OKU
# =============================================================================
MERKEZ_PATH = r"GIS/LGC_MERKEZ.shp"
HAT_PATH = r"GIS/H_ENERJI_NAKIL_HATTI.shp"
HUCRE_PATH = r"GIS/T_HUCRE.shp"
BARA_PATH = r"GIS/T_OG_BARA.shp"
KESICI_PATH = r"GIS/T_OG_KESICI.shp"
AYIRICI_PATH = r"GIS/T_OG_AYIRICI.shp"
T_OG_KABLO_BAGLANTISI_PATH = r"GIS/T_OG_KABLO_BAGLANTISI.shp"

print("GIS verileri okunuyor...")

merkez_df = read_file(MERKEZ_PATH)  # polygon (çokgen geometri)
merkez_df["MERKEZ_ABB_INT_ID"] = merkez_df.ABB_INT_ID
merkez_df["MERKEZ_GEOMETRY"] = merkez_df.geometry

hucre_df = read_file(HUCRE_PATH)  # polygon (çokgen geometri)
hucre_df = hucre_df[hucre_df["GERILIM"] == "34.5 kV"]
hucre_df["HUCRE_ABB_INT_ID"] = hucre_df.ABB_INT_ID
hucre_df["HUCRE_GEOMETRY"] = hucre_df.geometry

# hucre_id -> alttip (hücre tipi adı) sözlüğü
hucre_name_dict = {int(row.ABB_INT_ID): row.ALTTIP for _, row in hucre_df.iterrows()}

# hucre_id -> coupling bay mi? (1: bağlama/kuplaj hücresi, 0: değil)
coupling_bays = {}
for _, row in hucre_df.iterrows():
    alttip = str(row.ALTTIP).upper()
    if "BAGLAMA" in alttip or "KUBLAJ" in alttip:
        coupling_bays[int(row.ABB_INT_ID)] = 1
    else:
        coupling_bays[int(row.ABB_INT_ID)] = 0

bara_df = read_file(BARA_PATH)  # line (çizgi şeklinde bir obje geometri)
bara_df = bara_df[bara_df["GERILIM"] == "34.5 kV"]
bara_df["BARA_ABB_INT_ID"] = bara_df.ABB_INT_ID
bara_df["BARA_GEOMETRY"] = bara_df.geometry

hat_df = read_file(HAT_PATH)  # line (çizgi şeklinde bir obje geometri)
hat_df = hat_df[hat_df["GERILIM"] == "34.5 kV"]
hat_df["HAT_ABB_INT_ID"] = hat_df.ABB_INT_ID
hat_df["HAT_GEOMETRY"] = hat_df.geometry

# hat_id -> uzunluk (metre) sözlüğü
hat_mesafe_dict = {
    int(row.ABB_INT_ID): int(row.UZUNLUK) for _, row in hat_df.iterrows()
}

kesici_df = read_file(KESICI_PATH)  # point (nokta geometri)
kesici_df = kesici_df[kesici_df["GERILIM"] == "34.5 kV"]
kesici_df["KESICI_ABB_INT_ID"] = kesici_df.ABB_INT_ID
kesici_df["KESICI_GEOMETRY"] = kesici_df.geometry

ayirici_df = read_file(AYIRICI_PATH)  # point (nokta geometri)
ayirici_df = ayirici_df[
    ~ayirici_df["ALTTIP"].str.contains("TOPRAKLI", case=False, na=False)
]
# drop rows who doesnt have 34.5kV value in GERILIM column
ayirici_df = ayirici_df[ayirici_df["GERILIM"] == "34.5 kV"]
ayirici_df["AYIRICI_ABB_INT_ID"] = ayirici_df.ABB_INT_ID
ayirici_df["AYIRICI_GEOMETRY"] = ayirici_df.geometry
ayirici_df.to_excel(os.path.join(OUTPUT_DIR, "ayirici-shp.xlsx"), index=False)

baglanti_df = read_file(T_OG_KABLO_BAGLANTISI_PATH)  # point (nokta geometri)
baglanti_df = baglanti_df[baglanti_df["GERILIM"] == "34.5 kV"]
baglanti_df["BAGLANTI_ABB_INT_ID"] = baglanti_df.ABB_INT_ID
baglanti_df["BAGLANTI_GEOMETRY"] = baglanti_df.geometry

print("GIS verileri okundu.")


# =============================================================================
# edge exceli ve, point exceli oluşturma
# =============================================================================
PRECISION = 8
for gdf in [hat_df, bara_df, baglanti_df]:
    if (gdf is None) or (gdf.empty):
        continue
    start_series = gdf.geometry.apply(lambda g: get_point(g, 0) if g is not None and not g.is_empty else None)
    end_series = gdf.geometry.apply(lambda g: get_point(g, -1) if g is not None and not g.is_empty else None)

    gdf["START_POINT"] = start_series.apply(
        lambda p: (
            (round(p.x, PRECISION), round(p.y, PRECISION)) if p is not None and not p.is_empty else None
        )
    )
    gdf["END_POINT"] = end_series.apply(
        lambda p: (
            (round(p.x, PRECISION), round(p.y, PRECISION)) if p is not None and not p.is_empty else None
        )
    )

for gdf in [kesici_df, ayirici_df]:
    if (gdf is None) or (gdf.empty):
        continue
    gdf["geometry"] = gdf.geometry.apply(
        lambda p: (
            Point(round(p.x, PRECISION), round(p.y, PRECISION)) if p is not None and not p.is_empty else p
        )
    )
    gdf[["START_POINT", "END_POINT"]] = None


def create_edge_data(gdf, type_name):
    if gdf is None or gdf.empty:
        return pd.DataFrame()
    return pd.DataFrame(
        {
            "EDGE_ID": gdf["ABB_INT_ID"],
            "NODE_1": gdf["START_POINT"],
            "NODE_2": gdf["END_POINT"],
            "TYPE": type_name,
        }
    )


edge_df = pd.concat(
    [
        create_edge_data(hat_df, "HAT"),
        create_edge_data(bara_df, "BARA"),
        create_edge_data(baglanti_df, "BAGLANTI"),
    ],
    ignore_index=True,
)
edge_df.to_excel(os.path.join(OUTPUT_DIR, "edge_df.xlsx"), index=False)

# Node çifti -> Edge ID eşlemesi (her iki yön için)
start_end_2_edge_id = dict()
for _, row in edge_df.iterrows():
    start_end_2_edge_id[(row["NODE_1"], row["NODE_2"])] = row["EDGE_ID"]
    start_end_2_edge_id[(row["NODE_2"], row["NODE_1"])] = row["EDGE_ID"]

all_segments_df = pd.concat(
    [
        hat_df[["START_POINT", "END_POINT", "ABB_INT_ID"]],
        bara_df[["START_POINT", "END_POINT", "ABB_INT_ID"]],
        baglanti_df[["START_POINT", "END_POINT", "ABB_INT_ID"]],
    ]
).reset_index(drop=True)
all_segments_df.to_excel(os.path.join(OUTPUT_DIR, "all_segment.xlsx"), index=False)

all_points = pd.concat([edge_df["NODE_1"], edge_df["NODE_2"]]).unique()
point_df = pd.DataFrame({"NODE_ID": all_points})
point_df.to_excel(os.path.join(OUTPUT_DIR, "node_coords_to_make_graph_node.xlsx"), index=False)
point_df.to_excel(os.path.join(OUTPUT_DIR, "point_df.xlsx"), index=False)


# =============================================================================
# 2. SPATIAL JOIN İŞLEMLERİ (ön işleme)
# =============================================================================
print("Spatial join işlemleri yapılıyor...")

# --- Hücre <-> Merkez ---
birlesik_df_hucre_merkez = gpd.sjoin(
    hucre_df, merkez_df, how="left", predicate="within"
)
birlesik_df_hucre_merkez = birlesik_df_hucre_merkez[
    ~birlesik_df_hucre_merkez.index.duplicated(keep="first")
]
birlesik_df_hucre_merkez["geometry"] = hucre_df["geometry"]
hucre_df_processed = hucre_df.copy()
hucre_df_processed["MERKEZ_ABB_INT_ID"] = birlesik_df_hucre_merkez["MERKEZ_ABB_INT_ID"]
hucre_df_processed["MERKEZ_GEOMETRY"] = birlesik_df_hucre_merkez["MERKEZ_GEOMETRY"]

# --- Bağlantı <-> Merkez ---
baglanti_df_baglanti_merkez = gpd.sjoin(
    baglanti_df, merkez_df, how="left", predicate="intersects"
)
baglanti_df_baglanti_merkez = baglanti_df_baglanti_merkez[
    ~baglanti_df_baglanti_merkez.index.duplicated(keep="first")
]
baglanti_df_processed = baglanti_df.copy()
baglanti_df_processed["MERKEZ_ABB_INT_ID"] = baglanti_df_baglanti_merkez[
    "MERKEZ_ABB_INT_ID"
]
baglanti_df_processed["MERKEZ_GEOMETRY"] = baglanti_df_baglanti_merkez[
    "MERKEZ_GEOMETRY"
]

# --- Bağlantı <-> Hücre (bara üzerinden) ---
# Önce bara->hücre ilişkisini kur
temp_bara_2_hucre_df = gpd.sjoin(bara_df, hucre_df, how="left", predicate="intersects")
temp_bara_2_hucre_df = temp_bara_2_hucre_df.dropna(subset=["ABB_INT_ID_right"])

# Sonra bara->baglanti ilişkisini bul (touches = baraya dokunan bağlantılar)
temp_bara_2_baglanti_df = gpd.sjoin(
    bara_df, baglanti_df, how="inner", predicate="touches"
)
temp_bara_2_baglanti_df[["BARA_ABB_INT_ID", "BAGLANTI_ABB_INT_ID"]].to_excel(
    os.path.join(OUTPUT_DIR, "bara_2_baglanti.xlsx"), index=False
)

# Bara -> Ayırıcı spatial join (ayırıcı noktası baranın üzerinde mi?)
# Floating-point precision sorununu aşmak için bara geometrisi küçük bir
# tolerance buffer'ı ile genişletiliyor (~0.1m). Bu sayede koordinat tam
# eşleşmese bile ayırıcı buffered bara alanına düşüyor.
_AYIRICI_BARA_TOL = 1e-6  # derece cinsinden ~0.1m tolerans
_bara_df_buf = bara_df.copy()
_bara_df_buf["geometry"] = _bara_df_buf.geometry.buffer(_AYIRICI_BARA_TOL)
temp_bara_2_ayirici_df = gpd.sjoin(
    _bara_df_buf, ayirici_df, how="inner", predicate="intersects"
)
# Spatial join'den ayirici_id -> [bara_id, ...] eşlemesi (max 2 bara beklenir)
_ayirici_2_bara_spatial = {}
for _, _srow in temp_bara_2_ayirici_df.iterrows():
    _aid = int(_srow["AYIRICI_ABB_INT_ID"])
    _bid = int(_srow["BARA_ABB_INT_ID"])
    if _aid not in _ayirici_2_bara_spatial:
        _ayirici_2_bara_spatial[_aid] = []
    if _bid not in _ayirici_2_bara_spatial[_aid]:
        _ayirici_2_bara_spatial[_aid].append(_bid)

# Bağlantı'ya hücre ID ata (bara üzerinden)
baglanti_df_processed["HUCRE_ABB_INT_ID"] = None
baglanti_df_processed["BAGLANTI_ABB_INT_ID"] = baglanti_df_processed["ABB_INT_ID"]
for _, row in temp_bara_2_baglanti_df.iterrows():
    baglanti_temp_id = row["BAGLANTI_ABB_INT_ID"]
    bara_temp_id = row["BARA_ABB_INT_ID"]
    hucre_series = temp_bara_2_hucre_df[
        temp_bara_2_hucre_df["BARA_ABB_INT_ID"] == bara_temp_id
    ]["HUCRE_ABB_INT_ID"]
    if hucre_series.empty:
        continue
    hucre_id = int(hucre_series.values[0])
    baglanti_df_processed.loc[
        baglanti_df_processed["ABB_INT_ID"] == baglanti_temp_id,
        "HUCRE_ABB_INT_ID",
    ] = hucre_id

baglanti_df_processed.to_excel(os.path.join(OUTPUT_DIR, "baglanti_processed.xlsx"))
print("  -> baglanti_processed.xlsx kaydedildi")

# --- Kesici <-> Hücre/Merkez ---
birlesik_df_kesici_hucre = gpd.sjoin(
    kesici_df, hucre_df, how="left", predicate="within"
)
birlesik_df_kesici_hucre = birlesik_df_kesici_hucre[
    ~birlesik_df_kesici_hucre.index.duplicated(keep="first")
]
birlesik_df_kesici_hucre["geometry"] = kesici_df["geometry"]
birlesik_df_kesici_merkez = gpd.sjoin(
    kesici_df, merkez_df, how="left", predicate="within"
)
birlesik_df_kesici_merkez = birlesik_df_kesici_merkez[
    ~birlesik_df_kesici_merkez.index.duplicated(keep="first")
]
kesici_df_processed = kesici_df.copy()
kesici_df_processed["HUCRE_ABB_INT_ID"] = birlesik_df_kesici_hucre["HUCRE_ABB_INT_ID"]
kesici_df_processed["HUCRE_GEOMETRY"] = birlesik_df_kesici_hucre["HUCRE_GEOMETRY"]
kesici_df_processed["MERKEZ_ABB_INT_ID"] = birlesik_df_kesici_merkez[
    "MERKEZ_ABB_INT_ID"
]
kesici_df_processed["MERKEZ_GEOMETRY"] = birlesik_df_kesici_merkez["MERKEZ_GEOMETRY"]

# --- Ayırıcı <-> Hücre/Merkez ---
birlesik_df_ayirici_hucre = gpd.sjoin(
    ayirici_df, hucre_df, how="left", predicate="within"
)
birlesik_df_ayirici_hucre = birlesik_df_ayirici_hucre[
    ~birlesik_df_ayirici_hucre.index.duplicated(keep="first")
]
birlesik_df_ayirici_hucre["geometry"] = ayirici_df["geometry"]
birlesik_df_ayirici_merkez = gpd.sjoin(
    ayirici_df, merkez_df, how="left", predicate="within"
)
birlesik_df_ayirici_merkez = birlesik_df_ayirici_merkez[
    ~birlesik_df_ayirici_merkez.index.duplicated(keep="first")
]
ayirici_df_processed = ayirici_df.copy()
ayirici_df_processed["HUCRE_ABB_INT_ID"] = birlesik_df_ayirici_hucre["HUCRE_ABB_INT_ID"]
ayirici_df_processed["HUCRE_GEOMETRY"] = birlesik_df_ayirici_hucre["HUCRE_GEOMETRY"]
ayirici_df_processed["MERKEZ_ABB_INT_ID"] = birlesik_df_ayirici_merkez[
    "MERKEZ_ABB_INT_ID"
]
ayirici_df_processed["MERKEZ_GEOMETRY"] = birlesik_df_ayirici_merkez["MERKEZ_GEOMETRY"]

# Ayırıcı anahtarlama durumları Excel'e (test için varsayılan değerler)
# Gerçek GIS verisinde ANAHTARLAM ve NORMAL_ANA kolonları yoksa varsayılan atıyoruz
if "ANAHTARLAM" not in ayirici_df.columns:
    ayirici_df["ANAHTARLAM"] = 1  # Varsayılan: Kapalı
if "NORMAL_ANA" not in ayirici_df.columns:
    ayirici_df["NORMAL_ANA"] = "KAPALI"  # Varsayılan: KAPALI

ayirici_df[["ABB_INT_ID", "AYIRICI_ABB_INT_ID", "ANAHTARLAM", "NORMAL_ANA"]].to_excel(
    os.path.join(OUTPUT_DIR, "ayirici_anahtar_status.xlsx"), index=False
)
print("  -> ayirici_anahtar_status.xlsx kaydedildi")

# Aynı varsayılan değerleri ayirici_df_processed'e de ekle
if "ANAHTARLAM" not in ayirici_df_processed.columns:
    ayirici_df_processed["ANAHTARLAM"] = 1
if "NORMAL_ANA" not in ayirici_df_processed.columns:
    ayirici_df_processed["NORMAL_ANA"] = "KAPALI"

# --- Bara <-> Hücre/Merkez ---
birlesik_df_bara_hucre = gpd.sjoin(bara_df, hucre_df, how="left", predicate="within")
birlesik_df_bara_hucre = birlesik_df_bara_hucre[
    ~birlesik_df_bara_hucre.index.duplicated(keep="first")
]
birlesik_df_bara_hucre["geometry"] = bara_df["geometry"]
birlesik_df_bara_merkez = gpd.sjoin(bara_df, merkez_df, how="left", predicate="within")
birlesik_df_bara_merkez = birlesik_df_bara_merkez[
    ~birlesik_df_bara_merkez.index.duplicated(keep="first")
]
bara_df_processed = bara_df.copy()
bara_df_processed["HUCRE_ABB_INT_ID"] = birlesik_df_bara_hucre["HUCRE_ABB_INT_ID"]
bara_df_processed["HUCRE_GEOMETRY"] = birlesik_df_bara_hucre["HUCRE_GEOMETRY"]
bara_df_processed["MERKEZ_ABB_INT_ID"] = birlesik_df_bara_merkez["MERKEZ_ABB_INT_ID"]
bara_df_processed["MERKEZ_GEOMETRY"] = birlesik_df_bara_merkez["MERKEZ_GEOMETRY"]

# --- Merkez <-> Hücre (many-to-many, intersects) ---
birlesik_df_merkez_hucre = gpd.sjoin(
    merkez_df, hucre_df, how="left", predicate="intersects"
)
hucre_listesi_merkez = birlesik_df_merkez_hucre.groupby("MERKEZ_ABB_INT_ID")[
    "HUCRE_ABB_INT_ID"
].apply(lambda x: x.dropna().astype(int).unique().tolist())
merkez_df["HUCRE_ABB_INT_ID"] = merkez_df["MERKEZ_ABB_INT_ID"].map(hucre_listesi_merkez)

print("Spatial join işlemleri tamamlandı.")


# =============================================================================
# 3. LOOKUP DİCTİONARY'LERİ OLUŞTUR
# =============================================================================
print("Lookup dictionary'ler oluşturuluyor...")

# --- BARA bazlı sözlükler ---
bara_2_hucre_dict = (
    dict()
)  # bara ABB_INT_ID den hucre ABB_INT_ID'ne erişme, yani baranın içinde oldugu hücre(bay)
bara_2_bara_geometry_dict = dict()  # bara id ile baranın geometri bilgisine erişme
bara_2_merkez_dict = (
    dict()
)  # bara ABB_INT_ID ile merkez(substation) ABB_INT_ID ne erişme
bara_2_ayirici_dict = (
    dict()
)  # bara ABB_INT_ID ile aynı hücre(bay) içindeki ayirici ABB_INT_ID ne erişmek
bara_2_kesici_dict = (
    dict()
)  # bara ABB_INT_ID ile aynı hücre(bay) içindeki kesici ABB_INT_ID ne erişmek
for _, row in bara_df_processed.iterrows():
    bara_2_hucre_dict[row.ABB_INT_ID] = row.HUCRE_ABB_INT_ID
    bara_2_bara_geometry_dict[row.ABB_INT_ID] = [
        (round(x, PRECISION), round(y, PRECISION)) for x, y in row.geometry.coords
    ]  # LineString -> [(x1,y1), (x2,y2), ...] PRECISION ile yuvarlanmış
    bara_2_merkez_dict[row.ABB_INT_ID] = row.MERKEZ_ABB_INT_ID
    bara_2_ayirici_dict[row.ABB_INT_ID] = ayirici_df_processed[
        (ayirici_df_processed["MERKEZ_ABB_INT_ID"] == row.MERKEZ_ABB_INT_ID)
        & (ayirici_df_processed["HUCRE_ABB_INT_ID"] == row.HUCRE_ABB_INT_ID)
    ]["ABB_INT_ID"].to_list()
    bara_2_kesici_dict[row.ABB_INT_ID] = kesici_df_processed[
        (kesici_df_processed["MERKEZ_ABB_INT_ID"] == row.MERKEZ_ABB_INT_ID)
        & (kesici_df_processed["HUCRE_ABB_INT_ID"] == row.HUCRE_ABB_INT_ID)
    ]["ABB_INT_ID"].to_list()
print("  -> bara lookups OK")

# --- AYIRICI bazlı sözlükler ---
ayirici_2_hucre_dict = (
    dict()
)  # ayirici(disconnector, isolator) ABB_INT_ID den hucre ABB_INT_ID'ne erişme, yani ayiricinin içinde oldugu hücre(bay) id
ayirici_2_ayirici_geometry_dict = (
    dict()
)  # ayirici id ile ayiricinin geometri bilgisine erişme
ayirici_2_merkez_dict = (
    dict()
)  # ayirici ABB_INT_ID ile merkez(substation) ABB_INT_ID ne erişme, ayiricinin icinde oldugu merkez idsine erişmek için
ayirici_2_kesici_dict = (
    dict()
)  # ayirici ABB_INT_ID ile aynı hücre(bay) içindeki kesici ABB_INT_ID ne erişmek
ayirici_2_bara_dict = (
    dict()
)  # ayirici ABB_INT_ID ile aynı hücre(bay) içindeki bara ABB_INT_ID ne erişmek
ayirici_2_baglanti_dict = (
    dict()
)  # ayirici ABB_INT_ID ile aynı hücre(bay) içindeki baglanti ABB_INT_ID ne erişmek
ayirici_coord_2_baglanti_coord_dict = (
    dict()
)  # ayirici koordinatı (x,y) ile aynı hücre(bay) içindeki bağlantıların koordinatlarına erişmek
ayirici_coord_2_merkez_dict = (
    dict()
)  # ayirici koordinatı (x,y) ile ayiricinin içinde bulunduğu merkez ABB_INT_ID ne erişmek
ayirici_coord_2_ayirici_id_dict = (
    dict()
)  # ayirici koordinatı (x,y) ile ayirici ABB_INT_ID ne erişmek (ters eşleme)
ayirici_2_normal_ana_dict = dict()  # ayirici id ile initial anahtar durumuna erişmek
for _, row in ayirici_df_processed.iterrows():
    ayirici_2_normal_ana_dict[row.ABB_INT_ID] = (
        1 if row.NORMAL_ANA.upper() == "KAPALI" else 0
    )
    ayirici_2_hucre_dict[row.ABB_INT_ID] = row.HUCRE_ABB_INT_ID
    ayirici_2_ayirici_geometry_dict[row.ABB_INT_ID] = (
        round(row.geometry.x, PRECISION),
        round(row.geometry.y, PRECISION),
    )  # Point -> (x, y) tuple, PRECISION ile yuvarlanmış
    ayirici_2_merkez_dict[row.ABB_INT_ID] = row.MERKEZ_ABB_INT_ID
    ayirici_coord_2_merkez_dict[
        (round(row.geometry.x, PRECISION), round(row.geometry.y, PRECISION))
    ] = row.MERKEZ_ABB_INT_ID
    ayirici_coord_2_ayirici_id_dict[
        (round(row.geometry.x, PRECISION), round(row.geometry.y, PRECISION))
    ] = row.ABB_INT_ID
    merkez_id = row.MERKEZ_ABB_INT_ID
    hucre_id = row.HUCRE_ABB_INT_ID
    ayirici_2_kesici_dict[row.ABB_INT_ID] = kesici_df_processed[
        (kesici_df_processed["MERKEZ_ABB_INT_ID"] == merkez_id)
        & (kesici_df_processed["HUCRE_ABB_INT_ID"] == hucre_id)
    ]["KESICI_ABB_INT_ID"].to_list()
    # Spatial join'den gelen sonucu kullan (koordinat bazlı, max 2 bara)
    ayirici_2_bara_dict[row.ABB_INT_ID] = _ayirici_2_bara_spatial.get(
        int(row.ABB_INT_ID), []
    )
    # FIX: HUCRE_ABB_INT_ID artık integer, list değil -> basit == kullan
    ayirici_2_baglanti_dict[row.ABB_INT_ID] = baglanti_df_processed[
        (baglanti_df_processed["MERKEZ_ABB_INT_ID"] == merkez_id)
        & (baglanti_df_processed["HUCRE_ABB_INT_ID"] == hucre_id)
    ]["BAGLANTI_ABB_INT_ID"].to_list()
    # Bağlantı LineString'lerinden sadece start/end koordinatlarını al
    baglanti_geometries = baglanti_df_processed[
        (baglanti_df_processed["MERKEZ_ABB_INT_ID"] == merkez_id)
        & (baglanti_df_processed["HUCRE_ABB_INT_ID"] == hucre_id)
    ]["geometry"]
    if len(baglanti_geometries) > 0:
        first_geom = baglanti_geometries.iloc[0]
        rounded_key = (
            round(row.geometry.x, PRECISION),
            round(row.geometry.y, PRECISION),
        )
        start_coord = (
            round(first_geom.coords[0][0], PRECISION),
            round(first_geom.coords[0][1], PRECISION),
        )
        end_coord = (
            round(first_geom.coords[-1][0], PRECISION),
            round(first_geom.coords[-1][1], PRECISION),
        )
        ayirici_coord_2_baglanti_coord_dict[rounded_key] = [start_coord, end_coord]
print("  -> ayirici lookups OK")

# ayirici_id -> BARA_NO (ilişkili baraların bara numarası)
# bara_id_2_bara_no 588. satırda merkez_tek_bara_mi hesabından önce oluşturuluyor
# ancak biz buna ihtiyaç duyuyoruz, geçici olarak burada da tanımlıyoruz
_bara_id_2_bara_no_temp = {
    int(row.ABB_INT_ID): row.BARA_NO
    for _, row in bara_df.iterrows()
    if pd.notna(row.BARA_NO)
}
ayirici_2_bara_no = {}  # ayirici_id -> bara_no (int) veya lista (birden fazla ise)
for ayirici_id, bara_id_list in ayirici_2_bara_dict.items():
    bara_no_list = [
        str(_bara_id_2_bara_no_temp[bid])[0]  # sadece ilk digit: "1a","1b" -> "1"
        for bid in bara_id_list
        if bid in _bara_id_2_bara_no_temp
    ]
    # Tekrarsız liste
    bara_no_list = list(dict.fromkeys(bara_no_list))
    if len(bara_no_list) == 1:
        ayirici_2_bara_no[ayirici_id] = bara_no_list[0]  # tek değer -> scalar
    else:
        ayirici_2_bara_no[ayirici_id] = bara_no_list  # 0 veya çok -> liste
print(f"  -> ayirici_2_bara_no: {len(ayirici_2_bara_no)} kayıt")

# --- KESİCİ bazlı sözlükler ---
kesici_2_hucre_dict = (
    dict()
)  # kesici ABB_INT_ID ile kesicinin içinde bulunduğu Hucre(bay) ABB_INT_ID ne erişmek
kesici_2_kesici_geometry_dict = (
    dict()
)  # kesici id ile kesicinin geometri bilgisine erişmek
kesici_2_merkez_dict = (
    dict()
)  # kesici ABB_INT_ID ile kesicinin içinde bulunduğu merkez(substation) ABB_INT_ID ne erişmek
kesici_2_ayirici_dict = (
    dict()
)  # kesici ABB_INT_ID ile aynı hücre(bay) içindeki ayirici ABB_INT_ID ne erişmek
kesici_2_bara_dict = (
    dict()
)  # kesici ABB_INT_ID ile aynı hücre(bay) içindeki bara ABB_INT_ID ne erişmek
kesici_2_baglanti_dict = (
    dict()
)  # kesici ABB_INT_ID ile aynı hücre(bay) içindeki baglanti ABB_INT_ID ne erişmek
for _, row in kesici_df_processed.iterrows():
    kesici_2_hucre_dict[row.ABB_INT_ID] = row.HUCRE_ABB_INT_ID
    kesici_2_kesici_geometry_dict[row.ABB_INT_ID] = (
        round(row.geometry.x, PRECISION),
        round(row.geometry.y, PRECISION),
    )  # Point -> (x, y) tuple, PRECISION ile yuvarlanmış
    kesici_2_merkez_dict[row.ABB_INT_ID] = row.MERKEZ_ABB_INT_ID
    kesici_2_ayirici_dict[row.ABB_INT_ID] = ayirici_df_processed[
        (ayirici_df_processed["MERKEZ_ABB_INT_ID"] == row.MERKEZ_ABB_INT_ID)
        & (ayirici_df_processed["HUCRE_ABB_INT_ID"] == row.HUCRE_ABB_INT_ID)
    ]["ABB_INT_ID"].to_list()
    kesici_2_bara_dict[row.ABB_INT_ID] = bara_df_processed[
        (bara_df_processed["MERKEZ_ABB_INT_ID"] == row.MERKEZ_ABB_INT_ID)
        & (bara_df_processed["HUCRE_ABB_INT_ID"] == row.HUCRE_ABB_INT_ID)
    ]["BARA_ABB_INT_ID"].to_list()
    # FIX: HUCRE_ABB_INT_ID artık integer, list değil -> basit == kullan
    kesici_2_baglanti_dict[row.ABB_INT_ID] = baglanti_df_processed[
        (baglanti_df_processed["MERKEZ_ABB_INT_ID"] == row.MERKEZ_ABB_INT_ID)
        & (baglanti_df_processed["HUCRE_ABB_INT_ID"] == row.HUCRE_ABB_INT_ID)
    ]["BAGLANTI_ABB_INT_ID"].to_list()
print("  -> kesici lookups OK")

# --- BAĞLANTI bazlı sözlükler ---
baglanti_2_hucre_dict = (
    dict()
)  # baglanti ABB_INT_ID ile baglantinin bağlandığı Hucre(bay) ABB_INT_ID ne erismek
baglanti_2_baglanti_geometry_dict = (
    dict()
)  # baglanti id ile baglantinin geometri bilgisine erismek
baglanti_2_merkez_dict = (
    dict()
)  # baglanti ABB_INT_ID ile baglantinin icinde bulundugu merkez(substation) ABB_INT_ID ne erismek
baglanti_2_kesiciler_abb_id_dict = (
    dict()
)  # baglanti ABB_INT_ID ile baglantinin icinde bağlandığı hucre icindeki kesici ABB_INT_ID ne erismek
baglanti_2_ayiricilar_abb_id_dict = (
    dict()
)  # baglanti ABB_INT_ID ile baglantinin icinde bağlandığı hucre icindeki ayirici ABB_INT_ID ne erismek
baglanti_2_baralar_abb_id_dict = (
    dict()
)  # baglanti ABB_INT_ID ile baglantinin icinde bağlandığı hucre icindeki bara ABB_INT_ID ne erismek
baglanti_2_baglanti_end_start_coord_dict = dict()
for _, row in baglanti_df_processed.iterrows():
    baglanti_2_hucre_dict[row.ABB_INT_ID] = row.HUCRE_ABB_INT_ID
    baglanti_2_baglanti_geometry_dict[row.ABB_INT_ID] = [
        (round(x, PRECISION), round(y, PRECISION)) for x, y in row.geometry.coords
    ]  # LineString -> [(x1,y1), (x2,y2), ...] PRECISION ile yuvarlanmış
    baglanti_2_merkez_dict[row.ABB_INT_ID] = row.MERKEZ_ABB_INT_ID
    hucre_id = row.HUCRE_ABB_INT_ID
    # FIX: hucre_id artık integer (veya None), list değil
    if pd.notna(hucre_id):
        hucre_id = int(hucre_id)
        baglanti_2_kesiciler_abb_id_dict[row.ABB_INT_ID] = kesici_df_processed[
            (kesici_df_processed["MERKEZ_ABB_INT_ID"] == row.MERKEZ_ABB_INT_ID)
            & (kesici_df_processed["HUCRE_ABB_INT_ID"] == hucre_id)
        ]["KESICI_ABB_INT_ID"].to_list()
        baglanti_2_ayiricilar_abb_id_dict[row.ABB_INT_ID] = ayirici_df_processed[
            (ayirici_df_processed["MERKEZ_ABB_INT_ID"] == row.MERKEZ_ABB_INT_ID)
            & (ayirici_df_processed["HUCRE_ABB_INT_ID"] == hucre_id)
        ]["AYIRICI_ABB_INT_ID"].to_list()
        baglanti_2_baralar_abb_id_dict[row.ABB_INT_ID] = bara_df_processed[
            (bara_df_processed["MERKEZ_ABB_INT_ID"] == row.MERKEZ_ABB_INT_ID)
            & (bara_df_processed["HUCRE_ABB_INT_ID"] == hucre_id)
        ]["BARA_ABB_INT_ID"].to_list()
        baglanti_2_baglanti_end_start_coord_dict[row.ABB_INT_ID] = [
            (
                round(row.geometry.coords[0][0], PRECISION),
                round(row.geometry.coords[0][1], PRECISION),
            ),
            (
                round(row.geometry.coords[-1][0], PRECISION),
                round(row.geometry.coords[-1][1], PRECISION),
            ),
        ]
    else:
        baglanti_2_kesiciler_abb_id_dict[row.ABB_INT_ID] = []
        baglanti_2_ayiricilar_abb_id_dict[row.ABB_INT_ID] = []
        baglanti_2_baralar_abb_id_dict[row.ABB_INT_ID] = []
        baglanti_2_baglanti_end_start_coord_dict[row.ABB_INT_ID] = [
            (
                round(row.geometry.coords[0][0], PRECISION),
                round(row.geometry.coords[0][1], PRECISION),
            ),
            (
                round(row.geometry.coords[-1][0], PRECISION),
                round(row.geometry.coords[-1][1], PRECISION),
            ),
        ]
print("  -> baglanti lookups OK")

# --- HÜCRE bazlı sözlükler ---
hucre_2_merkez_dict = (
    dict()
)  # hucre ABB_INT_ID ile hucrenin icinde bulundugu merkez(substation) ABB_INT_ID ne erismek
hucre_2_hucre_geometry_dict = dict()  # hucre id ile hucrenin geometri bilgisine erismek
hucre_2_ayiricilar_abb_id_dict = (
    dict()
)  # hucre ABB_INT_ID ile hucre icindeki ayirici ABB_INT_ID ne erismek
hucre_2_kesiciler_abb_id_dict = (
    dict()
)  # hucre ABB_INT_ID ile hucre icindeki kesici ABB_INT_ID ne erismek
hucre_2_baralar_abb_id_dict = (
    dict()
)  # hucre ABB_INT_ID ile hucre icindeki bara ABB_INT_ID ne erismek
hucre_2_baglantilar_abb_id_dict = (
    dict()
)  # hucre ABB_INT_ID ile hucre icindeki baglanti ABB_INT_ID ne erismek
for _, row in birlesik_df_hucre_merkez.iterrows():
    hucre_2_merkez_dict[row.HUCRE_ABB_INT_ID] = row.MERKEZ_ABB_INT_ID
    hucre_2_hucre_geometry_dict[row.HUCRE_ABB_INT_ID] = str(
        row.geometry
    )  # Polygon -> WKT string
    # FIX: HUCRE_ABB_INT_ID artık integer -> basit == kullan
    hucre_2_baglantilar_abb_id_dict[row.HUCRE_ABB_INT_ID] = baglanti_df_processed[
        baglanti_df_processed["HUCRE_ABB_INT_ID"] == row.HUCRE_ABB_INT_ID
    ]["BAGLANTI_ABB_INT_ID"].to_list()
    hucre_2_ayiricilar_abb_id_dict[row.HUCRE_ABB_INT_ID] = ayirici_df_processed.loc[
        ayirici_df_processed["HUCRE_ABB_INT_ID"] == row.HUCRE_ABB_INT_ID,
        "AYIRICI_ABB_INT_ID",
    ].to_list()
    hucre_2_kesiciler_abb_id_dict[row.HUCRE_ABB_INT_ID] = kesici_df_processed.loc[
        kesici_df_processed["HUCRE_ABB_INT_ID"] == row.HUCRE_ABB_INT_ID,
        "KESICI_ABB_INT_ID",
    ].to_list()
    hucre_2_baralar_abb_id_dict[row.HUCRE_ABB_INT_ID] = bara_df_processed.loc[
        bara_df_processed["HUCRE_ABB_INT_ID"] == row.HUCRE_ABB_INT_ID, "BARA_ABB_INT_ID"
    ].to_list()
print("  -> hucre lookups OK")

# hucre_id -> besleyici hücre mi? (1: evet, 0: hayır)
# Bağlantı elemanı olmayan veya baglama/kublaj/koruma/olcu tipi hücreler besleyici değildir
bays_suplier = {}
for _, row in hucre_df.iterrows():
    hid = int(row.ABB_INT_ID)
    alttip = str(row.ALTTIP).upper()
    baglantilar = hucre_2_baglantilar_abb_id_dict.get(hid, [])
    if not baglantilar:
        bays_suplier[hid] = 0
    elif "BAGLAMA" in alttip:
        bays_suplier[hid] = 0
    elif "KUBLAJ" in alttip:
        bays_suplier[hid] = 0
    elif "KORUMA" in alttip:
        bays_suplier[hid] = 0
    elif "OLCU" in alttip:
        bays_suplier[hid] = 0
    else:
        bays_suplier[hid] = 1
print(
    f"  -> cikis_hucreleri: {len(bays_suplier)} kayıt (besleyici: {sum(v for v in bays_suplier.values())})"
)

# --- MERKEZ bazlı sözlükler ---
merkez_2_merkez_geometry_dict = dict()  # merkez id ile merkez geometrisine erismek
merkez_2_hucre_dict = (
    dict()
)  # merkez ABB_INT_ID ile merkez icindeki hucre ABB_INT_ID ne erismek
merkez_2_ayiricilar_abb_id_dict = (
    dict()
)  # merkez ABB_INT_ID ile merkez icindeki ayirici ABB_INT_ID ne erismek
merkez_2_kesiciler_abb_id_dict = (
    dict()
)  # merkez ABB_INT_ID ile merkez icindeki kesici ABB_INT_ID ne erismek
merkez_2_baralar_abb_id_dict = (
    dict()
)  # merkez ABB_INT_ID ile merkez icindeki bara ABB_INT_ID ne erismek
merkez_2_baglantilar_abb_id_dict = (
    dict()
)  # merkez ABB_INT_ID ile merkez icindeki baglanti ABB_INT_ID ne erismek
for _, row in merkez_df.iterrows():
    merkez_2_merkez_geometry_dict[row.MERKEZ_ABB_INT_ID] = str(
        row.geometry
    )  # Polygon -> WKT string
    merkez_2_hucre_dict[row.MERKEZ_ABB_INT_ID] = row.HUCRE_ABB_INT_ID
    merkez_2_baglantilar_abb_id_dict[row.MERKEZ_ABB_INT_ID] = baglanti_df_processed.loc[
        baglanti_df_processed["MERKEZ_ABB_INT_ID"] == row.MERKEZ_ABB_INT_ID,
        "BAGLANTI_ABB_INT_ID",
    ].to_list()
    merkez_2_ayiricilar_abb_id_dict[row.MERKEZ_ABB_INT_ID] = ayirici_df_processed.loc[
        ayirici_df_processed["MERKEZ_ABB_INT_ID"] == row.MERKEZ_ABB_INT_ID,
        "AYIRICI_ABB_INT_ID",
    ].to_list()
    merkez_2_kesiciler_abb_id_dict[row.MERKEZ_ABB_INT_ID] = kesici_df_processed.loc[
        kesici_df_processed["MERKEZ_ABB_INT_ID"] == row.MERKEZ_ABB_INT_ID,
        "KESICI_ABB_INT_ID",
    ].to_list()
    merkez_2_baralar_abb_id_dict[row.MERKEZ_ABB_INT_ID] = bara_df_processed.loc[
        bara_df_processed["MERKEZ_ABB_INT_ID"] == row.MERKEZ_ABB_INT_ID,
        "BARA_ABB_INT_ID",
    ].to_list()
print("  -> merkez lookups OK")

merkez_hucre_length_dict = dict()

# --- Merkez tek bara mı? ---
# Bir merkezin baralarının tamamı aynı BARA_NO değerini taşıyorsa 1 (tek bara),
# birden fazla farklı BARA_NO varsa 0 (çoklu bara) olarak kaydedilir.
bara_id_2_bara_no = {
    int(row.ABB_INT_ID): row.BARA_NO
    for _, row in bara_df.iterrows()
    if pd.notna(row.BARA_NO)
}

merkez_tek_bara_mi = (
    dict()
)  # merkez_id -> 1 (tek bara no) veya 0 (birden fazla bara no)
for merkez_id, baralar in merkez_2_baralar_abb_id_dict.items():
    if not baralar:  # bu merkeze ait bara yok
        merkez_tek_bara_mi[merkez_id] = 1
        continue
    bara_no_set = set()
    for bara_id in baralar:
        bara_no = bara_id_2_bara_no.get(bara_id)
        if bara_no is not None:
            # Sadece ilk digit'e bak: "1a","1b","1c" -> hepsi "1" = tek bara
            # "1a","2a" -> "1" ve "2" = çoklu bara
            bara_no_set.add(str(bara_no)[0])
    if len(bara_no_set) > 1:
        merkez_tek_bara_mi[merkez_id] = 0  # birden fazla farklı bara no var
    else:
        merkez_tek_bara_mi[merkez_id] = 1  # tek bara no (veya bara no bilgisi yok)
print(f"  -> merkez_tek_bara_mi: {len(merkez_tek_bara_mi)} kayıt")
print(f"     - Tek bara: {sum(1 for v in merkez_tek_bara_mi.values() if v == 1)}")
print(f"     - Çoklu bara: {sum(1 for v in merkez_tek_bara_mi.values() if v == 0)}")

print("Lookup dictionary'ler tamamlandı.")


# =============================================================================
# 3.5 AYIRICI TOP/BOTTOM SINIFLANDIRMASI (Graph tabanlı)
# =============================================================================
# Birden fazla ayırıcısı olan hücrelerde, her ayırıcının bağlantı elemanına
# olan uzaklığını networkx shortest_path ile hesaplayarak:
#   - En yakın ayırıcı -> bottom (bağlantı elemanına en yakın)
#   - Diğer ayırıcılar -> top (bağlantı elemanından uzak olanlar)
# =============================================================================
print("Ayırıcı top/bottom sınıflandırması yapılıyor...")

# --- Graph oluştur (graph.py make_graph mantığı ile aynı) ---
G = nx.Graph()
if not point_df.empty:
    G.add_nodes_from(point_df["NODE_ID"].values)
if not edge_df.empty:
    edges = edge_df[["NODE_1", "NODE_2", "EDGE_ID"]].values
    G.add_edges_from((u, v, {"name": eid}) for u, v, eid in edges)
print(f"  -> Graph oluşturuldu: {G.number_of_nodes()} node, {G.number_of_edges()} edge")

# --- Ayırıcı ID -> koordinat sözlüğü (graph node'u olarak kullanılacak) ---
ayirici_id_2_coord = dict()
for _, row in ayirici_df_processed.iterrows():
    ayirici_id_2_coord[row.ABB_INT_ID] = (
        round(row.geometry.x, PRECISION),
        round(row.geometry.y, PRECISION),
    )

# --- Bağlantı ID -> koordinat sözlüğü (start ve end noktaları) ---
baglanti_id_2_coords = dict()
for _, row in baglanti_df_processed.iterrows():
    baglanti_id_2_coords[row.ABB_INT_ID] = [
        (
            round(row.geometry.coords[0][0], PRECISION),
            round(row.geometry.coords[0][1], PRECISION),
        ),
        (
            round(row.geometry.coords[-1][0], PRECISION),
            round(row.geometry.coords[-1][1], PRECISION),
        ),
    ]

# --- Birden fazla ayırıcısı olan hücreleri bul ---
multi_ayirici_hucre_list = [
    hucre_id
    for hucre_id, ayirici_list in hucre_2_ayiricilar_abb_id_dict.items()
    if isinstance(ayirici_list, list) and len(ayirici_list) > 1
]
print(f"  -> Birden fazla ayırıcılı hücre sayısı: {len(multi_ayirici_hucre_list)}")

# --- Top/Bottom sınıflandırması ---
hucre_2_ayirici_bottom = dict()  # hücre ID -> en yakın ayırıcı ID (tek değer)
hucre_2_ayirici_top = dict()  # hücre ID -> diğer ayırıcı ID'leri (liste)

for hucre_id in multi_ayirici_hucre_list:
    ayiricilar = hucre_2_ayiricilar_abb_id_dict[hucre_id]
    baglantilar = hucre_2_baglantilar_abb_id_dict.get(hucre_id, [])

    if not baglantilar:
        # Bağlantı elemanı yoksa sınıflandırma yapılamaz
        """print(
            f"  -> UYARI: Hücre {hucre_id} için bağlantı elemanı bulunamadı, atlanıyor."
        )"""
        continue

    # İlk bağlantı elemanını hedef olarak al
    baglanti_id = baglantilar[0] if isinstance(baglantilar, list) else baglantilar
    baglanti_coords = baglanti_id_2_coords.get(baglanti_id)
    if not baglanti_coords:
        """print(
            f"  -> UYARI: Bağlantı {baglanti_id} koordinatları bulunamadı, atlanıyor."
        )"""
        continue

    # Bağlantı elemanının graph'taki node'larını belirle (start ve end)
    baglanti_start = baglanti_coords[0]
    baglanti_end = baglanti_coords[1]

    # Hedef node olarak graph'ta bulunan bağlantı koordinatını seç
    target_node = None
    if baglanti_start in G:
        target_node = baglanti_start
    elif baglanti_end in G:
        target_node = baglanti_end

    if target_node is None:
        print(
            f"  -> UYARI: Bağlantı {baglanti_id} node'ları graph'ta bulunamadı, atlanıyor."
        )
        continue

    # Her ayırıcı için bağlantı elemanına olan mesafeyi hesapla
    baglanti_mesafeleri = dict()
    for ayirici_id in ayiricilar:
        ayirici_coord = ayirici_id_2_coord.get(ayirici_id)
        if ayirici_coord is None or ayirici_coord not in G:
            continue
        try:
            path = nx.shortest_path(G, source=ayirici_coord, target=target_node)
            baglanti_mesafeleri[ayirici_id] = len(path)
        except nx.NetworkXNoPath:
            # Yol bulunamadıysa çok büyük bir mesafe ata
            baglanti_mesafeleri[ayirici_id] = 999999
        except nx.NodeNotFound:
            continue

    if len(baglanti_mesafeleri) < 2:
        # En az 2 ayırıcı mesafesi olmalı ki sınıflandırma yapılabilsin
        continue

    # Mesafeye göre sırala (en yakından en uzağa)
    sorted_ayiricilar = sorted(baglanti_mesafeleri.items(), key=lambda x: x[1])

    # En yakın -> bottom, diğerleri -> top
    hucre_2_ayirici_bottom[hucre_id] = sorted_ayiricilar[0][0]  # sadece ID
    hucre_2_ayirici_top[hucre_id] = [
        item[0] for item in sorted_ayiricilar[1:]
    ]  # ID listesi


# =============================================================================
# Tek Bara Merkezler İçin Ayırıcı Sınıflandırması
# =============================================================================
hucre_tek_bara_top_ayirici = dict()
hucre_tek_bara_bottom_ayirici = dict()

merkez_listesi_tek_bara = [m for m, v in merkez_tek_bara_mi.items() if v == 1]
for merkez in merkez_listesi_tek_bara:
    hucreler = merkez_2_hucre_dict.get(merkez, [])
    if not isinstance(hucreler, list):
        hucreler = [hucreler] if hucreler is not None else []

    for hucre_id in hucreler:
        ayiricilar = hucre_2_ayiricilar_abb_id_dict.get(hucre_id, [])
        if not isinstance(ayiricilar, list):
            ayiricilar = [ayiricilar] if ayiricilar is not None else []

        count = len(ayiricilar)
        if count == 0:
            hucre_tek_bara_top_ayirici[hucre_id] = None
            hucre_tek_bara_bottom_ayirici[hucre_id] = None
        elif count == 1:
            hucre_tek_bara_top_ayirici[hucre_id] = ayiricilar[0]
            hucre_tek_bara_bottom_ayirici[hucre_id] = ayiricilar[0]
        elif count >= 2:
            baglantilar = hucre_2_baglantilar_abb_id_dict.get(hucre_id, [])
            baglanti_id = (
                baglantilar[0]
                if isinstance(baglantilar, list) and baglantilar
                else baglantilar
            )
            if not baglanti_id:
                continue

            baglanti_coords = baglanti_id_2_coords.get(baglanti_id)
            if not baglanti_coords:
                continue

            baglanti_start = baglanti_coords[0]
            baglanti_end = baglanti_coords[1]

            # Hedef node olarak graph'ta bulunan bağlantı koordinatını seç
            target_node = None
            if baglanti_start in G:
                target_node = baglanti_start
            elif baglanti_end in G:
                target_node = baglanti_end

            # Her ayırıcı için bağlantı elemanına olan mesafeyi hesapla
            baglanti_mesafeleri = dict()
            for ayirici_id in ayiricilar:
                ayirici_coord = ayirici_id_2_coord.get(ayirici_id)
                if ayirici_coord is None or ayirici_coord not in G:
                    continue
                try:
                    path = nx.shortest_path(G, source=ayirici_coord, target=target_node)
                    baglanti_mesafeleri[ayirici_id] = len(path)
                except nx.NetworkXNoPath:
                    # Yol bulunamadıysa çok büyük bir mesafe ata
                    baglanti_mesafeleri[ayirici_id] = 999999
                except nx.NodeNotFound:
                    continue

            if len(baglanti_mesafeleri) < 2:
                # En az 2 ayırıcı mesafesi olmalı ki sınıflandırma yapılabilsin
                continue

            # Mesafeye göre sırala (en yakından en uzağa)
            sorted_ayiricilar = sorted(baglanti_mesafeleri.items(), key=lambda x: x[1])

            # En yakın -> bottom, diğerleri -> top
            hucre_tek_bara_bottom_ayirici[hucre_id] = sorted_ayiricilar[0][
                0
            ]  # sadece ID
            hucre_tek_bara_top_ayirici[hucre_id] = [
                item[0] for item in sorted_ayiricilar[1:]
            ]  # ID listesi


# =============================================================================
# 4. EXCEL'E DUMP ET
# =============================================================================
print("Excel dosyaları oluşturuluyor...")

bara_dicts = {
    "bara_2_hucre": bara_2_hucre_dict,
    "bara_2_bara_geometry": bara_2_bara_geometry_dict,
    "bara_2_merkez": bara_2_merkez_dict,
    "bara_2_ayirici": bara_2_ayirici_dict,
    "bara_2_kesici": bara_2_kesici_dict,
}

ayirici_dicts = {
    "ayirici_2_hucre": ayirici_2_hucre_dict,
    "ayirici_2_ayirici_geometry": ayirici_2_ayirici_geometry_dict,
    "ayirici_2_merkez": ayirici_2_merkez_dict,
    "ayirici_2_kesici": ayirici_2_kesici_dict,
    "ayirici_2_bara": ayirici_2_bara_dict,
    "ayirici_2_baglanti": ayirici_2_baglanti_dict,
    "ayirici_coord_2_baglanti_coord": ayirici_coord_2_baglanti_coord_dict,
    "ayirici_coord_2_merkez": ayirici_coord_2_merkez_dict,
    "ayirici_coord_2_ayirici_id": ayirici_coord_2_ayirici_id_dict,
    "ayirici_2_normal_ana": ayirici_2_normal_ana_dict,
    "ayirici_2_bara_no": ayirici_2_bara_no,
}

kesici_dicts = {
    "kesici_2_hucre": kesici_2_hucre_dict,
    "kesici_2_kesici_geometry": kesici_2_kesici_geometry_dict,
    "kesici_2_merkez": kesici_2_merkez_dict,
    "kesici_2_ayirici": kesici_2_ayirici_dict,
    "kesici_2_bara": kesici_2_bara_dict,
    "kesici_2_baglanti": kesici_2_baglanti_dict,
}

hucre_dicts = {
    "hucre_2_merkez": hucre_2_merkez_dict,
    "hucre_2_hucre_geometry": hucre_2_hucre_geometry_dict,
    "hucre_2_ayiricilar_abb_id": hucre_2_ayiricilar_abb_id_dict,
    "hucre_2_kesiciler_abb_id": hucre_2_kesiciler_abb_id_dict,
    "hucre_2_baralar_abb_id": hucre_2_baralar_abb_id_dict,
    "hucre_2_baglantilar_abb_id": hucre_2_baglantilar_abb_id_dict,
    "hucre_name": hucre_name_dict,
    "hucre_2_ayirici_top": hucre_2_ayirici_top,
    "hucre_2_ayirici_bottom": hucre_2_ayirici_bottom,
    "hucre_2_coupling_bays": coupling_bays,
    "hucre_2_cikis_hucreleri": bays_suplier,
    "hucre_tek_bara_top_ayirici": hucre_tek_bara_top_ayirici,
    "hucre_tek_bara_bottom_ayirici": hucre_tek_bara_bottom_ayirici,
}

merkez_dicts = {
    "merkez_2_merkez_geometry": merkez_2_merkez_geometry_dict,
    "merkez_2_hucre": merkez_2_hucre_dict,
    "merkez_2_ayiricilar_abb_id": merkez_2_ayiricilar_abb_id_dict,
    "merkez_2_kesiciler_abb_id": merkez_2_kesiciler_abb_id_dict,
    "merkez_2_baralar_abb_id": merkez_2_baralar_abb_id_dict,
    "merkez_2_baglantilar_abb_id": merkez_2_baglantilar_abb_id_dict,
    "merkez_tek_bara_mi": merkez_tek_bara_mi,
}

baglanti_dicts = {
    "baglanti_2_hucre": baglanti_2_hucre_dict,
    "baglanti_2_baglanti_geometry": baglanti_2_baglanti_geometry_dict,
    "baglanti_2_merkez": baglanti_2_merkez_dict,
    "baglanti_2_kesiciler_abb_id": baglanti_2_kesiciler_abb_id_dict,
    "baglanti_2_ayiricilar_abb_id": baglanti_2_ayiricilar_abb_id_dict,
    "baglanti_2_baralar_abb_id": baglanti_2_baralar_abb_id_dict,
    "baglanti_2_end_start_coord": baglanti_2_baglanti_end_start_coord_dict,
}

all_groups = {
    "bara_lookup_dicts.xlsx": bara_dicts,
    "ayirici_lookup_dicts.xlsx": ayirici_dicts,
    "kesici_lookup_dicts.xlsx": kesici_dicts,
    "hucre_lookup_dicts.xlsx": hucre_dicts,
    "merkez_lookup_dicts.xlsx": merkez_dicts,
    "baglanti_lookup_dicts.xlsx": baglanti_dicts,
}

edge_lookup_dicts = {
    "start_end_2_edge_id": start_end_2_edge_id,
    "hat_mesafe": hat_mesafe_dict,
}

all_groups["edge_lookup_dicts.xlsx"] = edge_lookup_dicts

# Excel dosyalarını oluştur
for filename, group_dicts in all_groups.items():
    try:
        filepath = os.path.join(OUTPUT_DIR, filename)
        with pd.ExcelWriter(filepath) as writer:
            for sheet_name, d in group_dicts.items():
                df = pd.DataFrame(list(d.items()), columns=["Key", "Value"])
                df["Value"] = df["Value"].apply(
                    lambda x: (
                        str(x)
                        if isinstance(x, (list, dict))
                        or hasattr(x, "wkt")
                        or "shapely" in str(type(x))
                        else x
                    )
                )
                df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
        print(f"Oluşturuldu: {filename}")
    except Exception as e:
        print(f"Hata oluştu ({filename}): {e}")

print("\nTamamlandı!")


# =============================================================================
# 5. SINIF TANIMLARI
# =============================================================================
class Substation:
    def __init__(self, merkez_abb_int_id, merkez_geometry):
        merkez_abb_int_id = merkez_abb_int_id
        merkez_geometry = merkez_geometry
        bay_dict = dict()


class Bay:
    def __init__(self, bay_abb_int_id, bay_geometry):
        bay_abb_int_id = bay_abb_int_id
        bay_geometry = bay_geometry
        circuit_breakers = list()
        isolators = list()
        bara_dict = dict()
