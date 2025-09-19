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
    - Посмотреть **график кумулятивной доходности** (рост $1 инвестиции)
""")

# --- Загрузка данных ---
try:
    # Показываем статистику
    st.write("### 📊 Статистика по бектестам")
    stats = pd.read_excel('sl_metrics.xlsx')
    if 'Unnamed: 0' in stats.columns:
        stats.drop(columns=['Unnamed: 0'], inplace=True)
    if 'Monthly Turnover' in stats.columns:
        stats.drop(columns=['Monthly Turnover'], inplace=True)
    st.dataframe(stats.style.format(precision=4))

    # Загружаем доходности
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
    st.write("Первые строки данных (доходности):")
    st.dataframe(df.head(10))

    # --- Выбор нескольких столбцов ---
    numeric_columns = df.select_dtypes(include='number').columns.tolist()
    if not numeric_columns:
        st.error("Нет числовых столбцов для построения графика.")
        st.stop()

    selected_columns = st.multiselect(
        "Выберите стратегии/активы для отображения",
        options=numeric_columns,
        default=numeric_columns[:2]
    )

    if not selected_columns:
        st.warning("Пожалуйста, выберите хотя бы один столбец.")
        st.stop()

    # --- Выбор периода ---
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
    filtered_df = df[[time_col] + selected_columns][mask].copy()

    if filtered_df.empty:
        st.info("Нет данных в выбранном диапазоне времени.")
    else:
        # --- РАСЧЁТ КУМУЛЯТИВНОЙ ДОХОДНОСТИ ---
        cumulative_df = filtered_df[[time_col]].copy()
        
        for col in selected_columns:
            # Преобразуем простую доходность в кумулятивную: (1 + r).cumprod()
            cumulative_df[col] = (1 + filtered_df[col]).cumprod()

        # Подготовка для Plotly («длинный» формат)
        plot_df = cumulative_df.melt(
            id_vars=[time_col],
            value_vars=selected_columns,
            var_name='Strategy',
            value_name='Cumulative returns'
        )

        # --- График кумулятивной доходности ---
        st.subheader("Strategies cumulative returns")

        fig = px.line(
            plot_df,
            x=time_col,
            y='Cumulative returns',
            color='Strategy',
            title=f"Рост $1: {', '.join(selected_columns)} | {start} – {end}",
            labels={time_col: "Time", "Cumulative returns": "Portfolio value"},
            markers=False
        )

        fig.update_layout(
            hovermode="x unified",
            xaxis_title="Time",
            yaxis_title="Portfolio",
            height=650,
            title_font_size=16,
            legend_title_text="Стратегии:",
            margin=dict(l=40, r=40, t=80, b=60),
            # yaxis=dict(rangemode="tozero")  # начинается с нуля
        )

        fig.update_traces(line=dict(width=2.5))

        st.plotly_chart(fig, use_container_width=True)

except FileNotFoundError as e:
    st.error(f"Файл не найден: {e.filename}")
except Exception as e:
    st.error(f"Ошибка при загрузке данных: {e}")
    st.exception(e)
