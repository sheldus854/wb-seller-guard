import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Pt
from io import BytesIO
import datetime
import requests
import google.generativeai as genai

# --- 1. НАСТРОЙКИ ---
st.set_page_config(page_title="SellerGuard AI", page_icon="🛡️", layout="wide")

# --- 2. ФУНКЦИИ БАЗЫ ---
def get_secrets():
    try:
        return st.secrets["supabase"]["url"], st.secrets["supabase"]["key"]
    except:
        return None, None

def send_to_supabase(contact, problem, amount):
    url, key = get_secrets()
    if not url: return False
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json", "Prefer": "return=minimal"}
    data = {"contact": contact, "problem_type": problem, "amount": int(amount)}
    try:
        requests.post(f"{url}/rest/v1/leads", headers=headers, json=data)
        return True
    except:
        return False

def fetch_leads():
    url, key = get_secrets()
    if not url: return []
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    try:
        r = requests.get(f"{url}/rest/v1/leads?select=*", headers=headers)
        return pd.DataFrame(r.json()) if r.status_code == 200 else pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 3. МОЗГИ (Google Gemini) ---
def get_ai_response(user_question):
    try:
        api_key = st.secrets["gemini"]["api_key"]
        genai.configure(api_key=api_key)
    except:
        return "⚠️ Ошибка: Нет ключа Gemini в secrets.toml"

    # Читаем базу знаний
    try:
        with open("knowledge.txt", "r", encoding="utf-8") as f:
            knowledge_base = f.read()
    except:
        knowledge_base = "База знаний временно недоступна."

    # Настройка модели
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = f"""
        Ты — SellerGuard, опытный юрист по защите прав селлеров Wildberries.
        Твоя задача: давать краткие, четкие и юридически грамотные советы.
        
        ИСПОЛЬЗУЙ ЭТОТ КОНТЕКСТ (ЗАКОНЫ И ПРАКТИКА):
        {knowledge_base}
        
        Вопрос пользователя: {user_question}
        
        Отвечай только по делу. В конце предложи сгенерировать претензию во вкладке "Генератор".
        """

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Ошибка Gemini: {e}"

# --- 4. ДОКУМЕНТЫ ---
def create_doc(seller, inn, act, money, problem):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)
    doc.add_paragraph(f"В ООО «Вайлдберриз»\nОт: {seller} (ИНН {inn})")
    doc.add_paragraph("\nДОСУДЕБНАЯ ПРЕТЕНЗИЯ")
    doc.add_paragraph(f"Суть нарушения: {problem}.")
    doc.add_paragraph(f"Основание: Отчет/Акт № {act}. Сумма ущерба: {money} руб.")
    doc.add_paragraph("На основании ст. 1109 ГК РФ и условий Оферты требую вернуть удержанные средства.")
    doc.add_paragraph(f"\nДата: {datetime.date.today()}")
    b = BytesIO()
    doc.save(b)
    b.seek(0)
    return b

# --- 5. ИНТЕРФЕЙС ---

# Сайдбар (Админка + ДИАГНОСТИКА)
with st.sidebar:
    st.header("🔐 Владелец")
    
    # --- БЛОК ДИАГНОСТИКИ ---
    st.divider()
    st.write("🔍 **Проверка связи с Google:**")
    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        models = list(genai.list_models())
        found = False
        for m in models:
            if "generateContent" in m.supported_generation_methods:
                st.code(m.name) # Покажет точное название модели
                found = True
        if not found:
            st.error("Список моделей пуст! Проблема с Ключом/Проектом.")
    except Exception as e:
        st.error(f"Ошибка доступа: {e}")
    st.divider()
    # ------------------------

    if st.text_input("Пароль", type="password") == st.secrets["admin"]["password"]:
        st.success("Доступ открыт")
        df = fetch_leads()
        if not df.empty:
            st.dataframe(df)
            st.metric("Потенциал (15%)", f"{int(df['amount'].sum() * 0.15):,} ₽")
        else:
            st.info("Заявок пока нет")
st.title("🛡️ SellerGuard AI")
st.markdown("#### Твой личный юрист и защита от штрафов WB")

tabs = st.tabs(["💬 AI-Консультант", "📄 Генератор Претензий", "👨‍⚖️ Нанять Профи"])

# Вкладка 1: ЧАТ
with tabs[0]:
    st.info("🤖 Я изучил судебную практику и Оферту WB. Задай мне вопрос!")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Например: 'Можно ли оспорить штраф за габариты?'"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Анализирую законы..."):
                reply = get_ai_response(prompt)
                st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

# Вкладка 2: ГЕНЕРАТОР
with tabs[1]:
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("Название (ИП/ООО)", "ИП Иванов")
        inn = st.text_input("ИНН", "1234567890")
    with c2:
        act = st.text_input("Номер Акта/Отчета")
        money = st.number_input("Сумма ущерба", 50000)
    
    if st.button("Сгенерировать Документ"):
        f = create_doc(name, inn, act, money, "Необоснованный штраф WB")
        st.download_button("Скачать Претензию (.docx)", f, "Pretenziya_WB.docx")

# Вкладка 3: ЮРИСТ
with tabs[2]:
    st.write("Сложный случай? Оставь заявку — мы берем % только после победы.")
    with st.form("lead"):
        c = st.text_input("Твой контакт (Telegram/WhatsApp)")
        p = st.text_area("Кратко о проблеме")
        a = st.number_input("Сумма спора", 100000)
        if st.form_submit_button("Отправить заявку"):
            if send_to_supabase(c, p, a):
                st.success("Заявка принята! Юрист скоро напишет.")
            else:
                st.error("Ошибка отправки.")




