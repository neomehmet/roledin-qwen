"""
import_dicts.py - Excel'den lookup sözlüklerini yükleme modülü

couplate.py tarafından Excel'e aktarılmış lookup dictionary verilerini
tekrar okuyarak Python dictionary'lerine dönüştürür.
Böylece her çalıştırmada ağır spatial join hesaplamalarının tekrarlanması önlenir.

Kullanım:
    import import_dicts
    dicts = import_dicts.load_and_unpack_all()

    bara_2_hucre_dict         = dicts["bara_2_hucre_dict"]
    bara_2_bara_geometry_dict = dicts["bara_2_bara_geometry_dict"]
    ...
"""

import pandas as pd
import ast
import os
import shapely.wkt


def safe_literal_eval(val):
    """
    Excel'den okunan string değerleri güvenli şekilde Python nesnelerine dönüştürür.

    - "[1, 2, 3]" -> [1, 2, 3]  (liste)
    - "{'a': 1}" -> {'a': 1}    (sözlük)
    - "123" -> 123               (integer - key olarak kullanılan ID'ler)
    - "45.6" -> 45.6             (float, NaN dahil)
    - Geometry WKT stringleri -> olduğu gibi string kalır
    """
    if pd.isna(val):
        return None

    if not isinstance(val, str):
        # pandas Excel'den okurken NaN olan sütunlarda int'leri float yapar (303430 -> 303430.0)
        # Bunları tekrar int'e çevir
        if isinstance(val, float) and val == val and val == int(val):
            return int(val)
        return val

    val_stripped = val.strip()

    if val_stripped == "":
        return None

    # WKT geometry stringleri için shapely'ye dönüştür
    wkt_prefixes = (
        "POINT",
        "LINESTRING",
        "POLYGON",
        "MULTIPOINT",
        "MULTILINESTRING",
        "MULTIPOLYGON",
        "GEOMETRYCOLLECTION",
    )
    if val_stripped.upper().startswith(wkt_prefixes):
        try:
            return shapely.wkt.loads(val_stripped)
        except Exception:
            return val

    # Liste veya sözlük gibi görünen stringler için ast.literal_eval kullan
    if val_stripped.startswith(("[", "{", "(")):
        try:
            return ast.literal_eval(val_stripped)
        except (ValueError, SyntaxError):
            return val

    # Sayısal değerleri dönüştürmeyi dene
    try:
        int_val = int(val_stripped)
        if str(int_val) == val_stripped:
            return int_val
    except ValueError:
        pass

    try:
        float_val = float(val_stripped)
        return float_val
    except ValueError:
        pass

    # Hiçbiri değilse string olarak döndür (geometry WKT vb.)
    return val


def _load_sheet_as_dict(filepath, sheet_name):
    """
    Bir Excel dosyasının belirtilen sheet'ini Key-Value dictionary'ye dönüştürür.
    """
    df = pd.read_excel(filepath, sheet_name=sheet_name)

    if "Key" not in df.columns or "Value" not in df.columns:
        print(f"UYARI: {filepath} -> {sheet_name} sheet'inde 'Key'/'Value' sütunu yok!")
        return {}

    d = {}
    for _, row in df.iterrows():
        key = safe_literal_eval(row["Key"])
        value = safe_literal_eval(row["Value"])
        if key is not None:
            d[key] = value
    return d


def load_and_unpack_all(base_path=None):
    """
    Tüm lookup dictionary'leri Excel dosyalarından yükler ve
    couplate.py'deki değişken adlarıyla eşleşen bir dict olarak döndürür.

    Args:
        base_path: Excel dosyalarının bulunduğu klasör yolu.
                   None ise bu dosyanın bulunduğu dizin kullanılır.

    Returns:
        dict: Aşağıdaki anahtarlarla tüm sözlükleri içerir:

        # BARA
        "bara_2_hucre_dict"
        "bara_2_bara_geometry_dict"
        "bara_2_merkez_dict"
        "bara_2_ayirici_dict"
        "bara_2_kesici_dict"

        # AYIRICI
        "ayirici_2_hucre_dict"
        "ayirici_2_ayirici_geometry_dict"
        "ayirici_2_merkez_dict"
        "ayirici_2_kesici_dict"
        "ayirici_2_bara_dict"
        "ayirici_coord_2_baglanti_coord_dict"

        # KESİCİ
        "kesici_2_hucre_dict"
        "kesici_2_kesici_geometry_dict"
        "kesici_2_merkez_dict"
        "kesici_2_ayirici_dict"
        "kesici_2_bara_dict"

        # HÜCRE
        "hucre_2_merkez_dict"
        "hucre_2_hucre_geometry_dict"
        "hucre_2_ayiricilar_abb_id_dict"
        "hucre_2_kesiciler_abb_id_dict"
        "hucre_2_baralar_abb_id_dict"
        "hucre_2_baglantilar_abb_id_dict"
        "hucre_2_ayirici_top_dict"
        "hucre_2_ayirici_bottom_dict"
        "hucre_tek_bara_top_ayirici_dict"
        "hucre_tek_bara_bottom_ayirici_dict"

        # MERKEZ
        "merkez_2_merkez_geometry_dict"
        "merkez_2_hucre_dict"
        "merkez_2_ayiricilar_abb_id_dict"
        "merkez_2_kesiciler_abb_id_dict"
        "merkez_2_baralar_abb_id_dict"
        "merkez_2_baglantilar_abb_id_dict"
        "merkez_hucre_length_dict"     # merkez_2_hucre_dict'ten türetilir
        "merkez_tek_bara_mi_dict"      # merkezdeki baralar tek bara no ise 1, farklı bara no varsa 0

        # BAĞLANTI
        "baglanti_2_hucre_dict"
        "baglanti_2_baglanti_geometry_dict"
        "baglanti_2_merkez_dict"
        "baglanti_2_kesiciler_abb_id_dict"
        "baglanti_2_ayiricilar_abb_id_dict"
        "baglanti_2_baralar_abb_id_dict"

        # NODE / EDGE
        "node_to_edge_dict"            # iki nokta koordinat çifti -> edge ABB_INT_ID
        "point_df"                     # pandas DataFrame - tüm node koordinatları
        "all_segments_df"              # pandas DataFrame - tüm segment'ler (START_POINT, END_POINT, ABB_INT_ID)
        "edge_df"                      # pandas DataFrame - edge verileri (EDGE_ID, NODE_1, NODE_2, TYPE)
    """
    if base_path is None:
        base_path = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.join(base_path, "look-ups")

    result = {}

    # =====================================================================
    # Excel dosya adı -> (sheet_adı, hedef_dict_adı) eşlemesi
    # couplate.py'deki export sırasıyla birebir aynı
    # =====================================================================

    file_mappings = {
        # ---- BARA ----
        "bara_lookup_dicts.xlsx": [
            ("bara_2_hucre", "bara_2_hucre_dict"),
            ("bara_2_bara_geometry", "bara_2_bara_geometry_dict"),
            ("bara_2_merkez", "bara_2_merkez_dict"),
            ("bara_2_ayirici", "bara_2_ayirici_dict"),
            ("bara_2_kesici", "bara_2_kesici_dict"),
        ],
        # ---- AYIRICI ----
        "ayirici_lookup_dicts.xlsx": [
            ("ayirici_2_hucre", "ayirici_2_hucre_dict"),
            ("ayirici_2_ayirici_geometry", "ayirici_2_ayirici_geometry_dict"),
            ("ayirici_2_merkez", "ayirici_2_merkez_dict"),
            ("ayirici_2_kesici", "ayirici_2_kesici_dict"),
            ("ayirici_2_bara", "ayirici_2_bara_dict"),
            ("ayirici_2_baglanti", "ayirici_2_baglanti_dict"),
            ("ayirici_coord_2_baglanti_coord", "ayirici_coord_2_baglanti_coord_dict"),
            ("ayirici_coord_2_merkez", "ayirici_coord_2_merkez_dict"),
            ("ayirici_coord_2_ayirici_id", "ayirici_coord_2_ayirici_id_dict"),
            ("ayirici_2_normal_ana", "ayirici_2_normal_ana_dict"),
            ("ayirici_2_bara_no", "ayirici_2_bara_no_dict"),
        ],
        # ---- KESİCİ ----
        "kesici_lookup_dicts.xlsx": [
            ("kesici_2_hucre", "kesici_2_hucre_dict"),
            ("kesici_2_kesici_geometry", "kesici_2_kesici_geometry_dict"),
            ("kesici_2_merkez", "kesici_2_merkez_dict"),
            ("kesici_2_ayirici", "kesici_2_ayirici_dict"),
            ("kesici_2_bara", "kesici_2_bara_dict"),
            ("kesici_2_baglanti", "kesici_2_baglanti_dict"),
        ],
        # ---- HÜCRE ----
        "hucre_lookup_dicts.xlsx": [
            ("hucre_2_merkez", "hucre_2_merkez_dict"),
            ("hucre_2_hucre_geometry", "hucre_2_hucre_geometry_dict"),
            ("hucre_2_ayiricilar_abb_id", "hucre_2_ayiricilar_abb_id_dict"),
            ("hucre_2_kesiciler_abb_id", "hucre_2_kesiciler_abb_id_dict"),
            ("hucre_2_baralar_abb_id", "hucre_2_baralar_abb_id_dict"),
            ("hucre_2_baglantilar_abb_id", "hucre_2_baglantilar_abb_id_dict"),
            ("hucre_name", "hucre_name_dict"),
            ("hucre_2_ayirici_top", "hucre_2_ayirici_top_dict"),
            ("hucre_2_ayirici_bottom", "hucre_2_ayirici_bottom_dict"),
            ("hucre_2_coupling_bays", "hucre_2_coupling_bays_dict"),
            ("hucre_2_cikis_hucreleri", "hucre_2_cikis_hucreleri_dict"),
            ("hucre_tek_bara_top_ayirici", "hucre_tek_bara_top_ayirici_dict"),
            ("hucre_tek_bara_bottom_ayirici", "hucre_tek_bara_bottom_ayirici_dict"),
        ],
        # ---- MERKEZ ----
        "merkez_lookup_dicts.xlsx": [
            ("merkez_2_merkez_geometry", "merkez_2_merkez_geometry_dict"),
            ("merkez_2_hucre", "merkez_2_hucre_dict"),
            ("merkez_2_ayiricilar_abb_id", "merkez_2_ayiricilar_abb_id_dict"),
            ("merkez_2_kesiciler_abb_id", "merkez_2_kesiciler_abb_id_dict"),
            ("merkez_2_baralar_abb_id", "merkez_2_baralar_abb_id_dict"),
            ("merkez_2_baglantilar_abb_id", "merkez_2_baglantilar_abb_id_dict"),
            ("merkez_tek_bara_mi", "merkez_tek_bara_mi_dict"),
        ],
        # ---- BAĞLANTI ----
        "baglanti_lookup_dicts.xlsx": [
            ("baglanti_2_hucre", "baglanti_2_hucre_dict"),
            ("baglanti_2_baglanti_geometry", "baglanti_2_baglanti_geometry_dict"),
            ("baglanti_2_merkez", "baglanti_2_merkez_dict"),
            ("baglanti_2_kesiciler_abb_id", "baglanti_2_kesiciler_abb_id_dict"),
            ("baglanti_2_ayiricilar_abb_id", "baglanti_2_ayiricilar_abb_id_dict"),
            ("baglanti_2_baralar_abb_id", "baglanti_2_baralar_abb_id_dict"),
            ("baglanti_2_end_start_coord", "baglanti_2_baglanti_end_start_coord_dict"),
        ],
        # ---- EDGE ----
        "edge_lookup_dicts.xlsx": [
            ("start_end_2_edge_id", "start_end_2_edge_id"),
            ("hat_mesafe", "hat_mesafe_dict"),
        ],
    }

    # Her Excel dosyasını ve içindeki her sheet'i sırayla yükle
    for filename, sheet_mappings in file_mappings.items():
        filepath = os.path.join(base_path, filename)

        if not os.path.exists(filepath):
            print(f"UYARI: {filepath} dosyası bulunamadı!")
            # Dosya yoksa boş dict'ler ata
            for sheet_name, dict_name in sheet_mappings:
                result[dict_name] = {}
            continue

        print(f"Yükleniyor: {filename}")
        for sheet_name, dict_name in sheet_mappings:
            try:
                d = _load_sheet_as_dict(filepath, sheet_name)
                result[dict_name] = d
                print(f"  -> {dict_name}: {len(d)} kayit")
            except Exception as e:
                print(f"  -> HATA {dict_name}: {e}")
                result[dict_name] = {}

    # =====================================================================
    # merkez_hucre_length_dict: Excel'e dump edilmedi,
    # merkez_2_hucre_dict'ten türetilir (her merkez için hücre sayısı)
    # =====================================================================
    merkez_2_hucre = result.get("merkez_2_hucre_dict", {})
    merkez_hucre_length = {}
    for merkez_id, hucre_list in merkez_2_hucre.items():
        if isinstance(hucre_list, list):
            merkez_hucre_length[merkez_id] = len(hucre_list)
        else:
            merkez_hucre_length[merkez_id] = 0
    result["merkez_hucre_length_dict"] = merkez_hucre_length
    print(
        f"  -> merkez_hucre_length_dict: {len(merkez_hucre_length)} kayıt (türetildi)"
    )

    # =====================================================================
    # node_to_edge_dict: node_to_edge_dict.xlsx dosyasından yüklenir
    # Key: "(x1,y1) (x2,y2)" formatında iki nokta koordinat çifti
    # Value: edge ABB_INT_ID (integer)
    # =====================================================================
    node_to_edge_filepath = os.path.join(base_path, "node_to_edge_dict.xlsx")
    if os.path.exists(node_to_edge_filepath):
        print(f"Yükleniyor: node_to_edge_dict.xlsx")
        try:
            df = pd.read_excel(node_to_edge_filepath)
            d = {}
            # Sütun adları: COORDINATE, ABB_INT_ID
            if "COORDINATE" in df.columns and "ABB_INT_ID" in df.columns:
                for _, row in df.iterrows():
                    key = str(row["COORDINATE"])
                    value = safe_literal_eval(row["ABB_INT_ID"])
                    d[key] = value
            elif "Key" in df.columns and "Value" in df.columns:
                for _, row in df.iterrows():
                    key = str(row["Key"])
                    value = safe_literal_eval(row["Value"])
                    d[key] = value
            result["node_to_edge_dict"] = d
            print(f"  -> node_to_edge_dict: {len(d)} kayıt")
        except Exception as e:
            print(f"  -> HATA node_to_edge_dict: {e}")
            result["node_to_edge_dict"] = {}
    else:
        print(f"UYARI: node_to_edge_dict.xlsx bulunamadı!")
        result["node_to_edge_dict"] = {}

    # =====================================================================
    # point_df: point_df.xlsx dosyasından DataFrame olarak yüklenir
    # NODE_ID sütunu: tüm node koordinatlarını içerir
    # =====================================================================
    point_df_filepath = os.path.join(base_path, "point_df.xlsx")
    if os.path.exists(point_df_filepath):
        print(f"Yükleniyor: point_df.xlsx")
        try:
            point_df = pd.read_excel(point_df_filepath)
            # NODE_ID sütunundaki string tuple'ları gerçek tuple'lara dönüştür
            if "NODE_ID" in point_df.columns:
                point_df["NODE_ID"] = point_df["NODE_ID"].apply(safe_literal_eval)
            result["point_df"] = point_df
            print(f"  -> point_df: {len(point_df)} satır")
        except Exception as e:
            print(f"  -> HATA point_df: {e}")
            result["point_df"] = pd.DataFrame()
    else:
        print(f"UYARI: point_df.xlsx bulunamadı!")
        result["point_df"] = pd.DataFrame()

    # =====================================================================
    # all_segments_df: all_segment.xlsx dosyasından DataFrame olarak yüklenir
    # START_POINT, END_POINT, ABB_INT_ID sütunları
    # =====================================================================
    all_segments_filepath = os.path.join(base_path, "all_segment.xlsx")
    if os.path.exists(all_segments_filepath):
        print(f"Yükleniyor: all_segment.xlsx")
        try:
            all_segments_df = pd.read_excel(all_segments_filepath)
            # String tuple'ları gerçek tuple'lara dönüştür
            for col in ["START_POINT", "END_POINT"]:
                if col in all_segments_df.columns:
                    all_segments_df[col] = all_segments_df[col].apply(safe_literal_eval)
            result["all_segments_df"] = all_segments_df
            print(f"  -> all_segments_df: {len(all_segments_df)} satır")
        except Exception as e:
            print(f"  -> HATA all_segments_df: {e}")
            result["all_segments_df"] = pd.DataFrame()
    else:
        print(f"UYARI: all_segment.xlsx bulunamadı!")
        result["all_segments_df"] = pd.DataFrame()

    # =====================================================================
    # edge_df: edge_df.xlsx dosyasından DataFrame olarak yüklenir
    # EDGE_ID, NODE_1, NODE_2, TYPE sütunları
    # =====================================================================
    edge_df_filepath = os.path.join(base_path, "edge_df.xlsx")
    if os.path.exists(edge_df_filepath):
        print(f"Yükleniyor: edge_df.xlsx")
        try:
            edge_df = pd.read_excel(edge_df_filepath)
            # String tuple'ları gerçek tuple'lara dönüştür
            for col in ["NODE_1", "NODE_2"]:
                if col in edge_df.columns:
                    edge_df[col] = edge_df[col].apply(safe_literal_eval)
            result["edge_df"] = edge_df
            print(f"  -> edge_df: {len(edge_df)} satır")
        except Exception as e:
            print(f"  -> HATA edge_df: {e}")
            result["edge_df"] = pd.DataFrame()
    else:
        print(f"UYARI: edge_df.xlsx bulunamadı!")
        result["edge_df"] = pd.DataFrame()

    # =====================================================================
    # bara_2_baglanti_df: bara_2_baglanti.xlsx dosyasından DataFrame olarak yüklenir
    # BARA_ABB_INT_ID, BAGLANTI_ABB_INT_ID sütunları
    # =====================================================================
    bara_baglanti_filepath = os.path.join(base_path, "bara_2_baglanti.xlsx")
    if os.path.exists(bara_baglanti_filepath):
        print(f"Yükleniyor: bara_2_baglanti.xlsx")
        try:
            bara_2_baglanti_df = pd.read_excel(bara_baglanti_filepath)
            result["bara_2_baglanti_df"] = bara_2_baglanti_df
            print(f"  -> bara_2_baglanti_df: {len(bara_2_baglanti_df)} satır")
        except Exception as e:
            print(f"  -> HATA bara_2_baglanti_df: {e}")
            result["bara_2_baglanti_df"] = pd.DataFrame()
    else:
        print(f"UYARI: bara_2_baglanti.xlsx bulunamadı!")
        result["bara_2_baglanti_df"] = pd.DataFrame()

    # =====================================================================
    # ayirici_anahtar_status_df: ayirici_anahtar_status.xlsx
    # ABB_INT_ID, AYIRICI_ABB_INT_ID, ANAHTARLAM, NORMAL_ANA sütunları
    # =====================================================================
    ayirici_status_filepath = os.path.join(base_path, "ayirici_anahtar_status.xlsx")
    if os.path.exists(ayirici_status_filepath):
        print(f"Yükleniyor: ayirici_anahtar_status.xlsx")
        try:
            ayirici_anahtar_status_df = pd.read_excel(ayirici_status_filepath)
            result["ayirici_anahtar_status_df"] = ayirici_anahtar_status_df
            print(
                f"  -> ayirici_anahtar_status_df: {len(ayirici_anahtar_status_df)} satır"
            )
        except Exception as e:
            print(f"  -> HATA ayirici_anahtar_status_df: {e}")
            result["ayirici_anahtar_status_df"] = pd.DataFrame()
    else:
        print(f"UYARI: ayirici_anahtar_status.xlsx bulunamadı!")
        result["ayirici_anahtar_status_df"] = pd.DataFrame()

    print(f"\nToplam {len(result)} öğe yüklendi.")
    return result


def load_dataframes_only(base_path=None):
    """
    Sadece edge_df ve point_df DataFrame'lerini Excel'den yükler.
    Lookup dictionary'leri yüklemez, sadece 2 DataFrame döndürür.

    Args:
        base_path: Excel dosyalarının bulunduğu klasör yolu.
                   None ise bu dosyanın bulunduğu dizin kullanılır.

    Returns:
        tuple: (edge_df, point_df)
            - edge_df:  EDGE_ID, NODE_1, NODE_2, TYPE sütunları (edge_df.xlsx)
            - point_df: NODE_ID sütunu (point_df.xlsx)
    """
    if base_path is None:
        base_path = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.join(base_path, "look-ups")
    # edge_df yükle
    edge_df_filepath = os.path.join(base_path, "edge_df.xlsx")
    if os.path.exists(edge_df_filepath):
        print(f"Yükleniyor: edge_df.xlsx")
        edge_df = pd.read_excel(edge_df_filepath)
        for col in ["NODE_1", "NODE_2"]:
            if col in edge_df.columns:
                edge_df[col] = edge_df[col].apply(safe_literal_eval)
        print(f"  -> edge_df: {len(edge_df)} satır")
    else:
        print(f"UYARI: edge_df.xlsx bulunamadı!")
        edge_df = pd.DataFrame()

    # point_df yükle
    point_df_filepath = os.path.join(base_path, "point_df.xlsx")
    if os.path.exists(point_df_filepath):
        print(f"Yükleniyor: point_df.xlsx")
        point_df = pd.read_excel(point_df_filepath)
        if "NODE_ID" in point_df.columns:
            point_df["NODE_ID"] = point_df["NODE_ID"].apply(safe_literal_eval)
        print(f"  -> point_df: {len(point_df)} satır")
    else:
        print(f"UYARI: point_df.xlsx bulunamadı!")
        point_df = pd.DataFrame()

    return edge_df, point_df


# Doğrudan çalıştırılırsa test amaçlı yükleme yap
if __name__ == "__main__":
    print("=" * 60)
    print("Excel'den Lookup Sözlüklerini Yükleme Testi")
    print("=" * 60)

    dicts = load_and_unpack_all()
    hucre_2_baglantilar_abb_id_dict = dicts["hucre_2_baglantilar_abb_id_dict"]

    """
    bara_2_hucre_dict = dicts["bara_2_hucre_dict"]
    bara_2_bara_geometry_dict = dicts["bara_2_bara_geometry_dict"]
    bara_2_merkez_dict = dicts["bara_2_merkez_dict"]
    bara_2_ayirici_dict = dicts["bara_2_ayirici_dict"]
    bara_2_kesici_dict = dicts["bara_2_kesici_dict"]

    ayirici_2_hucre_dict = dicts["ayirici_2_hucre_dict"]
    ayirici_2_ayirici_geometry_dict = dicts["ayirici_2_ayirici_geometry_dict"]
    ayirici_2_merkez_dict = dicts["ayirici_2_merkez_dict"]
    ayirici_2_kesici_dict = dicts["ayirici_2_kesici_dict"]
    ayirici_2_bara_dict = dicts["ayirici_2_bara_dict"]

    kesici_2_hucre_dict = dicts["kesici_2_hucre_dict"]
    kesici_2_kesici_geometry_dict = dicts["kesici_2_kesici_geometry_dict"]
    kesici_2_merkez_dict = dicts["kesici_2_merkez_dict"]
    kesici_2_ayirici_dict = dicts["kesici_2_ayirici_dict"]
    kesici_2_bara_dict = dicts["kesici_2_bara_dict"]

    hucre_2_merkez_dict = dicts["hucre_2_merkez_dict"]
    hucre_2_hucre_geometry_dict = dicts["hucre_2_hucre_geometry_dict"]
    hucre_2_ayiricilar_abb_id_dict = dicts["hucre_2_ayiricilar_abb_id_dict"]
    hucre_2_kesiciler_abb_id_dict = dicts["hucre_2_kesiciler_abb_id_dict"]
    hucre_2_baralar_abb_id_dict = dicts["hucre_2_baralar_abb_id_dict"]
    hucre_2_baglantilar_abb_id_dict = dicts["hucre_2_baglantilar_abb_id_dict"]

    merkez_2_merkez_geometry_dict = dicts["merkez_2_merkez_geometry_dict"]
    merkez_2_hucre_dict = dicts["merkez_2_hucre_dict"]
    merkez_2_ayiricilar_abb_id_dict = dicts["merkez_2_ayiricilar_abb_id_dict"]
    merkez_2_kesiciler_abb_id_dict = dicts["merkez_2_kesiciler_abb_id_dict"]
    merkez_2_baralar_abb_id_dict = dicts["merkez_2_baralar_abb_id_dict"]
    merkez_2_baglantilar_abb_id_dict = dicts["merkez_2_baglantilar_abb_id_dict"]
    # merkez_hucre_length_dict = dict()

    baglanti_2_hucre_dict = dicts["baglanti_2_hucre_dict"]
    baglanti_2_baglanti_geometry_dict = dicts["baglanti_2_baglanti_geometry_dict"]
    baglanti_2_merkez_dict = dicts["baglanti_2_merkez_dict"]
    baglanti_2_kesiciler_abb_id_dict = dicts["baglanti_2_kesiciler_abb_id_dict"]
    baglanti_2_ayiricilar_abb_id_dict = dicts["baglanti_2_ayiricilar_abb_id_dict"]
    baglanti_2_baralar_abb_id_dict = dicts["baglanti_2_baralar_abb_id_dict"]

    node_to_edge_dict = dicts["node_to_edge_dict"]
    point_df = dicts["point_df"]
    all_segments_df = dicts["all_segments_df"]
    edge_df = dicts["edge_df"]

    for key, row in all_segments_df.iterrows():
        start_point = row["START_POINT"]
        end_point = row["END_POINT"]
        abb_int_id = row["ABB_INT_ID"]
        if 15476431 == abb_int_id:
            print(start_point, end_point, abb_int_id)

    edge_df, point_df = load_dataframes_only()

    def make_graph(self):
        G = nx.Graph()
        if not self.point_df.empty:
            G.add_nodes_from(self.point_df["NODE_ID"].values)
        if not self.edge_df.empty:
            edges = self.edge_df[["NODE_1", "NODE_2", "EDGE_ID"]].values
            G.add_edges_from((u, v, {"name": eid}) for u, v, eid in edges)
        self.graph = G
    """
