import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Pt
from io import BytesIO
import datetime
import requests
import google.generativeai as genai
import time

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

# --- 3. МОЗГИ (СИСТЕМА-ВЕЗДЕХОД) ---
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

# СПИСОК МОДЕЛЕЙ (Самые надежные)
    models_to_try = [
        'gemini-1.5-flash',      # 1. Быстрая и современная
        'gemini-1.5-pro',        # 2. Умная (другие лимиты)
        'gemini-pro',            # 3. Старая надежная (резерв)
        'gemini-1.0-pro'         # 4. Самая совместимая
    ]

    last_error = ""

    prompt = f"""
    Ты — SellerGuard, юрист по Wildberries.
    Контекст: {knowledge_base}
    Вопрос: {user_question}
    Отвечай кратко и юридически точно.
    """

    # Цикл перебора
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text # Если сработало — возвращаем ответ и выходим
        except Exception as e:
            last_error = e
            time.sleep(1) # Пауза 1 сек перед следующей попыткой
            continue # Если ошибка — идем к следующей модели

    # Если ничего не помогло
    return f"⚠️ Все линии заняты. Ошибка: {last_error}"

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
with st.sidebar:
    st.header("🔐 Владелец")
    if st.text_input("Пароль", type="password") == st.secrets["admin"]["password"]:
        st.success("Доступ открыт")
        df = fetch_leads()
        if not df.empty:
            st.dataframe(df)
            st.metric("Потенциал", f"{int(df['amount'].sum() * 0.15):,} ₽")

st.title("🛡️ SellerGuard AI")
st.markdown("#### Твой личный юрист и защита от штрафов WB")

tabs = st.tabs(["💬 AI-Консультант", "📄 Генератор Претензий", "👨‍⚖️ Нанять Профи"])

# Вкладка 1: ЧАТ
with tabs[0]:
    st.info("🤖 Я на связи! Использую умный поиск свободной модели.")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Например: 'Можно ли оспорить штраф?'"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Подбираю свободного юриста (модель)..."):
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
    with st.form("lead"):
        c = st.text_input("Контакт")
        p = st.text_area("Проблема")
        a = st.number_input("Сумма", 100000)
        if st.form_submit_button("Отправить"):
            send_to_supabase(c, p, a)
            st.success("Отправлено!")




