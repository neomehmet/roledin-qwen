# GIS-Based Electrical Substation Graph Analysis

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: Private](https://img.shields.io/badge/license-Private-red.svg)](LICENSE)

Elektrik trafo merkezlerindeki şalt sahalarının GIS verilerini kullanarak elektriksel bağlantı graflarını oluşturan ve analiz eden gelişmiş bir araç.

## 📋 İçindekiler

- [Genel Bakış](#-genel-bakış)
- [Özellikler](#-özellikler)
- [Kurulum](#-kurulum)
- [Kullanım](#-kullanım)
- [Proje Yapısı](#-proje-yapısı)
- [Yapılandırma](#️-yapılandırma)
- [Çıktılar](#-çıktılar)
- [Teknik Detaylar](#-teknik-detaylar)
- [Sorun Giderme](#-sorun-giderme)

## 📊 Genel Bakış

Bu proje, Coğrafi Bilgi Sistemleri (CBS/GIS) verilerinden elektrik şebekesi bileşenlerinin (bara, hücre, kesici, ayırıcı, bağlantı) uzamsal ilişkilerini çıkarır ve **graph teorisi** ile modelleyerek enerji akış yollarını analiz eder.

### Temel İş Akışı

```mermaid
graph LR
    A[GIS Shapefiles] --> B[couplateV2.py<br/>Spatial Join]
    B --> C[Excel Lookup Tables]
    C --> D[import_dicts.py<br/>Dictionary Load]
    D --> E[graph.py<br/>Graph Analysis]
    E --> F[Enerji Akış Yolları]
```

## ✨ Özellikler

- ✅ **GIS Tabanlı Analiz**: Spatial join işlemleri ile otomatik bağlantı keşfi
- ✅ **Graph Modelleme**: NetworkX ile elektriksel bağlantı grafları
- ✅ **Enerji Akış Analizi**: Besleme yolları ve bağlantı noktalarının tespiti
- ✅ **Akıllı Filtreleme**: Hücre tiplerine göre otomatik eleme
- ✅ **Mesafe Hesaplama**: Hat uzunlukları ve kablo takibi
- ✅ **Cache Sistemi**: Excel tabanlı lookup dictionary'ler ile hızlı yeniden yükleme
- ✅ **Hata Tespiti**: Bağlantısız node'ların ve anomalilerin otomatik tespiti
- ✅ **WKT Geometry Desteği**: Shapely ile geometri işleme

## 🔧 Kurulum

### Gereksinimler

- Python 3.8+
- pip paket yöneticisi

### Bağımlılıkları Yükle

```bash
pip install geopandas pandas networkx shapely openpyxl psutil
```

### Alternatif: requirements.txt

```bash
pip install -r requirements.txt
```

## 🚀 Kullanım

### 1. Lookup Dictionary'lerini Oluştur

GIS shapefile dosyalarını işleyerek lookup tablolarını oluşturun:

```bash
python couplateV2.py
```

**Not:** GIS dosyalarının `..\GIS\` dizininde olduğundan emin olun.

### 2. Graph Analizi Yap

Oluşturulan lookup tablolarını kullanarak graph analizi gerçekleştirin:

```bash
python graph.py
```

### 3. (Opsiyonel) Dictionary'leri Tekrar Yükle

Mevcut Excel dosyalarından dictionary'leri yüklemek için:

```python
import import_dicts
dicts = import_dicts.load_and_unpack_all()
```

## 🗂️ Proje Yapısı

```
/workspace/
├── couplateV2.py           # GIS verilerini işler, lookup tabloları oluşturur
├── graph.py                # Graph oluşturma ve analiz modülü
├── import_dicts.py         # Excel'den dictionary yükleme modülü
├── README.md               # Bu dokümantasyon dosyası
├── look-ups/               # Oluşturulan lookup Excel dosyaları
│   ├── bara_*.xlsx
│   ├── ayirici_*.xlsx
│   ├── kesici_*.xlsx
│   ├── hucre_*.xlsx
│   ├── merkez_*.xlsx
│   └── baglanti_*.xlsx
└── requirements.txt        # Python bağımlılıkları (opsiyonel)
```

### Dosya Açıklamaları

| Dosya | Açıklama |
|-------|----------|
| `couplateV2.py` | GIS shapefile'ları okur, spatial join yapar, 6 Excel lookup dosyası oluşturur |
| `graph.py` | NetworkX graph modeli kurar, enerji akış yollarını bulur, analiz raporları üretir |
| `import_dicts.py` | Excel lookup dosyalarını Python dictionary'lerine dönüştürür, WKT parse eder |

## ⚙️ Yapılandırma

### GIS Dosya Yolları

`couplateV2.py` içindeki dosya yollarını projenize göre düzenleyin:

```python
MERKEZ_PATH = r"..\GIS\LGC_MERKEZ.shp"
HAT_PATH = r"..\GIS\H_ENERJI_NAKIL_HATTI.shp"
HUCRE_PATH = r"..\GIS\T_HUCRE.shp"
BARA_PATH = r"..\GIS\T_OG_BARA.shp"
KESICI_PATH = r"..\GIS\T_OG_KESICI.shp"
AYIRICI_PATH = r"..\GIS\T_OG_AYIRICI.shp"
T_OG_KABLO_BAGLANTISI_PATH = r"..\GIS\T_OG_KABLO_BAGLANTISI.shp"
```

### Filtre Ayarları

`graph.py` içinde atlanacak hücre tiplerini yapılandırın:

```python
SKIP_HUCRE_TYPES = {
    "BARA BAGLAMA (KUPLAJ) HUCRESI",
    "GERILIM KORUMA HUCRESI",
    "TRANSFORMATOR KORUMA HUCRESI",
    "AKIM OLCU HUCRESI",
    "AKIM GERILIM HUCRESI",
}
```

### Gerilim Seviyesi

Proje varsayılan olarak **34.5 kV** gerilim seviyesine odaklanmıştır. Bu değeri ilgili scriptlerde değiştirebilirsiniz.

## 📤 Çıktılar

### Lookup Excel Dosyaları

`look-ups/` dizininde oluşturulan 6 ana lookup dosyası:

| Dosya | İçerik |
|-------|--------|
| `bara_*.xlsx` | Bara-Hücre-Bara bağlantı ilişkileri |
| `ayirici_*.xlsx` | Ayırıcı konum ve durum bilgileri |
| `kesici_*.xlsx` | Kesici bağlantı bilgileri |
| `hucre_*.xlsx` | Hücre detayları ve tipleri |
| `merkez_*.xlsx` | Trafo merkezi bilgileri |
| `baglanti_*.xlsx` | Kablo bağlantı noktaları |

### Ek Çıktılar

- `bara_2_baglanti.xlsx` - Bara-Bağlantı spatial join sonucu
- `ayirici_anahtar_status.xlsx` - Ayırıcı anahtarlama durumları
- `baglanti_processed.xlsx` - İşlenmiş bağlantı verisi

## 🔬 Teknik Detaylar

### Veri Tipleri

| GIS Katmanı | Geometri Tipi | Açıklama |
|-------------|---------------|----------|
| MERKEZ | Polygon | Trafo merkezi sınırları |
| HUCRE | Polygon | Hücre alanları |
| BARA | LineString | Bara çizgileri |
| HAT | LineString | Enerji nakil hatları |
| KESICI | Point | Kesici noktaları |
| AYIRICI | Point | Ayırıcı noktaları |
| BAGLANTI | Point | Kablo bağlantı noktaları |

### Graph Yapısı

- **Nodes**: Koordinat bazlı bağlantı noktaları
- **Edges**: Elektriksel bağlantılar (edge ID'ler ile takip edilir)
- **Edge Attributes**: Tip (kablo/hat), uzunluk, bağlantı bilgileri

### Performans Optimizasyonları

- Heavy spatial join hesaplamaları Excel'de cache'lenir
- WKT geometry string'leri güvenli parsing ile işlenir
- NetworkX ile optimize edilmiş graph algoritmaları
- Pandas DataFrame operasyonları ile hızlı veri işleme

## 🐛 Sorun Giderme

### Yaygın Hatalar

**1. GIS dosyaları bulunamadı**
```
FileNotFoundError: ...LGC_MERKEZ.shp
```
**Çözüm:** `couplateV2.py` içindeki dosya yollarını kontrol edin.

**2. ModuleNotFoundError**
```
ModuleNotFoundError: No module named 'geopandas'
```
**Çözüm:** `pip install geopandas pandas networkx shapely openpyxl psutil`

**3. Empty DataFrame after filtering**
```
UserWarning: Geometry is in a geographic CRS...
```
**Çözüm:** GIS verilerinizin koordinat sistemini (CRS) kontrol edin.

### Log Çıktıları

Scriptler çalışırken detaylı log mesajları üretir:
- GIS verilerinin okunma durumu
- Spatial join işlem adımları
- Graph oluşturma süreci
- Hata ve uyarı mesajları

## 📝 Notlar

- Proje **34.5 kV** gerilim seviyesindeki hücrelere odaklanmıştır
- Bazı özel hücre tipleri (barabaralama, gerilim koruma, vb.) analiz dışı bırakılabilir
- Geometry verileri **WKT (Well-Known Text)** formatında işlenir
- Büyük veri setleri için yeterli RAM gereklidir (8GB+ önerilir)

## 📄 Lisans

Bu proje **özel kullanım** içindir. Tüm hakları saklıdır.

## 👥 Katkıda Bulunma

Bu proje kapalı kaynaklıdır ve dış katkıya açık değildir.

## 📞 İletişim

Sorularınız için proje sahibi ile iletişime geçiniz.

---

**Son Güncelleme:** Haziran 2024  
**Proje Sürümü:** 2.0