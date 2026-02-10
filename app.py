import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Pt
from io import BytesIO
import zipfile
import datetime
import requests # <-- Используем стандартную библиотеку вместо тяжелой Supabase
import json

# --- 1. НАСТРОЙКИ И ПОДКЛЮЧЕНИЕ ---
st.set_page_config(page_title="SellerGuard: AI System", page_icon="🛡️", layout="wide")

# Функция для прямой отправки в Supabase через HTTP
def send_to_supabase_direct(contact, problem, amount):
    try:
        # Достаем ключи из секретов
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        
        # Адрес твоей таблицы (REST API)
        endpoint = f"{url}/rest/v1/leads"
        
        # Заголовки (паспорт для входа)
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        
        # Данные для отправки
        payload = {
            "contact": contact,
            "problem_type": problem,
            "amount": int(amount)
        }
        
        # Стучимся в базу
        response = requests.post(endpoint, headers=headers, json=payload)
        
        # Если код ответа 201 (Created) - всё супер
        if response.status_code in [200, 201]:
            return True
        else:
            st.error(f"Ошибка сервера: {response.text}")
            return False
            
    except Exception as e:
        # Если ключей нет или нет интернета
        st.warning(f"База данных не подключена или ошибка сети. (Детали: {e})")
        return False

# --- 2. ГЕНЕРАТОР ДОКУМЕНТОВ ---
def create_legal_doc(seller, inn, act, money, date_event, problem):
    doc = Document()
    # Стили
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)
    
    doc.add_paragraph(f"Генеральному директору ООО «Вайлдберриз»\nОт Партнера: {seller} (ИНН {inn})")
    doc.add_paragraph("\nДОСУДЕБНАЯ ПРЕТЕНЗИЯ")
    doc.add_paragraph(f"В ходе работы на портале WB произошел инцидент: {problem}.")
    doc.add_paragraph(f"Согласно отчету/акту № {act} от {date_event}, сумма ущерба составила {money} руб.")
    doc.add_paragraph("На основании ст. 1109 ГК РФ прошу предоставить доказательства обоснованности удержания или вернуть средства.")
    doc.add_paragraph("\nВ случае отказа буду вынужден обратиться в суд (расходы на юриста будут возложены на Ответчика).")
    doc.add_paragraph(f"\nДата: {datetime.date.today()}")
    
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 3. ИНТЕРФЕЙС ---
st.title("🛡️ SellerGuard: Экосистема Защиты")
st.markdown("### 🚀 Верни свои деньги от Wildberries без юристов")

# Метрики
col1, col2, col3 = st.columns(3)
col1.metric("Средний штраф", "50 000 ₽", "Убыток")
col2.metric("Срок подачи", "7 дней", "Горит!")
col3.metric("Экономия", "15 000 ₽", "На юристе")

st.divider()

tab1, tab2 = st.tabs(["🤖 Генератор (Бесплатно)", "👨‍⚖️ Нанять Профи (PRO)"])

# ВКЛАДКА 1: РОБОТ
with tab1:
    c1, c2 = st.columns(2)
    with c1:
        s_name = st.text_input("Ваше Название (ИП/ООО)", "ИП Иванов И.И.")
        s_inn = st.text_input("ИНН", "500100200300")
    with c2:
        s_problem = st.selectbox("Что случилось?", ["Штраф (Логистика)", "Штраф (Габариты)", "Утеря товара", "Блокировка"])
        s_amount = st.number_input("Сумма ущерба (₽)", value=15000)
        s_act = st.text_input("Номер Отчета/Акта", "№ 12345")

    if st.button("📄 Скачать Претензию", key="gen_btn"):
        doc = create_legal_doc(s_name, s_inn, s_act, s_amount, datetime.date.today(), s_problem)
        st.download_button("📥 Сохранить Word", doc, file_name=f"Претензия_{s_inn}.docx")
        st.success("Готово! Отправьте этот файл через 'Поддержку' на портале WB.")

# ВКЛАДКА 2: БАЗА ДАННЫХ (ЛИДГЕН)
with tab2:
    st.write("### Сложный случай? Передадим дело юристу.")
    st.info("Мы работаем за % от выигранной суммы. Оплата только по факту.")
    
    with st.form("lead_form"):
        f_contact = st.text_input("Ваш Telegram или WhatsApp", placeholder="+7 900 000 00 00")
        f_desc = st.text_area("Опишите проблему", "Штраф 200к, WB молчит неделю...")
        f_sum = st.number_input("Сумма спора", value=100000)
        
        btn = st.form_submit_button("🚀 Отправить заявку")
        
        if btn:
            if len(f_contact) < 5:
                st.error("Напишите контакт для связи!")
            else:
                # ОТПРАВКА В SUPABASE НАПРЯМУЮ
                ok = send_to_supabase_direct(f_contact, f_desc, f_sum)
                if ok:
                    st.success("✅ Заявка у юриста! Мы свяжемся в течение 30 минут.")
                    st.balloons()