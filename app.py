import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Pt
from io import BytesIO
import datetime
import requests
import json

# --- 1. НАСТРОЙКИ ---
st.set_page_config(page_title="SellerGuard: AI System", page_icon="🛡️", layout="wide")

# --- 2. ФУНКЦИИ БАЗЫ ДАННЫХ ---
def get_secrets():
    try:
        return st.secrets["supabase"]["url"], st.secrets["supabase"]["key"]
    except:
        return None, None

def send_to_supabase(contact, problem, amount):
    url, key = get_secrets()
    if not url: return False
    
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    data = {"contact": contact, "problem_type": problem, "amount": int(amount)}
    
    try:
        r = requests.post(f"{url}/rest/v1/leads", headers=headers, json=data)
        return r.status_code in [200, 201]
    except:
        return False

def fetch_all_leads():
    url, key = get_secrets()
    if not url: return pd.DataFrame()
    
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}"
    }
    
    try:
        # Запрашиваем ВСЕ данные из таблицы leads
        r = requests.get(f"{url}/rest/v1/leads?select=*", headers=headers)
        if r.status_code == 200:
            data = r.json()
            return pd.DataFrame(data)
    except:
        pass
    return pd.DataFrame()

# --- 3. ГЕНЕРАТОР ДОКУМЕНТОВ ---
def create_legal_doc(seller, inn, act, money, date_event, problem):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)
    
    doc.add_paragraph(f"Генеральному директору ООО «Вайлдберриз»\nОт: {seller} (ИНН {inn})")
    doc.add_paragraph("\nДОСУДЕБНАЯ ПРЕТЕНЗИЯ")
    doc.add_paragraph(f"Суть претензии: {problem}.")
    doc.add_paragraph(f"Документ-основание: {act} от {date_event}. Сумма: {money} руб.")
    doc.add_paragraph("Требую вернуть средства в течение 10 дней (ст. 1109 ГК РФ).")
    doc.add_paragraph(f"\nДата: {datetime.date.today()}")
    
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 4. ИНТЕРФЕЙС ---

# === БОКОВАЯ ПАНЕЛЬ (АДМИНКА) ===
with st.sidebar:
    st.header("🔐 Вход для Владельца")
    admin_pass = st.text_input("Пароль", type="password")
    
    if admin_pass == st.secrets["admin"]["password"]:
        st.success("Доступ разрешен!")
        st.divider()
        st.write("### 📂 База Заявок")
        
        # Кнопка обновления
        if st.button("Обновить данные"):
            st.rerun()
            
        # Загружаем таблицу
        df = fetch_all_leads()
        
        if not df.empty:
            # Показываем таблицу
            st.dataframe(df)
            
            # Считаем деньги
            total_potential = df['amount'].sum()
            st.metric("Потенциал выручки (15%)", f"{int(total_potential * 0.15):,} ₽")
            
            # Скачать базу в Excel
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Скачать базу (.csv)", csv, "leads.csv", "text/csv")
        else:
            st.info("База пока пуста.")

# === ОСНОВНОЙ ЭКРАН ===
st.title("🛡️ SellerGuard: Защита Селлера")

tab1, tab2 = st.tabs(["🤖 Робот-Юрист", "👨‍⚖️ Нанять Профи"])

with tab1:
    st.write("### Генератор Претензий")
    c1, c2 = st.columns(2)
    with c1:
        s_name = st.text_input("Название", "ИП Иванов")
        s_inn = st.text_input("ИНН", "1234567890")
    with c2:
        s_act = st.text_input("Номер Штрафа", "№ 555-777")
        s_sum = st.number_input("Сумма (₽)", 50000)
    
    if st.button("Сгенерировать"):
        doc = create_legal_doc(s_name, s_inn, s_act, s_sum, datetime.date.today(), "Штраф WB")
        st.download_button("Скачать", doc, "claim.docx")

with tab2:
    st.write("### Сложный случай? Мы поможем.")
    with st.form("lead"):
        contact = st.text_input("Ваш Telegram/Телефон")
        desc = st.text_area("Описание проблемы")
        amount = st.number_input("Сумма спора", 100000)
        
        if st.form_submit_button("Отправить заявку"):
            if send_to_supabase(contact, desc, amount):
                st.success("Заявка принята!")
            else:
                st.error("Ошибка отправки.")
