import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Настройка страницы
st.set_page_config(page_title="Drift Data Viewer", layout="centered")

# Заголовок
st.title("📊 Анализ данных из drift_data.xlsx")
st.markdown("""
    Добро пожаловать в приложение для анализа данных.
    
    Здесь вы можете:
    - Выбрать интересующий столбец
    - Указать временной период
    - Посмотреть график динамики
""")

# --- Загрузка данных ---
try:
    # Предполагаем, что файл лежит рядом с app.py
    df = pd.read_excel("drift_data.xlsx")

    # Проверим, есть ли дата. Предположим, что столбец называется 'date'
    if 'date' not in df.columns:
        st.error("В Excel-файле должен быть столбец 'date'")
        st.stop()

    # Преобразуем дату
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date']).sort_values('date').reset_index(drop=True)

    # Покажем первые строки
    st.write("Первые строки данных:")
    st.dataframe(df.head())

    # --- Выбор столбца ---
    numeric_columns = df.select_dtypes(include='number').columns.tolist()
    if not numeric_columns:
        st.error("Нет числовых столбцов для построения графика.")
        st.stop()

    selected_column = st.selectbox("Выберите столбец для отображения", numeric_columns)

    # --- Выбор периода ---
    min_date = df['date'].min().date()
    max_date = df['date'].max().date()

    st.write("Выберите временной диапазон:")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Начало периода", min_date)
    with col2:
        end_date = st.date_input("Конец периода", max_date)

    # Проверка корректности дат
    if start_date > end_date:
        st.warning("Начальная дата не может быть позже конечной.")
        st.stop()

    # Фильтрация данных
    mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
    filtered_df = df[mask]

    if filtered_df.empty:
        st.info("Нет данных в выбранном диапазоне дат.")
    else:
        # --- Построение графика ---
        st.subheader(f"График: {selected_column}")
        
        # Вариант 1: Простой график через Streamlit
        # st.line_chart(filtered_df.set_index('date')[selected_column])

        # Вариант 2: Гибкий график через matplotlib (лучше кастомизация)
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(filtered_df['date'], filtered_df[selected_column], marker='o', linewidth=2)
        ax.set_title(f"{selected_column} за период с {start_date} по {end_date}")
        ax.set_ylabel(selected_column)
        ax.set_xlabel("Дата")
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3)
        st.pyplot(fig)

except FileNotFoundError:
    st.error("Файл `drift_data.xlsx` не найден. Убедитесь, что он находится в той же папке, что и `streamlit_app.py`.")
except Exception as e:
    st.error(f"Ошибка при загрузке данных: {e}")
