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

# --- 2. ФУНКЦИИ БАЗЫ (Supabase) ---
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

# --- 3. МОЗГИ (AI Chat) ---
def get_ai_response(user_question):
    # 1. Достаем ключ
    try:
        api_key = st.secrets["openai"]["api_key"]
    except:
        return "⚠️ Ошибка: Нет API ключа OpenAI."

    # 2. Читаем базу знаний
    try:
        with open("knowledge.txt", "r", encoding="utf-8") as f:
            knowledge_base = f.read()
    except:
        knowledge_base = "База знаний временно недоступна. Отвечай, как опытный юрист РФ."

    client = OpenAI(api_key=api_key)

    # 3. Формируем запрос
    system_prompt = f"""
    Ты — SellerGuard, опытный юрист по защите прав селлеров Wildberries.
    Твоя задача: давать четкие, юридически грамотные советы, опираясь на контекст ниже.
    
    КОНТЕКСТ (ЗНАНИЯ):
    {knowledge_base}
    
    ПРАВИЛА:
    1. Если в контексте есть ответ (например, про 7 дней или оферту), цитируй его.
    2. Будь краток и конкретен.
    3. В конце всегда предлагай сгенерировать претензию во вкладке "Генератор".
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Используем быструю и дешевую модель
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Ошибка ИИ: {e}"

# --- 4. ФУНКЦИИ ДОКУМЕНТОВ ---
def create_doc(seller, inn, act, money, problem):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)
    doc.add_paragraph(f"В ООО «Вайлдберриз»\nОт: {seller} (ИНН {inn})")
    doc.add_paragraph("\nДОСУДЕБНАЯ ПРЕТЕНЗИЯ")
    doc.add_paragraph(f"По факту нарушения: {problem}.")
    doc.add_paragraph(f"Основание: Отчет {act}. Сумма: {money} руб.")
    doc.add_paragraph("На основании ст. 1109 ГК РФ требую вернуть средства.")
    doc.add_paragraph(f"\nДата: {datetime.date.today()}")
    b = BytesIO()
    doc.save(b)
    b.seek(0)
    return b

# --- 5. ИНТЕРФЕЙС ---

# АДМИНКА
with st.sidebar:
    st.header("🔐 Владелец")
    if st.text_input("Пароль", type="password") == st.secrets["admin"]["password"]:
        st.success("Admin OK")
        df = fetch_leads()
        if not df.empty:
            st.dataframe(df)
            st.metric("Потенциал", f"{int(df['amount'].sum() * 0.15):,} ₽")

# ОСНОВНОЕ ОКНО
st.title("🛡️ SellerGuard AI")
st.markdown("#### Твой личный юрист и защита от штрафов WB")

tabs = st.tabs(["💬 AI-Консультант", "📄 Генератор Претензий", "👨‍⚖️ Нанять Профи"])

# Вкладка 1: ЧАТ С ИИ
with tabs[0]:
    st.write("Задай вопрос роботу-юристу. Он знает судебную практику и оферту WB.")
    
    # История чата
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Поле ввода
    if prompt := st.chat_input("Например: 'Мне пришел штраф за габариты, что делать?'"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Анализирую судебную практику..."):
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
        act = st.text_input("Номер штрафа/отчета")
        money = st.number_input("Сумма ущерба", 50000)
    
    if st.button("Сгенерировать документ"):
        file = create_doc(name, inn, act, money, "Штраф WB")
        st.download_button("Скачать .docx", file, "Pretenziya.docx")

# Вкладка 3: ЮРИСТ
with tabs[2]:
    st.write("Сложный случай? Оставь заявку.")
    with st.form("lead"):
        c = st.text_input("Контакт")
        p = st.text_area("Проблема")
        a = st.number_input("Сумма спора", 100000)
        if st.form_submit_button("Отправить"):
            if send_to_supabase(c, p, a):
                st.success("Отправлено!")
