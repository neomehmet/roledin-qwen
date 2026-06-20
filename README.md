# GIS-Based Electrical Substation Graph Analysis

Bu proje, elektrik trafo merkezlerindeki (substation) şalt sahalarının GIS verilerini kullanarak elektriksel bağlantı graflarını oluşturur ve analiz eder.

## 📋 Genel Bakış

Proje, Coğrafi Bilgi Sistemleri (CBS/GIS) verilerinden elektrik şebekesi bileşenlerinin (bara, hücre, kesici, ayırıcı, bağlantı) uzamsal ilişkilerini çıkarır ve bunları graph teorisi ile modelleyerek enerji akış yollarını analiz eder.

## 🗂️ Dosyalar

### Ana Scriptler

- **`couplateV2.py`**: GIS shapefile dosyalarını okuyarak spatial join işlemleri yapar ve lookup dictionary'lerini Excel dosyaları olarak dışa aktarır.
  - Bara-Hücre-Bara bağlantı ilişkilerini kurar
  - 6 adet Excel lookup dosyası oluşturur
  - Spatial join sonuçlarını kaydeder

- **`graph.py`**: Lookup dictionary'lerini kullanarak elektriksel bağlantı graflarını oluşturur ve analiz eder.
  - NetworkX ile graph modelleme
  - Enerji akış yollarının bulunması
  - Bağlantısız node'ların tespiti
  - Hat uzunluğu hesaplama

- **`import_dicts.py`**: Excel'den lookup sözlüklerini yükleyerek Python dictionary'lerine dönüştürür.
  - Heavy spatial join hesaplamalarının tekrarını önler
  - WKT geometry stringlerini parse eder
  - Güvenli veri dönüşümü sağlar

### Çıktı Dosyaları

- `look-ups/` dizininde 6 adet Excel lookup dosyası:
  - `bara_*.xlsx`
  - `ayirici_*.xlsx`
  - `kesici_*.xlsx`
  - `hucre_*.xlsx`
  - `merkez_*.xlsx`
  - `baglanti_*.xlsx`

## 🔧 Gereksinimler

```bash
pip install geopandas pandas networkx shapely openpyxl psutil
```

## 🚀 Kullanım

### 1. Lookup Dictionary'lerini Oluştur

```bash
python couplateV2.py
```

GIS shapefile dosyalarının doğru yolda olduğundan emin olun (`..\GIS\` dizini).

### 2. Graph Analizi Yap

```bash
python graph.py
```

Lookup dictionary'lerini otomatik olarak yükler ve graph analizi gerçekleştirir.

## 📊 Özellikler

- ✅ GIS tabanlı spatial join işlemleri
- ✅ Elektriksel bağlantı graph'ı oluşturma
- ✅ Enerji akış yolu analizi
- ✅ Hücre tiplerine göre filtreleme
- ✅ Hat uzunluğu hesaplama
- ✅ Bağlantısız node tespiti
- ✅ Excel tabanlı lookup cache sistemi

## ⚙️ Yapılandırma

GIS dosya yollarını `couplateV2.py` içindeki ilgili değişkenlerden düzenleyebilirsiniz:

```python
MERKEZ_PATH = r"..\GIS\LGC_MERKEZ.shp"
HAT_PATH = r"..\GIS\H_ENERJI_NAKIL_HATTI.shp"
HUCRE_PATH = r"..\GIS\T_HUCRE.shp"
BARA_PATH = r"..\GIS\T_OG_BARA.shp"
KESICI_PATH = r"..\GIS\T_OG_KESICI.shp"
AYIRICI_PATH = r"..\GIS\T_OG_AYIRICI.shp"
```

## 📝 Notlar

- Proje 34.5 kV gerilim seviyesindeki hücrelere odaklanmıştır
- Bazı hücre tipleri (barabaralama, gerilim koruma, vb.) analiz dışı bırakılabilir
- Geometry verileri WKT formatında işlenir

## 📄 Lisans

Bu proje özel kullanım içindir.