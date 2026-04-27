# Sosyal Medya Platformu - AI Destekli İçerik Etiketleme

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-19.2.4-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135.2-green.svg)](https://fastapi.tiangolo.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9.3-blue.svg)](https://www.typescriptlang.org/)

Modern, gerçek zamanlı sosyal medya platformu. Yapay zeka destekli otomatik içerik etiketleme, gerçek zamanlı mesajlaşma ve etkileşim özellikleri ile kullanıcı deneyimini geliştirir.

## ✨ Özellikler

### 🔐 Kimlik Doğrulama & Güvenlik
- JWT tabanlı güvenli giriş/çıkış sistemi
- Refresh token desteği
- Şifre hash'leme (bcrypt)
- Güvenli API endpoints

### 📱 Sosyal Medya Özellikleri
- **Gönderiler**: Metin, resim ve medya içeriği paylaşımı
- **Beğeni Sistemi**: Gönderilere beğeni ekleme/çıkarma
- **Yorumlar**: Gönderilere yorum yapma ve etkileşim
- **Takip Sistemi**: Kullanıcıları takip etme/çıkarma
- **Hikayeler**: Geçici içerik paylaşımı
- **Bildirimler**: Gerçek zamanlı bildirim sistemi

### 🤖 Yapay Zeka Entegrasyonu
- **Otomatik Etiketleme**: OpenAI GPT kullanarak gönderi içeriğine akıllı etiketler ekleme
- **Konu Tespiti**: İçerik analizi ile ilgili konuların belirlenmesi

### ⚡ Gerçek Zamanlı Özellikler
- **WebSocket Bağlantısı**: Anlık mesajlaşma ve bildirimler
- **Push Notifications**: Tarayıcı bildirimleri
- **Canlı Sohbet**: Kullanıcılar arası gerçek zamanlı mesajlaşma

### 🎨 Kullanıcı Arayüzü
- **Responsive Tasarım**: Mobil ve masaüstü uyumlu
- **Modern UI**: Temiz ve kullanıcı dostu arayüz
- **Gece/Gündüz Modu**: Ambient light adaptasyonu (donanım entegrasyonu ile)
- **Erişilebilirlik**: WCAG uyumlu tasarım

## 🛠️ Teknoloji Stack'i

### Backend
- **Python 3.8+**
- **FastAPI**: Yüksek performanslı REST API framework
- **SQLAlchemy**: ORM ve veritabanı işlemleri
- **Alembic**: Veritabanı migrasyonları
- **WebSocket**: Gerçek zamanlı iletişim
- **OpenAI API**: Yapay zeka etiketleme

### Frontend
- **React 19.2.4**: Modern JavaScript framework
- **TypeScript 5.9.3**: Tip güvenliği
- **Vite**: Hızlı geliştirme ve build tool
- **Zustand**: State management
- **Axios**: HTTP client
- **React Router**: Sayfa yönlendirme

### Veritabanı
- **SQLite**: Geliştirme ortamı
- **PostgreSQL**: Üretim ortamı desteği

### Güvenlik & Kalite
- **pytest**: Unit testing
- **ESLint**: Kod kalitesi
- **Pre-commit hooks**: Kod standartları

## 🚀 Kurulum

### Ön Gereksinimler

- Python 3.8+
- Node.js 18+
- Git

### Backend Kurulumu

```bash
# Repository'yi klonlayın
git clone https://github.com/DenizDogrul/Social-Media-Platform-With-AI.git
cd Social-Media-Platform-With-AI

# Backend dizinine gidin
cd backend

# Virtual environment oluşturun
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Bağımlılıkları yükleyin
pip install -r requirements.txt

# Environment variables'ları ayarlayın
cp .env.example .env
# .env dosyasını düzenleyin (API keys, veritabanı ayarları)
```

### Frontend Kurulumu

```bash
# Frontend dizinine gidin
cd frontend

# Bağımlılıkları yükleyin
npm install

# Geliştirme sunucusunu başlatın
npm run dev
```

### Veritabanı Kurulumu

```bash
# Backend dizininde
cd backend

# Veritabanı migrasyonlarını çalıştırın
alembic upgrade head

# Demo verilerini yükleyin (opsiyonel)
python scripts/seed_demo.py
```

## 🔧 Yapılandırma

### Environment Variables

Backend için `.env` dosyası oluşturun:

```env
# Güvenlik
SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Veritabanı
DATABASE_URL=sqlite:///./app.db

# OpenAI API
OPENAI_API_KEY=sk-your-openai-api-key

# Diğer ayarlar
APP_ENV=development
DEBUG=true
```

Frontend için `.env` dosyası oluşturun:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## 📖 Kullanım

### Geliştirme Ortamı

```bash
# Backend'i başlatın
cd backend
uvicorn app.main:app --reload

# Frontend'i başlatın
cd frontend
npm run dev
```

Uygulamaya erişim:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Dokümantasyonu: http://localhost:8000/docs

### Üretim Ortamı

```bash
# Backend build
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend build
cd frontend
npm run build
npm run preview
```

## 📚 API Dokümantasyonu

### Ana Endpoints

#### Kimlik Doğrulama
- `POST /auth/login` - Kullanıcı girişi
- `POST /auth/register` - Kullanıcı kaydı
- `POST /auth/refresh` - Token yenileme
- `POST /auth/logout` - Çıkış

#### Gönderiler
- `GET /posts` - Gönderileri listele
- `POST /posts` - Yeni gönderi oluştur
- `GET /posts/{id}` - Gönderi detayı
- `PUT /posts/{id}` - Gönderi güncelle
- `DELETE /posts/{id}` - Gönderi sil

#### Etkileşim
- `POST /posts/{id}/like` - Gönderi beğen
- `DELETE /posts/{id}/like` - Beğeniyi kaldır
- `POST /posts/{id}/comments` - Yorum ekle
- `GET /posts/{id}/comments` - Yorumları listele

#### Gerçek Zamanlı
- `WebSocket /ws/notifications` - Bildirimler
- `WebSocket /ws/messages` - Mesajlaşma

Detaylı API dokümantasyonu için: http://localhost:8000/docs

## 🧪 Testler

```bash
# Backend testlerini çalıştırın
cd backend
pytest tests/ -v

# Frontend testlerini çalıştırın
cd frontend
npm run lint
```

## 🤝 Katkıda Bulunma

1. Fork edin
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit edin (`git commit -m 'Add amazing feature'`)
4. Push edin (`git push origin feature/amazing-feature`)
5. Pull Request oluşturun

### Geliştirme Standartları

- **Kod Kalitesi**: ESLint ve Black kullanımı zorunlu
- **Testler**: Yeni özellikler için test yazın
- **Commit Mesajları**: Anlamlı ve açıklayıcı commit mesajları
- **Dokümantasyon**: Yeni API'ler için dokümantasyon güncelleyin

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.

## 👥 Yazar

**Deniz Doğru** - [GitHub](https://github.com/DenizDogrul)

## 🙏 Teşekkürler

- [FastAPI](https://fastapi.tiangolo.com/) ekibine
- [React](https://reactjs.org/) topluluğuna
- [OpenAI](https://openai.com/) API'sine
- Tüm katkıda bulunanlara

---

⭐ Bu projeyi beğendiyseniz yıldız vermeyi unutmayın!</content>
<parameter name="filePath">c:\Users\Deniz\OneDrive\Masaüstü\tez\README.md