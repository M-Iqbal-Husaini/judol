import telebot
import pickle
import re
import os
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
from tensorflow.keras.callbacks import EarlyStopping # Penting untuk load model

# === KONFIGURASI BOT ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
# Pastikan nama file model dan tokenizer sesuai dengan yang disimpan
MODEL_PATH = "judi.keras"
TOKENIZER_PATH = "judi.pkl"

# === LOAD MODEL & TOKENIZER ===
try:
    # Penting: load_model memerlukan argumen custom_objects jika ada
    # Dalam kasus ini, EarlyStopping tidak perlu dimasukkan
    model = load_model(MODEL_PATH)
    with open(TOKENIZER_PATH, "rb") as f:
        tokenizer = pickle.load(f)
    # Dapatkan max_length dari arsitektur model
    MAX_LEN = model.input_shape[1] 
    print(f"✅ Model dan tokenizer berhasil dimuat. Max length: {MAX_LEN}")
except Exception as e:
    print(f"❌ Error saat memuat model atau tokenizer: {e}")
    exit()

# === INISIALISASI PREPROCESSING (HARUS SAMA DENGAN SAAT PELATIHAN) ===
factory_stemmer = StemmerFactory()
stemmer = factory_stemmer.create_stemmer()
factory_remover = StopWordRemoverFactory()
stopwords_list = factory_remover.get_stop_words()

# === FUNGSI PREDIKSI ===
def complex_clean_text(text):
    text = str(text)
    text = text.lower()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"[^a-zA-Z\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Pastikan stopwords_list sudah didefinisikan sebelumnya
    text = ' '.join([word for word in text.split() if word not in stopwords_list])
    text = stemmer.stem(text)
    return text

def predict_message(message):
    cleaned_message = complex_clean_text(message)
    sequence = tokenizer.texts_to_sequences([cleaned_message])
    padded_sequence = pad_sequences(sequence, maxlen=MAX_LEN, padding='post')
    prob = model.predict(padded_sequence, verbose=0)[0][0]
    return prob

# === KONFIGURASI TELEGRAM BOT ===
bot = telebot.TeleBot(BOT_TOKEN)
THRESHOLD = 0.5  # Ambang batas bisa disesuaikan. 0.5 adalah default yang baik.

@bot.message_handler(func=lambda msg: True)
def handle_message(msg):
    pred = predict_message(msg.text)
    
    # Hapus pesan jika terdeteksi judi
    if pred > THRESHOLD:
        try:
            bot.delete_message(msg.chat.id, msg.message_id)
            bot.send_message(msg.chat.id, f"⚠️ *Pesan terdeteksi sebagai spam judi online dan telah dihapus.* (Prob: {pred:.2f})", parse_mode="Markdown")
        except telebot.apihelper.ApiException as e:
            # Handle error jika bot tidak memiliki hak admin untuk menghapus pesan
            bot.reply_to(msg, f"⚠️ *Peringatan!* Terdeteksi promosi judi online. (Prob: {pred:.2f})\n\n_Bot tidak memiliki hak admin untuk menghapus pesan._", parse_mode="Markdown")
    
    # Jika aman, bot bisa dibiarkan tidak merespons atau memberikan respons positif
    else:
        # Pilihan: tidak merespons sama sekali (biasanya lebih baik untuk bot moderasi)
        # Atau berikan respons untuk debug
        pass
        # bot.reply_to(msg, f"✅ Aman. (Prob: {pred:.2f})", parse_mode="Markdown")
    
print("🤖 Bot aktif...")
bot.remove_webhook()
bot.infinity_polling()