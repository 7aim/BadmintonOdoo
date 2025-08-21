# 🏟️ Volan Sport Management System

Badminton və basketbol üçün tam idman idarəetmə sistemi.

## Xüsusiyyətlər

### 🏸 Badminton İdarəetməsi

#### 1. Müştəri Qeydiyyatı
- ✅ Avtomatik QR kod yaradılması
- ✅ Müştəri məlumatlarının saxlanması
- ✅ Doğum tarixi və əlavə məlumatlar

#### 2. Badminton Satışı ⭐ YENİ
- ✅ **Tez Satış**: Sadə interfeys ilə tez satış
- ✅ **Filial üzrə qiymətlər**: Hər filialın öz qiymətləri
- ✅ **Balans sistemi**: Müştəri hesabında saatların saxlanması
- ✅ **Ödəniş növləri**: Nəğd, Kart, Bank köçürməsi
- ✅ **Balans tarixçəsi**: Bütün əməliyyatların qeydiyyatı

#### 3. Badminton Dərsləri ⭐ YENİ
- ✅ **Dərs qrafiki**: Həftəlik dərs planı
- ✅ **Müəllim təyinatı**: Dərslər üçün müəllim seçimi
- ✅ **İştirak izləmə**: Dərslərə iştirakın qeydiyyatı
- ✅ **QR kod dəstəyi**: Dərslərə QR kod ilə giriş

#### 4. Sessiya İdarəetməsi
- ✅ QR kod oxuma
- ✅ Aktiv sessiyaların izlənməsi
- ✅ Sessiya uzatma imkanı
- ✅ Avtomatik balans çıxılması

### 🏀 Basketbol İdarəetməsi
- ✅ Aylıq üzvlük sistemi
- ✅ Dərs qrafiki
- ✅ İştirak qeydiyyatı
- ✅ Həftəlik dərs hesablaması

### 🔍 QR Scanner
- ✅ QR kod oxuma
- ✅ Avtomatik müştəri tanıma
- ✅ Sessiya başlatma

### ⚙️ Tənzimləmələr
- ✅ **Müştəri axtarışı**: Tez müştəri tapma
- ✅ İdman növləri
- ✅ Filial idarəetməsi
- ✅ Qiymət parametrləri

## İstifadə Qaydası

### Badminton Satışı
1. **Menyu**: Badminton → Satış (Tez)
2. Müştəri seçin
3. Filial seçin
4. Saat sayını daxil edin
5. Ödəniş növünü seçin
6. "Satışı Tamamla" düyməsini basın

### Badminton Dərsi
1. **Menyu**: Badminton → Dərslər
2. Yeni dərs yaradın
3. Müştəri və müəllim seçin
4. Dərs qrafikini əlavə edin
5. Ödənişi qeyd edin

### Sessiya Başlatma
1. **QR kod ilə**: QR Scanner menusundan
2. **Manual**: Badminton → Aktiv Sessiyalar

## Balans Sistemi

### Necə işləyir:
1. Müştəri badminton saatları alır
2. Satışdan sonra müştərinin hesabına saatlar əlavə olunur
3. Sessiya tamamlandıqda balansdan avtomatik çıxılır
4. Bütün əməliyyatlar tarixçədə saxlanır

### Balans yoxlama:
- Müştəri kartında "Badminton Balansı" sahəsi
- Müştəri səhifəsində "Balans Tarixçəsi" tabı

## Texniki Məlumatlar

### Yeni Modellər:
- `badminton.sale` - Badminton satışları
- `badminton.balance.history` - Balans tarixçəsi
- `badminton.lesson` - Badminton dərsləri
- `badminton.lesson.schedule` - Dərs qrafiki
- `badminton.lesson.attendance` - Dərs iştirakları

### Database Dəyişiklikləri:
- `res.partner` modelinə `badminton_balance` sahəsi əlavə edildi
- Yeni sequence-lər əlavə edildi
- Yeni menyu strukuru yaradıldı

## Gələcək İnkişaf
- 🔄 Basketbol balans sistemi
- 📊 Hesabat və analitika
- 📱 Mobil tətbiq inteqrasiyası
- 🔔 Bildirişlər sistemi

---

**Versiyan**: 2.0.0  
**Son yeniləmə**: Avqust 2025