import __main__
import import_dicts
import networkx as nx
import pandas as pd
import ast
import psutil
import os
import sys
from collections import deque

fot_text = ""
count = 0
# not 10816713 bu merkez biraz anormal
SKIP_HUCRE_TYPES = {
    "BARA BAGLAMA (KUPLAJ) HUCRESI",
    "GERILIM KORUMA HUCRESI",
    "TRANSFORMATOR KORUMA HUCRESI",
    "AKIM OLCU HUCRESI",
    "AKIM GERILIM HUCRESI",
}

connection_and_length = (
    list()
)  # node, node , path, pathi length, # bu satırdaki liste to_delete.py dosyasındaki results listesi gibi kullanılacak


# 5145271
def deduplicate_dict_list(dict_list):
    """
    Liste içindeki tekrar eden dict'leri kaldırır.
    Dict value'ları liste olsa bile çalışır, tipleri değiştirmez.
    """
    seen = set()
    result = []
    for item in dict_list:
        # Dict'i hashlenebilir tuple'a çevir (liste -> tuple)
        key = tuple(
            (k, tuple(v) if isinstance(v, list) else v) for k, v in sorted(item.items())
        )
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def get_line_id(edge_df, node_1, node_2):
    pass


def is_cable_include(hat_edge_ids, path_ids):
    """path_ids listesindeki herhangi bir edge kablo (HAT) tipinde mi?"""
    """
    for i in path_ids:
        if i == 13398981:
            print("hat bulundu ", i)
            print("hat bulundu ", i)
            print("hat bulundu ", i)
            print("hat bulundu ", i)
    """
    return bool(path_ids) and any(i in hat_edge_ids for i in path_ids)


# start_end_2_edge_id is a dict was created couplatev2.py keys are coordinate, values are edge id
# path is a list of nodes as coordinate
def get_path_ids(start_end_2_edge_id, path):
    path_contains_id = list()
    for i in range(len(path) - 1):
        edge_id = start_end_2_edge_id.get((path[i], path[i + 1]))
        if edge_id is None:
            return None
        path_contains_id.append(edge_id)
    return path_contains_id


class Graph:
    def __init__(self):
        self.graph = None
        self.point_df = None
        self.edge_df = None
        self.m2h = None
        self.h2a = None
        self.hucre_2_ayiricilar_abb_id_dict = None
        self.ayirici_coord_2_baglanti_coord_dict = None
        self.ayirici_coord_2_merkez_dict = None
        self.ayirici_id_2_coord = None
        self.ayirici_2_normal_ana_dict = None
        self.root_node_merkez_id = 144725
        self.hucre_tree = pd.DataFrame()
        self.to_trace_hucre = None
        self.ayirici_2_normal_ana = None
        self.merkez_giris_ayiricilari = list()  # hücre id to ayirici list
        self.merkez_giris_hucreleri = (
            list()
        )  # bir merkezi besleyen fiderin girdiği hücre key merkez id, value hücre id
        self.merkez_cikis_hucreleri = list()
        self.ayirici_coord_set = None
        self.start_end_2_edge_id = None
        self.hat_edge_ids = set()  # HAT (kablo) tipindeki edge ID'leri
        self.hat_mesafe_dict = dict()
        self.buffer_df = pd.DataFrame(
            columns=[
                "source_coord",
                "target_coord",
                "path_coord",
                "path_ids",
                "source_id",
                "target_id",
                "source_merkez_id",
                "target_merkez_id",
                "source_hucre_id",
                "target_hucre_id",
            ]
        )
        self.hata_loglari = list()

    def init_dicts(self):
        dicts = import_dicts.load_and_unpack_all()
        self.m2h = dicts["merkez_2_hucre_dict"]  # merkez to hucre list
        self.h2a = dicts["hucre_2_ayiricilar_abb_id_dict"]
        self.hucreler = self.m2h.get(144725, [])  # Sarıyer hücre listesi
        self.enh_length = dicts["hat_mesafe_dict"]
        # Ayırıcı verilerini al
        self.ayirici_id_2_coord = dicts[
            "ayirici_2_ayirici_geometry_dict"
        ]  # ayirici_id -> (x, y)
        self.ayirici_coord_2_ayirici_id_dict = dicts["ayirici_coord_2_ayirici_id_dict"]
        self.ayirici_coord_set = set(self.ayirici_coord_2_ayirici_id_dict.keys())
        self.ayirici_2_hucre_dict = dicts[
            "ayirici_2_hucre_dict"
        ]  # ayirici id -> hucre id
        self.ayirici_2_merkez_dict = dicts[
            "ayirici_2_merkez_dict"
        ]  # ayirici id -> merkez id
        self.ayirici_2_baglanti_dict = dicts[
            "ayirici_2_baglanti_dict"
        ]  # ayirici id -> baglanti id
        self.ayirici_coord_2_baglanti_coord_dict = dicts[
            "ayirici_coord_2_baglanti_coord_dict"
        ]  # ayirici coord -> baglanti coord to find downstream
        self.ayirici_coord_2_merkez_dict = dicts[
            "ayirici_coord_2_merkez_dict"
        ]  # ayirici coord -> merkez id
        self.ayirici_2_normal_ana_dict = dicts["ayirici_2_normal_ana_dict"]
        self.start_end_2_edge_id = dicts["start_end_2_edge_id"]
        self.hat_mesafe_dict = dicts.get(
            "hat_mesafe_dict", {}
        )  # hat_id -> uzunluk (metre)
        self.hucre_2_ayiricilar_abb_id_dict = dicts["hucre_2_ayiricilar_abb_id_dict"]
        self.point_df = dicts["point_df"]
        self.edge_df = dicts["edge_df"]
        self.hucre_name = dicts[
            "hucre_name_dict"
        ]  # bura doğru olmayabilir böyle mi import edebilrim
        # HAT tipindeki edge ID'lerini set olarak sakla (is_cable_include için)
        if not self.edge_df.empty and "TYPE" in self.edge_df.columns:
            self.hat_edge_ids = set(
                self.edge_df.loc[self.edge_df["TYPE"] == "HAT", "EDGE_ID"]
            )
        else:
            self.hat_edge_ids = set()
        # Yeni dict yüklemeleri (merkez içi trace için)
        self.hucre_2_merkez = dicts["hucre_2_merkez_dict"]
        self.hucre_2_ayirici_top = dicts["hucre_2_ayirici_top_dict"]
        self.hucre_2_ayirici_bottom = dicts["hucre_2_ayirici_bottom_dict"]
        self.hucre_2_cikis = dicts["hucre_2_cikis_hucreleri_dict"]
        self.hucre_2_coupling = dicts["hucre_2_coupling_bays_dict"]
        self.ayirici_2_bara_no = dicts["ayirici_2_bara_no_dict"]
        self.merkez_tek_bara_mi = dicts["merkez_tek_bara_mi_dict"]
        self.hucre_tek_bara_top_ayirici = dicts.get(
            "hucre_tek_bara_top_ayirici_dict", {}
        )
        self.hucre_tek_bara_bottom_ayirici = dicts.get(
            "hucre_tek_bara_bottom_ayirici_dict", {}
        )
        self.merkez_hucre_2_sub_merkez_sub_hucre = pd.DataFrame(
            columns=(
                "source_merkez_id",
                "source_hucre",
                "target_merkez",
                "target_hucre",
            )
        )

    def make_graph(self):
        G = nx.Graph()
        if not self.point_df.empty:
            G.add_nodes_from(self.point_df["NODE_ID"].values)

        # Ayırıcı koordinatlarını da graph'a ekle (edge'lerdeki node'lar dışında kalan)
        if self.ayirici_id_2_coord:
            ayirici_coords = set(self.ayirici_id_2_coord.values())
            G.add_nodes_from(ayirici_coords)

        if not self.edge_df.empty:
            edges = self.edge_df[["NODE_1", "NODE_2", "EDGE_ID"]].values
            G.add_edges_from((u, v, {"name": eid}) for u, v, eid in edges)
        self.graph = G

    def search_and_create_tree(
        self, start_hucre_id
    ):  # , to_trace_list: list(), traced_list: list()
        global connection_and_length  # node, node , path, pathi length, # bu satırdaki liste to_delete.py dosyasındaki results listesi gibi kullanılacak

        source_nodes = self.preperation(start_hucre_id)
        # source_nodes: ( trace starting coord, start ayirici id, initial connections )

        just_between_bays = list()  # to debugging

        for source_node_coord, ayirici_id, initial_conns in source_nodes:
            connection_and_length.clear()
            connection_and_length.extend(initial_conns)

            just_between_bays.clear()
            just_between_bays.extend(initial_conns)

            visited = set()
            # Her ayırıcı için visited sıfırlanmalı ki birbirini engellemesin!
            queue = deque([source_node_coord])

            process = psutil.Process(os.getpid())  # RAM takibi için işlem objesi
            mem_info_mb = process.memory_info().rss / (1024 * 1024)
            print(f"--- Queue Size: {len(queue)} | RAM: {mem_info_mb:.2f} MB ---")

            while queue:
                ayirici_coord = queue.popleft()
                # boşsa hata fırlatır ama boşsa zaten while girmez
                if ayirici_coord in visited:
                    continue
                paths, baglanti_start, baglanti_end = self.pre_process(ayirici_coord)
                if paths is None:
                    # print("pre_process() method return None")
                    continue
                buffer_df, filter_param = self.process_paths_fast(
                    ayirici_coord, paths, baglanti_start, baglanti_end
                )
                if buffer_df is None:
                    # print("Warning : filter_and_clear_buffer() method return None")
                    continue
                to_add_queueu = self.prepare_connection(
                    ayirici_coord,
                    buffer_df,
                    filter_param,
                    connection_and_length,
                    just_between_bays,
                )
                if to_add_queueu is not None:
                    queue.extend(to_add_queueu)
                    # print(to_add_queueu)
                visited.add(ayirici_coord)

            # while döngüsü bittikten sonra excele aktar
            if connection_and_length:
                df_conn = pd.DataFrame(
                    connection_and_length,
                    columns=[
                        "from_ayirici",
                        "to_ayirici",
                        "length",
                        "enh_ids",
                        "anahtar_durumu",
                    ],
                )
                df_conn.drop_duplicates(
                    subset=["from_ayirici", "to_ayirici"], inplace=True
                )
                df_conn.to_excel(
                    f"{ayirici_id}-connection_and_length.xlsx", index=False
                )
                print(
                    "Trace bağlantı sonuçları 'connection_and_length.xlsx' dosyasına kaydedildi."
                )
            if just_between_bays:
                df_conn = pd.DataFrame(
                    just_between_bays,
                    columns=[
                        "from_ayirici",
                        "to_ayirici",
                        "length",
                        "enh_ids",
                        "anahtar_durumu",
                    ],
                )
                df_conn.drop_duplicates(
                    subset=["from_ayirici", "to_ayirici"], inplace=True
                )
                df_conn.to_excel(
                    f"{ayirici_id}-just_between_bays.xlsx", index=False
                )  # 305327

    def preperation(self, hucre_id):
        """
        Prepares graph traversal data for a given hucre_id. hucre means bay
        Function workflow:
        1. Retrieves all ayirici (disconnector) IDs connected to the given hucre.
        2. Searches for a CLOSED ("KAPALI") ayirici among them.
        3. Retrieves the coordinate (graph node) of the selected ayirici.
        4. Verifies that this node exists in the network graph.
        5. Obtains the connection coordinates of the ayirici.
        6. Extracts start and end connection nodes.
        7. Computes shortest paths from the ayirici node in the graph
        using NetworkX (cutoff = 30 steps)
        """

        source_nodes = list()
        top_ayirici_list, bottom_ayirici_id, tek_bara_mi = self.ayirici_list_finder(
            hucre_id
        )
        for i in self.ensure_list(top_ayirici_list):
            anahtar_durumu = self.ayirici_2_normal_ana_dict.get(i, 0)
            if i is None:
                # ("Warning : ayirici_id is None - hiç KAPALI ayirici bulunamadı!")
                return None, None

            source_node = self.ayirici_id_2_coord.get(i)  # (x, y) tuple
            if not source_node:
                # print(f"Warning: source_node not found for ayirici_id {ayirici_id}")
                return None, None

            # source_merkez = self.ayirici_coord_2_merkez_dict.get(source_node)
            # Bu node graph'ta yoksa atla
            if source_node not in self.graph:
                # print(f"Warning: source_node {source_node} not in graph")
                # return source_node, source_merkez, None, None, None, None
                return None, None

            # Ayırıcı koordinatının bağlantı verisi yoksa atla
            baglanti_coords = self.ayirici_coord_2_baglanti_coord_dict.get(source_node)
            if not baglanti_coords:
                # print(f"Warning: baglanti_coords not found for source_node {source_node}")
                # return source_node, source_merkez, None, None, None, None
                return None, None
            baglanti_start = baglanti_coords[0]
            paths = nx.shortest_path(self.graph, source_node, baglanti_start)
            initial_conns = []
            source_node = self.baslangic_setter(
                paths, i, bottom_ayirici_id, initial_conns, tek_bara_mi
            )

            if source_node is None:
                continue
            else:
                source_nodes.append([source_node, i, initial_conns])

        return source_nodes
        """(
            source_node,
            # source_merkez,
            # baglanti_coords,
            # baglanti_start,
            # baglanti_end,
            # paths,
            ayirici_id,
            anahtar_durumu,
        )"""

    def ayirici_list_finder(self, hucre_id):
        """merkezin tek var ve 2.5 bara olmasına göre üst ve alt ayiricilari buluyor"""
        bottom_ayirici_id = None
        merkez = self.hucre_2_merkez.get(hucre_id)
        tek_bara_mi = self.merkez_tek_bara_mi.get(merkez)  # 1 tek bara, 0 2.5 bara

        if tek_bara_mi == 1:
            ayirici_id_list = self.hucre_tek_bara_top_ayirici.get(hucre_id)
            bottom_ayirici_id = self.hucre_tek_bara_bottom_ayirici.get(hucre_id)
            # burada üstteki 2 satır hatalı olabilir check etmek gerek.
        else:
            ayirici_id_list = self.hucre_2_ayirici_top.get(hucre_id)
            bottom_ayirici_id = self.hucre_2_ayirici_bottom.get(hucre_id)

        return ayirici_id_list, bottom_ayirici_id, tek_bara_mi

    def baslangic_setter(
        self,
        path,
        source_ayirici_id,
        bottom_ayirici_id,
        tablo,
        tek_bara_mi,
    ):
        source_node = None
        bottom_ayirici_coord = self.ayirici_id_2_coord.get(bottom_ayirici_id)
        source_ayirici_coord = self.ayirici_id_2_coord.get(source_ayirici_id)
        anahtar_durumu = self.ayirici_2_normal_ana_dict.get(source_ayirici_id, 0)
        if tek_bara_mi == 1:
            if bottom_ayirici_id != source_ayirici_id:
                # tek bara merkez ve aynı hucrede 2 ayırıcı var
                if bottom_ayirici_coord in path:
                    source_node = bottom_ayirici_coord
                    tablo.append(
                        (source_ayirici_id, bottom_ayirici_id, 0, [], anahtar_durumu)
                    )
                else:
                    # error log write (tabloya ekle)
                    pass
            elif bottom_ayirici_id == source_ayirici_id:
                # tek bara merkez ve aynı hucrede 1 ayırıcı var
                source_node = bottom_ayirici_coord
            else:
                source_node = None
        elif tek_bara_mi == 0:
            print("2.5 bara id", source_ayirici_id)
            if bottom_ayirici_coord in path:
                source_node = bottom_ayirici_coord
                tablo.append(
                    (source_ayirici_id, bottom_ayirici_id, 0, [], anahtar_durumu)
                )
                print("heey id ve id", source_ayirici_id, bottom_ayirici_id)
            elif bottom_ayirici_coord not in path:
                source_node = source_ayirici_coord

        return source_node  # this coords is to trace queueu

    def pre_process(self, source_node):
        """
        Ayırıcı koordinatının bağlantı verisi yoksa atla
        returns : paths, baglanti_start, baglanti_end
        """
        global fot_text
        # Bu node graph'ta yoksa atla
        if source_node not in self.graph:
            # print(f"Warning: source_node {source_node} not in graph")
            fot_text += f"source node not in graph {source_node} \n"
            return None, None, None

        # Ayırıcı koordinatının bağlantı verisi yoksa atla
        baglanti_coords = self.ayirici_coord_2_baglanti_coord_dict.get(source_node)
        if not baglanti_coords:
            # print(f"Warning: baglanti_coords not found for source_node {source_node}")
            fot_text += f"baglanti_coords not found for source_node {source_node} \n"
            return None, None, None

        baglanti_start = baglanti_coords[0]
        baglanti_end = baglanti_coords[1]
        # Kısa yolları bul (cutoff=50 adım)
        paths = nx.single_source_shortest_path(
            self.graph, source=source_node, cutoff=50
        )
        return (
            paths,
            baglanti_start,
            baglanti_end,
        )

    def process_paths_fast(self, source_node_coord, paths, baglanti_start, baglanti_end):
        """
        create_temp_bufferV2 + filter_and_clear_bufferV2 adimlarini tek geciste yapar.

        Eski akisla ayni DataFrame kolonlarini ve filtre semantigini korur:
        - alt merkez adaylari varsa sonlanan hat adaylari yok sayilir.
        - alt merkez icin en kisa, sonlanan hat icin en uzun ham path secilir.
        - path_ids prepare_connection'a liste olarak gider; Excel'e yazim asamasina
          kadar stringe cevrilmez.
        """
        columns = [
            "source_coord",
            "target_coord",
            "path_coord",
            "path_ids",
            "source_ayirici_id",
            "target_ayirici_id",
            "source_merkez_id",
            "target_merkez_id",
        ]

        source_merkez_id = self.ayirici_coord_2_merkez_dict.get(source_node_coord)
        source_ayirici_id = self.ayirici_coord_2_ayirici_id_dict.get(
            source_node_coord
        )

        sonlanan_rows = []
        alt_merkez_rows = []

        for _, path in paths.items():
            if baglanti_start not in path and baglanti_end not in path:
                continue
            if len(path) < 4:
                continue

            target_node_coord = path[-1]
            target_merkez_id = self.ayirici_coord_2_merkez_dict.get(
                target_node_coord
            )

            if target_merkez_id == source_merkez_id:
                continue

            edge_ids = get_path_ids(self.start_end_2_edge_id, path)
            if edge_ids is None:
                self.hata_loglari.append(
                    {
                        "source_node": source_node_coord,
                        "target_node": target_node_coord,
                        "merkez": target_merkez_id,
                        "bilgi": "path icin edge id bulunamadi",
                    }
                )
                continue
            if not is_cable_include(self.hat_edge_ids, edge_ids):
                continue

            target_ayirici_id = self.ayirici_coord_2_ayirici_id_dict.get(
                target_node_coord
            )
            cleaned_edge_ids = [i for i in edge_ids if i in self.hat_edge_ids]
            row = [
                str(source_node_coord),
                str(target_node_coord),
                str(path),
                cleaned_edge_ids,
                source_ayirici_id,
                target_ayirici_id,
                source_merkez_id,
                target_merkez_id,
            ]
            row_length = len(edge_ids)

            if target_node_coord in self.ayirici_coord_set:
                alt_merkez_rows.append((len(alt_merkez_rows), row_length, row))
            else:
                sonlanan_rows.append((len(sonlanan_rows), row_length, row))

        if alt_merkez_rows:
            best_length = min(length for _, length, _ in alt_merkez_rows)
            selected = [
                (index, row)
                for index, length, row in alt_merkez_rows
                if length == best_length
            ]
            rows = [row for _, row in selected]
            index = [index for index, _ in selected]
            return pd.DataFrame(rows, columns=columns, index=index), "alt_merkez"

        if sonlanan_rows:
            best_length = max(length for _, length, _ in sonlanan_rows)
            selected = [
                (index, row)
                for index, length, row in sonlanan_rows
                if length == best_length
            ]
            rows = [row for _, row in selected]
            index = [index for index, _ in selected]
            return pd.DataFrame(rows, columns=columns, index=index), "sonlanan_hat"

        return None, "none"

    def create_temp_bufferV2(
        self, source_node_coord, paths, baglanti_start, baglanti_end
    ):
        # Verileri geçici olarak listelerde tutuyoruz (Hız için)
        sonlanan_rows = []
        alt_merkez_rows = []
        # Sütun yapısı
        columns = [
            "source_coord",
            "target_coord",
            "path_coord",
            "path_ids",
            "source_ayirici_id",
            "target_ayirici_id",
            "source_merkez_id",
            "target_merkez_id",
            # "source_hucre_id",
            # "target_hucre_id",
        ]

        source_merkez_id = self.ayirici_coord_2_merkez_dict.get(source_node_coord)
        for target_node_coord, path in paths.items():
            # 1. Mesafe ve Downstream(baglanti) Kontrolleri
            if baglanti_start not in path and baglanti_end not in path:
                continue
            if len(path) < 4:
                continue

            # source_node_coord = path[0]
            target_node_coord = path[-1]
            # 2. Merkez Bilgileri
            target_merkez_id = self.ayirici_coord_2_merkez_dict.get(target_node_coord)
            # source_merkez_id = self.ayirici_coord_2_merkez_dict.get(source_node_coord)

            if target_merkez_id == source_merkez_id:
                continue

            # 3. Ayırıcı ve Kablo Sorguları
            is_in_ayirici = target_node_coord in self.ayirici_coord_set
            edge_ids = get_path_ids(self.start_end_2_edge_id, path)
            include_cable = is_cable_include(self.hat_edge_ids, edge_ids)

            # 4. ID Bilgilerini Çekme (Hata almamak için .get)
            source_ayirici_id = self.ayirici_coord_2_ayirici_id_dict.get(
                source_node_coord
            )
            target_ayirici_id = self.ayirici_coord_2_ayirici_id_dict.get(
                target_node_coord
            )

            # Satır verisini oluştur
            row = [
                str(source_node_coord),
                str(target_node_coord),
                str(path),
                str(edge_ids),
                source_ayirici_id,
                target_ayirici_id,
                source_merkez_id,
                target_merkez_id,
                # self.ayirici_2_hucre_dict.get(source_ayirici_id),
                # self.ayirici_2_hucre_dict.get(target_ayirici_id),
            ]

            # 5. Sınıflandırma Mantığı
            if (
                not is_in_ayirici and include_cable
            ):  # topraklı ayırıcıları ignore ettiğimiz için sonlanan hatlarda da bunlardan var
                sonlanan_rows.append(row)
            elif is_in_ayirici and include_cable:
                alt_merkez_rows.append(row)

        # 6. Listeleri DataFrame'e Dönüştür ve İşlemleri Yap
        if alt_merkez_rows:
            df = pd.DataFrame(alt_merkez_rows, columns=columns)
            return df, "alt_merkez"
        elif sonlanan_rows:
            df = pd.DataFrame(sonlanan_rows, columns=columns)
            return df, "sonlanan_hat"
        else:
            return pd.DataFrame(columns=columns), "none"

    def filter_and_clear_bufferV2(
        self, source_node_coord, buffer_df, filter_param=None
    ):
        # Boş DataFrame kontrolü
        if (
            buffer_df is None or buffer_df.empty
        ):  # filter paramdan da kontrol edebiliriz

            return None

        # 1. Yol uzunluklarını hesapla (Liste uzunluğu üzerinden)
        # create_temp_buffer içinde str(edge_ids) yaptığın için literal_eval kullanıyoruz
        def get_length(x):
            if isinstance(x, str):
                try:
                    # String halindeki listeyi ([1, 2, 3]) gerçek listeye çevirir
                    return len(ast.literal_eval(x))
                except:
                    return 0
            return len(x) if x is not None else 0

        buffer_df["path_ids_length"] = buffer_df["path_ids"].apply(get_length)

        # 2. Parametreye göre filtreleme mantığını belirle
        if filter_param == "alt_merkez":
            # Alt merkezler için her ayırıcı bazında EN KISA (min) yolu bul
            mask = (
                buffer_df.groupby("source_ayirici_id")["path_ids_length"].transform(
                    "min"
                )
                == buffer_df["path_ids_length"]
            )

        elif filter_param == "sonlanan_hat":
            # Sonlanan hatlar için her ayırıcı bazında EN UZUN (max) yolu bul
            mask = (
                buffer_df.groupby("source_ayirici_id")["path_ids_length"].transform(
                    "max"
                )
                == buffer_df["path_ids_length"]
            )
        else:
            # Eğer parametre gelmezse filtreleme yapmadan devam et
            mask = True
        # Filtreyi uygula
        buffer_new = buffer_df[mask].copy()

        # 3. Temizlik ve Kayıt
        # Geçici uzunluk sütununu kaldırıyoruz
        # target_node_coord = buffer_new["target_coord"]
        # source_merkez_id = self.ayirici_coord_2_merkez_dict.get(source_node_coord)
        # target_merkez_id = self.ayirici_coord_2_merkez_dict.get(target_node_coord)
        def clean_path_ids(path_str):
            p_ids = (
                ast.literal_eval(path_str) if isinstance(path_str, str) else path_str
            )
            # Sadece hat_edge_ids içinde olanları filtrele ve yeni liste yap
            cleaned = [i for i in p_ids if i in self.hat_edge_ids]
            return str(cleaned)

        # Temizlenmiş listeleri DataFrame'e geri yaz
        if "path_ids" in buffer_new.columns:
            buffer_new["path_ids"] = buffer_new["path_ids"].apply(clean_path_ids)

        buffer_new = buffer_new.drop("path_ids_length", axis=1)
        # Excel çıktısı al debugging
        # buffer_new.to_excel("siralanmis.xlsx", index=False)

        return buffer_new

    def prepare_connection_legacy(
        self, source_node, buffer_df, filter_param, tablo, just_between_bays
    ):
        if buffer_df.empty:
            # print("prepare_connection fonk buffer_df bos")
            return None

        # Her satır için ayrı ayrı işle
        all_queue_items = []
        for (
            _,
            row,
        ) in buffer_df.iterrows():
            # bu for sadece 1 kere dönmeli çünkü daha önceki fonksiyonlarda bu dataframe tek satır veri kalacak şekilde bazı işlemlerden geçiyor
            ust_ayirici_id = row["source_ayirici_id"]
            giris_ayirici_id = row["target_ayirici_id"]
            giris_hucre_coord = row[
                "target_coord"
            ]  # bu ayirici coord olabilir bir ara kontrol edeceğim
            path_ids = row["path_ids"]
            alt_merkez_id = row["target_merkez_id"]
            mesafe = self.get_mesafe(path_ids)
            anahtar_durumu = self.ayirici_2_normal_ana_dict.get(ust_ayirici_id)

            # Giriş hücresini ayırıcıdan bul
            giris_hucre_id = None
            if giris_ayirici_id is not None and not pd.isna(giris_ayirici_id):
                giris_hucre_id = self.ayirici_2_hucre_dict.get(int(giris_ayirici_id))

            if filter_param == "sonlanan_hat":
                tablo.append(
                    (
                        ust_ayirici_id,
                        giris_ayirici_id,
                        mesafe,
                        path_ids,
                        anahtar_durumu,
                    )
                )
                just_between_bays.append(
                    (ust_ayirici_id, giris_ayirici_id, mesafe, path_ids, anahtar_durumu)
                )
                continue

            elif filter_param == "alt_merkez":
                if alt_merkez_id == self.root_node_merkez_id:
                    tablo.append(
                        (
                            ust_ayirici_id,
                            giris_ayirici_id,
                            mesafe,
                            path_ids,
                            anahtar_durumu,
                        )
                    )
                    just_between_bays.append(
                        (
                            ust_ayirici_id,
                            giris_ayirici_id,
                            mesafe,
                            path_ids,
                            anahtar_durumu,
                        )
                    )
                    continue
                else:
                    tablo.append(
                        (
                            ust_ayirici_id,
                            giris_ayirici_id,
                            mesafe,
                            path_ids,
                            anahtar_durumu,
                        )
                    )
                    just_between_bays.append(
                        (
                            ust_ayirici_id,
                            giris_ayirici_id,
                            mesafe,
                            path_ids,
                            anahtar_durumu,
                        )
                    )
                    # tek bara merkezler
                    if self.merkez_tek_bara_mi.get(alt_merkez_id) == 1:
                        queue_items = self.trace_merkez_ici_1_bara(
                            giris_ayirici_id, giris_hucre_id, alt_merkez_id, tablo
                        )
                        if queue_items:
                            all_queue_items.extend(queue_items)
                    # tek bara olmayan merkezler, yani 2.5 bara merkez ise alttaki elif blogu calisacak
                    elif self.merkez_tek_bara_mi.get(alt_merkez_id) == 0:
                        queue_items = self.trace_merkez_ici_2_5_bara(
                            giris_hucre_id, tablo, giris_ayirici_id
                        )
                        if queue_items:
                            all_queue_items.extend(queue_items)

        return all_queue_items if all_queue_items else None

    def prepare_connection(
        self, source_node, buffer_df, filter_param, tablo, just_between_bays
    ):
        if buffer_df.empty:
            return None

        all_queue_items = []
        for _, row in buffer_df.iterrows():
            context = self.prepare_connection_context(row)

            if filter_param == "sonlanan_hat":
                self.append_trace_result(tablo, just_between_bays, context)
                continue

            if filter_param == "alt_merkez":
                self.append_trace_result(tablo, just_between_bays, context)
                queue_items = self.get_alt_merkez_queue_items(context, tablo)
                if queue_items:
                    all_queue_items.extend(queue_items)

        return all_queue_items if all_queue_items else None

    def prepare_connection_context(self, row):
        ust_ayirici_id = row["source_ayirici_id"]
        giris_ayirici_id = row["target_ayirici_id"]
        path_ids = row["path_ids"]
        alt_merkez_id = row["target_merkez_id"]

        giris_hucre_id = None
        if giris_ayirici_id is not None and not pd.isna(giris_ayirici_id):
            giris_hucre_id = self.ayirici_2_hucre_dict.get(int(giris_ayirici_id))

        return {
            "ust_ayirici_id": ust_ayirici_id,
            "giris_ayirici_id": giris_ayirici_id,
            "giris_hucre_id": giris_hucre_id,
            "path_ids": path_ids,
            "alt_merkez_id": alt_merkez_id,
            "mesafe": self.get_mesafe(path_ids),
            "anahtar_durumu": self.ayirici_2_normal_ana_dict.get(ust_ayirici_id),
        }

    def append_trace_result(self, tablo, just_between_bays, context):
        trace_row = (
            context["ust_ayirici_id"],
            context["giris_ayirici_id"],
            context["mesafe"],
            context["path_ids"],
            context["anahtar_durumu"],
        )
        tablo.append(trace_row)
        just_between_bays.append(trace_row)

    def get_alt_merkez_queue_items(self, context, tablo):
        alt_merkez_id = context["alt_merkez_id"]
        if alt_merkez_id == self.root_node_merkez_id:
            return []

        if self.merkez_tek_bara_mi.get(alt_merkez_id) == 1:
            return self.trace_merkez_ici_1_bara(
                context["giris_ayirici_id"],
                context["giris_hucre_id"],
                alt_merkez_id,
                tablo,
            )

        if self.merkez_tek_bara_mi.get(alt_merkez_id) == 0:
            return self.trace_merkez_ici_2_5_bara(
                context["giris_hucre_id"], tablo, context["giris_ayirici_id"]
            )

        return []

    def trace_merkez_ici_1_bara(self, giris_ayirici, giris_hucre, giris_merkez, tablo):
        global fot_text, count
        to_add_queue = list()
        giris_bottom_ayirici = self.hucre_tek_bara_bottom_ayirici.get(giris_hucre)
        giris_top_ayiricilar = self.ensure_list(
            self.hucre_tek_bara_top_ayirici.get(giris_hucre, [])
        )
        cikis_hucreleri_list = self.get_exit_bay_list(giris_merkez, giris_hucre)

        if not giris_top_ayiricilar or giris_bottom_ayirici is None:
            self.hata_loglari.append(
                {
                    "source_node": giris_ayirici,
                    "target_node": None,
                    "merkez": giris_merkez,
                    "bilgi": "alt-üst ayirici giriş hücresi ayiricilar eksik (None veya boş)",
                }
            )
            return []

        for giris_top_ayirici in giris_top_ayiricilar:
            if giris_bottom_ayirici != giris_top_ayirici:
                anahtar_durumu = self.ayirici_2_normal_ana_dict.get(
                    giris_bottom_ayirici
                )
                tablo.append(
                    (giris_bottom_ayirici, giris_top_ayirici, 0, [], anahtar_durumu)
                )

            for hucre in cikis_hucreleri_list:
                cikis_bottom_ayirici = self.hucre_tek_bara_bottom_ayirici.get(hucre)
                cikis_top_ayiricilar = self.ensure_list(
                    self.hucre_tek_bara_top_ayirici.get(hucre, [])
                )

                for cikis_top_ayirici in cikis_top_ayiricilar:
                    queue_ayirici_id = self.ayirici_finder_in_path(
                        giris_top_ayirici,
                        cikis_top_ayirici,
                        cikis_bottom_ayirici,
                        giris_merkez,
                        tablo,
                    )
                    if queue_ayirici_id is not None:
                        coord = self.ayirici_id_2_coord.get(queue_ayirici_id)
                        if coord is not None:
                            to_add_queue.append(coord)
                            # print("coord", coord)
                            fot_text += f"{coord} - merkez:{giris_merkez} - giris_hucre:{giris_hucre}, giris_top_ayirici:{giris_top_ayirici}  \n"
                            count += 1
                            if count % 2000 == 0:
                                with open(f"fot_text_{count}.txt", "a") as f:
                                    f.write(fot_text)
                                fot_text = ""

        return list(set(to_add_queue))

    def ayirici_finder_in_path(
        self,
        source_ayirici,
        cikis_top_ayirici,
        cikis_bottom_ayirici,
        giris_merkez,
        tablo,
    ):
        ayirici_list = list()
        queue_ayiricisi = None

        if cikis_top_ayirici is None:
            self.hata_loglari.append(
                {
                    "source_node": source_ayirici,
                    "target_node": None,
                    "merkez": giris_merkez,
                    "bilgi": "cikis hucresi top ayirici yok",
                }
            )
            return None

        if cikis_top_ayirici == cikis_bottom_ayirici:
            queue_ayiricisi = cikis_top_ayirici
            path = self.shortest_path_safe(source_ayirici, cikis_top_ayirici)

        elif (
            cikis_top_ayirici != cikis_bottom_ayirici
            and cikis_bottom_ayirici is not None
        ):
            queue_ayiricisi = cikis_bottom_ayirici
            path = self.shortest_path_safe(source_ayirici, cikis_bottom_ayirici)
        else:
            path = None

        if path is None:
            return queue_ayiricisi

        for ayirici_coord in path:
            if ayirici_coord in self.ayirici_coord_set:
                ayirici_id = self.ayirici_coord_2_ayirici_id_dict.get(ayirici_coord)
                if self.ayirici_2_merkez_dict.get(ayirici_id) != giris_merkez:
                    self.hata_loglari.append(
                        {
                            "source_node": source_ayirici,
                            "target_node": cikis_top_ayirici,
                            "merkez": giris_merkez,
                            "bilgi": "tek bara merkez içinde hücreler arası trace path yanlışlık var !!! önemli hata",
                        }
                    )
                else:
                    ayirici_list.append(ayirici_id)

        if (
            cikis_top_ayirici != cikis_bottom_ayirici
            and len(ayirici_list) >= 2
            and ayirici_list[-2] != cikis_top_ayirici
        ):
            self.hata_loglari.append(
                {
                    "source_node": source_ayirici,
                    "target_node": cikis_bottom_ayirici,
                    "merkez": giris_merkez,
                    "bilgi": "cikis alt-ust ayirici farklı ama ayirici_list sondan 2. cikis top ayirici degil anormal",
                }
            )

        for i in range(len(ayirici_list) - 1):
            anahtar_durumu = self.ayirici_2_normal_ana_dict.get(ayirici_list[i])
            tablo.append(
                (ayirici_list[i], ayirici_list[i + 1], 0, None, anahtar_durumu)
            )

        return queue_ayiricisi

    def trace_merkez_ici_2_5_bara(self, giris_hucresi, tablo, merkeze_giris_ayirici):
        """lorem ipsum"""
        global fot_text
        to_add_queue = list()
        merkez = self.hucre_2_merkez.get(giris_hucresi)  # "hucre_2_merkez_dict"
        if merkez is None:
            # print(f"HATA: Hücre {giris_hucresi} için merkez bulunamadı!")
            fot_text += f"merkez bulunamadı, giris_hucresi: {giris_hucresi} \n"
            return

        giris_top_ayiricilar = self.ensure_list(
            self.hucre_2_ayirici_top.get(giris_hucresi, [])
        )

        for ayirici_1 in giris_top_ayiricilar:
            anahtar_durumu = self.ayirici_2_normal_ana_dict.get(merkeze_giris_ayirici)
            tablo.append((merkeze_giris_ayirici, ayirici_1, 0, None, anahtar_durumu))
            bara_no_1 = self.ayirici_2_bara_no.get(
                ayirici_1
            )  # "ayirici_2_bara_no_dict"
            cikis_hucreleri_list = self.get_exit_bay_list(merkez, giris_hucresi)

            for cikis_hucresi in cikis_hucreleri_list:
                cikis_bottom_ayirici_to_trace = self.hucre_2_ayirici_bottom.get(
                    cikis_hucresi
                )
                # === SENARYO 1: Doğrudan aynı bara üzerinden ===
                bara_no_2, ayirici_2 = self.get_bara_and_ayirici(
                    bara_no_1, cikis_hucresi
                )
                if ayirici_2 is not None:
                    coord_path = self.shortest_path_safe(ayirici_1, ayirici_2)
                    if coord_path is not None:
                        # pid = get_path_ids(coord_path) merkez içinde path ve mesafe gereksiz
                        anahtar_durumu = self.ayirici_2_normal_ana_dict.get(
                            merkeze_giris_ayirici
                        )
                        tablo.append((ayirici_1, ayirici_2, 0, [], anahtar_durumu))
                    else:
                        pass

                # === SENARYO 2: Bağlama hücresi üzerinden ===
                baglama_hucreleri = self.get_baglama_bays(merkez)

                for baglama_hucresi in baglama_hucreleri:
                    baglama_bara_2, baglama_ayirici_2 = self.get_bara_and_ayirici(
                        bara_no_1, baglama_hucresi
                    )
                    if baglama_ayirici_2 is None:
                        continue
                    baglama_ayiricilar = self.ensure_list(
                        self.hucre_2_ayiricilar_abb_id_dict.get(baglama_hucresi, [])
                    )
                    for baglama_ayirici_3 in baglama_ayiricilar:
                        if baglama_ayirici_3 == baglama_ayirici_2:
                            continue
                        baglama_bara_3 = self.ayirici_2_bara_no.get(baglama_ayirici_3)
                        if baglama_bara_3 is None:
                            continue
                        if self.bara_no_match(baglama_bara_3, bara_no_1):
                            continue
                        ayirici_4 = self.get_cikis_baglama_ayirici(
                            baglama_bara_3, cikis_hucresi
                        )
                        if ayirici_4 is None:
                            continue

                        cp1 = self.shortest_path_safe(ayirici_1, baglama_ayirici_2)
                        cp3 = self.shortest_path_safe(baglama_ayirici_3, ayirici_4)
                        if cp1 is None or cp3 is None:
                            continue

                        anahtar_durumu = self.ayirici_2_normal_ana_dict.get(ayirici_1)
                        tablo.append(
                            (ayirici_1, baglama_ayirici_2, 0, [], anahtar_durumu)
                        )

                        anahtar_durumu = self.ayirici_2_normal_ana_dict.get(
                            baglama_ayirici_2
                        )
                        tablo.append(
                            (
                                baglama_ayirici_2,
                                baglama_ayirici_3,
                                0,
                                [],
                                anahtar_durumu,
                            )
                        )

                        anahtar_durumu = self.ayirici_2_normal_ana_dict.get(
                            baglama_ayirici_3
                        )
                        tablo.append(
                            (baglama_ayirici_3, ayirici_4, 0, [], anahtar_durumu)
                        )

                if cikis_bottom_ayirici_to_trace is not None:
                    coord = self.ayirici_id_2_coord.get(cikis_bottom_ayirici_to_trace)
                    if coord is not None:
                        to_add_queue.append(coord)

        return list(set(to_add_queue))

    def get_exit_bay_list(self, merkez, giris_hucresi):
        """Merkezdeki çıkış hücrelerini döndürür (giriş hücresi ve çıkış olmayan hücreler hariç)."""
        bays = self.ensure_list(self.m2h.get(merkez, []))
        return [
            b for b in bays if b != giris_hucresi and self.hucre_2_cikis.get(b, 0) == 1
        ]

    def get_bara_and_ayirici(self, bara_no_1, hucre_id):
        """Hücredeki top ayırıcılardan bara_no_1 ile eşleşeni bul.
        Top ayırıcı yoksa (bağlama hücreleri gibi) tüm ayırıcılara fallback yapar."""
        top_list = self.ensure_list(self.hucre_2_ayirici_top.get(hucre_id))
        if not top_list:
            top_list = self.ensure_list(
                self.hucre_2_ayiricilar_abb_id_dict.get(hucre_id)
            )
        for j in top_list:
            temp_bn = self.ayirici_2_bara_no.get(j)
            if self.bara_no_match(temp_bn, bara_no_1):
                return temp_bn, j
        return None, None

    def get_baglama_bays(self, merkez):
        """Merkezdeki bağlama (coupling) hücrelerini döndürür."""
        bays = self.ensure_list(self.m2h.get(merkez, []))
        return [b for b in bays if self.hucre_2_coupling.get(b, 0) == 1]

    def get_cikis_baglama_ayirici(self, bara_no, cikis_hucre):
        """Çıkış hücresindeki top ayırıcılardan bara_no ile eşleşeni bul."""
        top_list = self.ensure_list(self.hucre_2_ayirici_top.get(cikis_hucre))
        for j in top_list:
            temp_bn = self.ayirici_2_bara_no.get(j)
            if self.bara_no_match(temp_bn, bara_no):
                return j
        return None

    def ensure_list(self, val):
        if val is None:
            return []
        return val if isinstance(val, list) else [val]

    def bara_no_match(self, bn1, bn2):
        return bool(self.normalize_bara_no(bn1) & self.normalize_bara_no(bn2))

    def shortest_path_safe(self, ayirici_id_1, ayirici_id_2):
        """ID bazlı shortest path. Koordinata çevirip hesaplar."""
        c1 = self.ayirici_id_2_coord.get(ayirici_id_1)
        c2 = self.ayirici_id_2_coord.get(ayirici_id_2)
        if c1 is None or c2 is None or c1 not in self.graph or c2 not in self.graph:
            return None
        try:
            return nx.shortest_path(self.graph, source=c1, target=c2)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def normalize_bara_no(self, bn):
        if bn is None:
            return set()
        if isinstance(bn, list):
            return set(str(x) for x in bn)
        return {str(bn)}

    def get_mesafe(self, path_ids):
        # 2 node arasındaki mesafe bulucu
        if path_ids is None:
            return 0
        if isinstance(path_ids, str):
            try:
                path_ids = ast.literal_eval(path_ids)
            except Exception:
                return 0

        uzunluk = 0
        for i in path_ids:
            if i in self.hat_edge_ids:
                uzunluk += self.hat_mesafe_dict[i]
        return uzunluk

    def get_ayirici_ids_in_path(self, path):
        # path içindeki i'leri dön, eğer i sözlüğün anahtarlarında varsa listeye ekle
        key = path.key
        path = path.value
        return [i for i in path if i in self.ayirici_id_2_coord]

    def create_connection_node_list(
        self, paths
    ):  # paths contains that return value of networkx.shortest_path function
        to_coord, path = paths.items()
        from_id = path[0]
        to_id = path[-1]

    def export_nodes_to_excel(self, filename="graph_nodes_export.xlsx"):
        """
        Graphtaki tüm nodeları Excel dosyasına aktarır.

        Parameters:
        -----------
        filename : str
            Çıkış Excel dosyasının adı (varsayılan: "nodes_export.xlsx")
        """
        if self.graph is None:
            print("Error: Graph oluşturulmamış. Önce make_graph() metodunu çalıştırın.")
            return False

        try:
            # Nodeları listele
            nodes_list = list(self.graph.nodes())

            # Node'lar tuple veya coordinate ise, onları ayrı sütunlara ayır
            nodes_data = []
            for node in nodes_list:
                if isinstance(node, tuple) and len(node) == 2:
                    # Koordinat tipindeki node (x, y)
                    node_id = self.ayirici_coord_2_ayirici_id_dict.get(node, str(node))
                    nodes_data.append(
                        {
                            "Node_ID": node_id,
                            "X_Coordinate": node[0],
                            "Y_Coordinate": node[1],
                            "Node_Type": (
                                "Ayirici"
                                if node in self.ayirici_coord_2_ayirici_id_dict
                                else "Coordinate"
                            ),
                        }
                    )
                else:
                    # Diğer tipte node (genellikle ID)
                    nodes_data.append(
                        {
                            "Node_ID": node,
                            "X_Coordinate": None,
                            "Y_Coordinate": None,
                            "Node_Type": "ID",
                        }
                    )

            # DataFrame oluştur ve Excel'e kaydet
            df = pd.DataFrame(nodes_data)
            df.to_excel(filename, index=False)
            print(f"✓ {len(nodes_list)} adet node Excel'e aktarıldı: {filename}")
            return True

        except Exception as e:
            print(f"Error: Excel export sırasında hata oluştu: {str(e)}")
            return False

    def export_nodes_to_text(self, filename="nodes_export.txt"):
        """
        Graphtaki tüm nodeları metin dosyasına aktarır.

        Parameters:
        -----------
        filename : str
            Çıkış metin dosyasının adı (varsayılan: "nodes_export.txt")
        """
        if self.graph is None:
            print("Error: Graph oluşturulmamış. Önce make_graph() metodunu çalıştırın.")
            return False

        try:
            nodes_list = list(self.graph.nodes())

            with open(filename, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write(f"NODE EXPORT - Toplam {len(nodes_list)} node\n")
                f.write("=" * 60 + "\n\n")

                # Node tipine göre kategorize et
                coordinate_nodes = []
                id_nodes = []

                for node in sorted(nodes_list):
                    if isinstance(node, tuple) and len(node) == 2:
                        coordinate_nodes.append(node)
                    else:
                        id_nodes.append(node)

                # Koordinat nodeları yaz
                if coordinate_nodes:
                    f.write(f"COORDINATE NODELAR ({len(coordinate_nodes)} adet):\n")
                    f.write("-" * 60 + "\n")
                    for i, node in enumerate(coordinate_nodes, 1):
                        f.write(f"{i:4d}. {node}\n")
                    f.write("\n")

                # ID nodeları yaz
                if id_nodes:
                    f.write(f"ID NODELAR ({len(id_nodes)} adet):\n")
                    f.write("-" * 60 + "\n")
                    for i, node in enumerate(id_nodes, 1):
                        f.write(f"{i:4d}. {node}\n")
                    f.write("\n")

                f.write("=" * 60 + "\n")
                f.write(f"Toplam Node Sayısı: {len(nodes_list)}\n")
                f.write("=" * 60 + "\n")

            print(
                f"✓ {len(nodes_list)} adet node metin dosyasına aktarıldı: {filename}"
            )
            return True

        except Exception as e:
            print(f"Error: Metin dosyası export sırasında hata oluştu: {str(e)}")
            return False

    def export_nodes_to_csv(self, filename="nodes_export.csv"):
        """
        Graphtaki tüm nodeları CSV dosyasına aktarır.

        Parameters:
        -----------
        filename : str
            Çıkış CSV dosyasının adı (varsayılan: "nodes_export.csv")
        """
        if self.graph is None:
            print("Error: Graph oluşturulmamış. Önce make_graph() metodunu çalıştırın.")
            return False

        try:
            nodes_list = list(self.graph.nodes())

            # Node'lar tuple veya coordinate ise, onları ayrı sütunlara ayır
            nodes_data = []
            for node in nodes_list:
                if isinstance(node, tuple) and len(node) == 2:
                    nodes_data.append(
                        {
                            "Node_ID": str(node),
                            "X": node[0],
                            "Y": node[1],
                            "Type": "Coordinate",
                        }
                    )
                else:
                    nodes_data.append(
                        {"Node_ID": str(node), "X": "", "Y": "", "Type": "ID"}
                    )

            df = pd.DataFrame(nodes_data)
            df.to_csv(filename, index=False, encoding="utf-8")
            print(f"✓ {len(nodes_list)} adet node CSV'ye aktarıldı: {filename}")
            return True

        except Exception as e:
            print(f"Error: CSV export sırasında hata oluştu: {str(e)}")
            return False


if __name__ == "__main__":
    # sarıyer abb int id 144725
    graph = Graph()
    graph.init_dicts()
    graph.make_graph()
    # graph.export_nodes_to_excel()

    graph.search_and_create_tree(
        304374
    )  # 301455 5145281 = sonlanan,  5145265=kablo yok, 305331=kablo içermeyen

    # Hata loglarını Excel'e aktar
    if graph.hata_loglari:
        hata_df = pd.DataFrame(graph.hata_loglari)
        hata_df.to_excel("hata_loglari.xlsx", index=False)
        print(
            f"[{len(graph.hata_loglari)}] adet hata/uyarı tespit edildi. 'hata_loglari.xlsx' dosyasına kaydedildi."
        )
    else:
        print(
            "Sistemde mantıksal bir hata logu (alt/üst ayırıcı problemi vs.) tespit edilmedi."
        )
