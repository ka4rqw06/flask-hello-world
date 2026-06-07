import os
import time
import threading
import random
import telebot
from google import genai
from google.genai import types
import schedule
from flask import Flask  # <--- Hayalet sunucu için bunu ekledik amk

# =====================================================================
# 🌐 HAYALET WEB SUNUCUSU (Render'ı Bedavaya Kandırma Noktası)
# =====================================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "🔥 CANAVAR AYAKTA AMK, 7/24 PROTOKOLÜ AKTİF!"

def run_flask():
    # Render'ın istediği portu otomatik yakalar
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# =====================================================================
# 🔑 ŞİFRELER GİZLİ BÖLMEDEN OKUNACAK
# =====================================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MY_CHAT_ID = os.environ.get("MY_CHAT_ID")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
ai_client = genai.Client(api_key=GEMINI_API_KEY)

user_memories = {}
SABAH_SAATI = "07:30"
GECE_SAATI = "22:30"

def rastgele_saatleri_guncelle():
    return f"{random.randint(11, 15):02d}:{random.randint(0, 59):02d}", f"{random.randint(16, 21):02d}:{random.randint(0, 59):02d}"

baskin_saati_1, baskin_saati_2 = rastgele_saatleri_guncelle()

KOC_TALIMATI = (
    "Sen Kayra'nın sikiş profesörü kişisel fitness koçusun. Karakterin tamamen Gokalaf ve Ege Fitness kırması. "
    "Sert, disiplinli, gevşekliğe, amcılığa, tembelliğe asla gelemeyen, küfürü ve argoyu sonuna kadar acımadan kullanan bir canavarsın. "
    "Kayra'ya 'aslanım', 'gevşek', 'canavar', 'yavşak' diye hitap et. "
    "Sana yemek veya barkod fotosu atarsa makrosunu sök al, yaramazsa o yemeği kafasına fırlat. "
    "Video atarsa formunu kare kare sikip at, sakatlık riskini sertçe yüzüne vur. "
    "Ses atarsa idmanda ter içinde olduğunu bil, ona göre gaza getir, anasını ağlatsın o demirlerin."
)

def get_user_context(chat_id):
    if chat_id not in user_memories:
        user_memories[chat_id] = []
    return user_memories[chat_id]

def gemini_cevap_uret(chat_id, user_prompt, file_bytes=None, mime_type=None):
    context = get_user_context(chat_id)
    gecmis_metni = "".join([f"{msg['role']}: {msg['content']}\n" for msg in context[-10:]])
    
    contents = [f"{gecmis_metni}Kullanıcı: {user_prompt}"]
    if file_bytes and mime_type:
        contents.append(types.Part.from_bytes(data=file_bytes, mime_type=mime_type))
    
    config = types.GenerateContentConfig(
        system_instruction=KOC_TALIMATI,
        temperature=0.7,
        tools=[types.Tool(google_search=types.GoogleSearch())]
    )
    
    try:
        response = ai_client.models.generate_content(
            model='gemini-1.5-flash',
            contents=contents,
            config=config
        )
        context.append({"role": "Kullanıcı", "content": user_prompt})
        context.append({"role": "Koç", "content": response.text})
        return response.text
    except Exception as e:
        return f"❌ GEMINI BAĞLANTI HATASI AMK: {str(e)}"

@bot.message_handler(commands=['start'])
def start_mesaji(message):
    bot.send_message(message.chat.id, "🔥 RENDER WEB SERVICE'DEN SELAMINALEYKÜM ASLANIM! Bot şu an beleş buluttan uçuyor, sıfır engel! At sesini, fırlat fotonu!")

@bot.message_handler(content_types=['voice'])
def ses_analiz(message):
    try:
        bot.send_message(message.chat.id, "🎧 Sesini dinliyorum yavşak, bekle...")
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        cevap = gemini_cevap_uret(message.chat.id, "Ses kaydı attım, dinle ve koç gibi cevap ver.", file_bytes=downloaded_file, mime_type="audio/ogg")
        bot.send_message(message.chat.id, cevap)
    except Exception as e:
        bot.send_message(message.chat.id, "Ses dosyası çekilemedi amk!")

@bot.message_handler(content_types=['photo'])
def fotograf_analiz(message):
    try:
        bot.send_message(message.chat.id, "👀 Fotoğrafı/Barkodu aldım, saniyede çözüyorum...")
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        caption = message.caption if message.caption else "Bu fotoğrafı/barkodu analiz et koç."
        cevap = gemini_cevap_uret(message.chat.id, caption, file_bytes=downloaded_file, mime_type="image/jpeg")
        bot.send_message(message.chat.id, cevap)
    except Exception as e:
        bot.send_message(message.chat.id, "Fotoğraf çekilemedi amk!")

@bot.message_handler(content_types=['video', 'video_note'])
def video_analiz(message):
    try:
        bot.send_message(message.chat.id, "💪 Seti izliyorum, form kontrolü başladı...")
        file_id = message.video.file_id if message.content_type == 'video' else message.video_note.file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        caption = message.caption if message.caption else "Formumu incele koç."
        cevap = gemini_cevap_uret(message.chat.id, caption, file_bytes=downloaded_file, mime_type="video/mp4")
        bot.send_message(message.chat.id, cevap)
    except Exception as e:
        bot.send_message(message.chat.id, "Video çekilemedi amk!")

@bot.message_handler(func=lambda message: True)
def metin_cevap(message):
    cevap = gemini_cevap_uret(message.chat.id, message.text)
    bot.send_message(message.chat.id, cevap)

def sabah_baskini():
    if MY_CHAT_ID:
        bot.send_message(int(MY_CHAT_ID), "☀️ KALK ULAN KALK AMK! Saat 07:30! Hemen aç karnına tartıl ve kilonu buraya yaz!")

def gece_baskini():
    if MY_CHAT_ID:
        bot.send_message(int(MY_CHAT_ID), "💤 Saat 22:30 oldu yavşak. Telefonu siktir et ve yatağa gir.")

def rastgele_baskin():
    if MY_CHAT_ID:
        mesajlar = [
            "🚨 BASKIN LAN AMCİK! Okulda veya dışarıda diyeti bozdun mu doğruyu söyle?!",
            "🔥 SAĞA SOLA BAKMA KAYRA! Bugün suyunu düzgün içtin mi lan gevşek?!",
            "⚡ GEVŞEKLİK SEZİYORUM! Hemen durum raporu ver orospu çocuğu!"
        ]
        bot.send_message(int(MY_CHAT_ID), random.choice(mesajlar))

def zamanlayici_dongusu():
    global baskin_saati_1, baskin_saati_2
    schedule.every().day.at(SABAH_SAATI).do(sabah_baskini)
    schedule.every().day.at(GECE_SAATI).do(gece_baskini)
    
    def saatleri_sifirla():
        global baskin_saati_1, baskin_saati_2
        schedule.clear('baskin')
        baskin_saati_1, baskin_saati_2 = rastgele_saatleri_guncelle()
        schedule.every().day.at(baskin_saati_1).do(rastgele_baskin).tag('baskin')
        schedule.every().day.at(baskin_saati_2).do(rastgele_baskin).tag('baskin')

    schedule.every().day.at("00:01").do(saatleri_sifirla)
    schedule.every().day.at(baskin_saati_1).do(rastgele_baskin).tag('baskin')
    schedule.every().day.at(baskin_saati_2).do(rastgele_baskin).tag('baskin')

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # Flask sunucusunu arka planda başlat
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Baskın zamanlayıcısını başlat
    t = threading.Thread(target=zamanlayici_dongusu)
    t.daemon = True
    t.start()

    # Telegram botunu sonsuz döngüye sok
    bot.infinity_polling()
