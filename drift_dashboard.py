import streamlit as st
import pandas as pd
import plotly.express as px

# Настройка страницы
st.set_page_config(page_title="Drift Dashboard", layout="wide")

# Заголовок
st.title("📊 Drift Dashboard")
st.markdown("""
    Добро пожаловать в приложение для анализа данных.
    
    Здесь вы можете:
    - Выбрать **один или несколько столбцов** для отображения
    - Указать временной период **с точностью до часа**
    - Посмотреть **красивый интерактивный график** с несколькими линиями
""")

# --- Загрузка данных ---
try:
    st.write("### 📊 Статистика по бектестам данным")
    stats = pd.read_excel('sl_metrics.xlsx')
    stats.drop(columns=['Unnamed: 0', 'Monthly Turnover'], inplace=True)
    st.dataframe(stats.style.format(precision=4))

    df = pd.read_excel("sl_returns.xlsx")

    # Проверяем наличие столбца времени
    time_col = 'time'
    if time_col not in df.columns:
        st.error(f"В Excel-файле должен быть столбец '{time_col}'")
        st.stop()

    # Преобразуем в datetime
    df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
    df = df.dropna(subset=[time_col]).sort_values(time_col).reset_index(drop=True)
    
    # Показываем первые строки
    st.write("Первые строки данных:")
    st.dataframe(df.head(10))

    # --- Выбор нескольких столбцов ---
    numeric_columns = df.select_dtypes(include='number').columns.tolist()
    if not numeric_columns:
        st.error("Нет числовых столбцов для построения графика.")
        st.stop()

    # Мультиселект: окно с выбором нескольких столбцов
    selected_columns = st.multiselect(
        "Выберите столбцы для отображения на графике",
        options=numeric_columns,
        default=numeric_columns[:2]  # можно выбрать первые 1–2 как дефолт
    )

    if not selected_columns:
        st.warning("Пожалуйста, выберите хотя бы один столбец для отображения.")
        st.stop()

    # --- Выбор периода с точностью до часа ---
    st.write("### 🔍 Выберите временной диапазон (с точностью до часа)")

    min_dt = df[time_col].min()
    max_dt = df[time_col].max()

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Дата начала", min_dt.date())
        start_time = st.time_input("Время начала", min_dt.time())
    with col2:
        end_date = st.date_input("Дата окончания", max_dt.date())
        end_time = st.time_input("Время окончания", max_dt.time())

    start = pd.Timestamp.combine(start_date, start_time)
    end = pd.Timestamp.combine(end_date, end_time)

    if start >= end:
        st.warning("Время начала не может быть позже или равно времени окончания.")
        st.stop()

    # Фильтрация
    mask = (df[time_col] >= start) & (df[time_col] <= end)
    filtered_df = df[mask].copy()

    if filtered_df.empty:
        st.info("Нет данных в выбранном диапазоне времени.")
    else:
        # --- Построение графика для нескольких столбцов ---
        st.subheader("Динамика выбранных показателей")

        # Подготовим данные для Plotly («длинный» формат)
        plot_df = filtered_df[[time_col] + selected_columns].melt(
            id_vars=[time_col],
            value_vars=selected_columns,
            var_name='Показатель',
            value_name='Значение'
        )

        # График
        fig = px.line(
            plot_df,
            x=time_col,
            y='Значение',
            color='Показатель',  # разные цвета для каждого столбца
            title=f"Динамика: {', '.join(selected_columns)} | {start} – {end}",
            labels={time_col: "Время", "Значение": "Значение"},
            markers=False
        )

        # Улучшаем внешний вид
        fig.update_layout(
            hovermode="x unified",  # одна вертикальная линия при наведении
            xaxis_title="Время",
            yaxis_title="Значение",
            height=650,
            title_font_size=16,
            legend_title_text="Столбцы:",
            margin=dict(l=40, r=40, t=80, b=60)
        )

        fig.update_traces(
            line=dict(width=2),
            marker=dict(size=4)
        )

        # Отображаем график
        st.plotly_chart(fig, use_container_width=True)


except FileNotFoundError:
    st.error("Файл `sl_returns.xlsx` не найден. Положите его в ту же папку, что и `drift_dashboard.py`.")
except Exception as e:
    st.error(f"Ошибка при загрузке данных: {e}")
    st.exception(e)
