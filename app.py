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

# --- 2. ФУНКЦИИ ---
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

# --- 3. МОЗГИ (Только Lite) ---
def get_ai_response(user_question):
    try:
        api_key = st.secrets["gemini"]["api_key"]
        genai.configure(api_key=api_key)
    except:
        return "⚠️ Ошибка: Нет ключа Gemini в secrets.toml"

    # Читаем базу
    try:
        with open("knowledge.txt", "r", encoding="utf-8") as f:
            knowledge_base = f.read()
    except:
        knowledge_base = "База недоступна."

    # ИСПОЛЬЗУЕМ ТОЛЬКО ОДНУ МОДЕЛЬ (САМУЮ ЛЕГКУЮ)
    # Это точное название из твоего списка
    model = genai.GenerativeModel('gemini-2.0-flash-lite')
    
    prompt = f"""
    Ты — юрист SellerGuard.
    Контекст: {knowledge_base}
    Вопрос: {user_question}
    Ответь кратко.
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        # Если ошибка — выводим её честно
        return f"🚨 Ошибка Google: {e}"

# --- 4. ДОКУМЕНТЫ ---
def create_doc(seller, inn, act, money, problem):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)
    doc.add_paragraph(f"В ООО «Вайлдберриз»\nОт: {seller} (ИНН {inn})")
    doc.add_paragraph("\nДОСУДЕБНАЯ ПРЕТЕНЗИЯ")
    doc.add_paragraph(f"Суть: {problem}.")
    doc.add_paragraph(f"Акт: {act}. Сумма: {money} руб.")
    doc.add_paragraph(f"\nДата: {datetime.date.today()}")
    b = BytesIO()
    doc.save(b)
    b.seek(0)
    return b

# --- 5. ИНТЕРФЕЙС ---
with st.sidebar:
    st.header("🔐 Владелец")
    if st.text_input("Пароль", type="password") == st.secrets["admin"]["password"]:
        st.success("OK")
        df = fetch_leads()
        if not df.empty:
            st.dataframe(df)

st.title("🛡️ SellerGuard AI")
tabs = st.tabs(["💬 Чат", "📄 Документы", "👨‍⚖️ Юрист"])

with tabs[0]:
    st.info("🤖 Версия Lite (Экономная). Задай вопрос.")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Вопрос..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Думаю..."):
                reply = get_ai_response(prompt)
                st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

with tabs[1]:
    if st.button("Скачать пример"):
        f = create_doc("ИП", "123", "555", 50000, "Штраф")
        st.download_button("Скачать", f, "Claim.docx")

with tabs[2]:
    with st.form("lead"):
        if st.form_submit_button("Отправить"):
            st.success("Отправлено")
