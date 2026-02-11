import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Pt
from io import BytesIO
import datetime
import requests
from openai import OpenAI

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

# --- 3. МОЗГИ (УНИВЕРСАЛЬНЫЕ) ---
def get_ai_response(user_question):
    try:
        key = st.secrets["ai_service"]["api_key"]
        
        # Определяем сервис по началу ключа
        if key.startswith("gsk_"):
            # Это GROQ (Супер быстрый)
            base_url = "https://api.groq.com/openai/v1"
            model = "llama3-70b-8192" # Очень умная бесплатная модель
            system_name = "Groq Llama 3"
        else:
            # Это OPENROUTER (Доступ к Google)
            base_url = "https://openrouter.ai/api/v1"
            # Самая надежная бесплатная модель (без лишних цифр)
            model="deepseek/deepseek-r1:free",
            system_name = "OpenRouter Gemini"

        client = OpenAI(base_url=base_url, api_key=key)
        
    except:
        return "⚠️ Ошибка: Проверь ключ в secrets.toml"

    try:
        with open("knowledge.txt", "r", encoding="utf-8") as f:
            knowledge_base = f.read()
    except:
        knowledge_base = "База знаний недоступна."

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": f"Ты юрист по Wildberries. Контекст: {knowledge_base}. Отвечай кратко."},
                {"role": "user", "content": user_question}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Ошибка ({system_name}): {e}"

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
        st.success("Вход выполнен")
        df = fetch_leads()
        if not df.empty: st.dataframe(df)

st.title("🛡️ SellerGuard AI")
tabs = st.tabs(["💬 Чат", "📄 Документы", "👨‍⚖️ Юрист"])

with tabs[0]:
    st.info("🤖 Система активна. Задайте вопрос.")
    if "messages" not in st.session_state: st.session_state.messages = []
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("Ваш вопрос..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Анализирую..."):
                reply = get_ai_response(prompt)
                st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

with tabs[1]:
    if st.button("Скачать пример"):
        f = create_doc("ИП", "000", "111", 5000, "Тест")
        st.download_button("Скачать", f, "Claim.docx")

with tabs[2]:
    with st.form("lead"):
        c, p, a = st.text_input("Контакты"), st.text_area("Проблема"), st.number_input("Сумма")
        if st.form_submit_button("Отправить"): send_to_supabase(c, p, a)


