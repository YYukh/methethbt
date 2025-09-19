import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import time

# Настройка страницы
st.set_page_config(page_title="Drift Dashboard", layout="wide")

# Заголовок
st.title("Анализ бектестов стратегий по METH/ETH")
st.markdown("""
    Добро пожаловать в приложение для анализа данных.
    
    Здесь вы можете:
    - Выбрать **один или несколько столбцов** для отображения
    - Указать временной период **с точностью до часа**
    - Посмотреть **график кумулятивной доходности** 
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

    # --- Выбор нескольких столбцов ---
    numeric_columns = df.select_dtypes(include='number').columns.tolist()
    if not numeric_columns:
        st.error("Нет числовых столбцов для построения графика.")
        st.stop()

    selected_columns = st.multiselect(
        "Выберите стратегии для отображения",
        options=numeric_columns,
        default=numeric_columns[4:5]  # дефолт — 5-я стратегия
    )

    if not selected_columns:
        st.warning("Пожалуйста, выберите хотя бы один столбец.")
        st.stop()

    # --- Выбор периода (только полные часы) ---
    st.write("### 🔍 Выберите временной диапазон (по полным часам)")

    min_dt = df[time_col].min()
    max_dt = df[time_col].max()

    # Округляем время до ближайшего часа (вниз)
    min_time_rounded = time(min_dt.hour, 0, 0)
    max_time_rounded = time(max_dt.hour, 0, 0)

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Дата начала", min_dt.date())
        # Только выбор часа
        start_hour = st.slider("Час начала", 0, 23, min_dt.hour)
        start_time = time(start_hour, 0, 0)
    with col2:
        end_date = st.date_input("Дата окончания", max_dt.date())
        end_hour = st.slider("Час окончания", 0, 23, max_dt.hour)
        end_time = time(end_hour, 0, 0)

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
            cumulative_df[col] = (1 + filtered_df[col]).cumprod()

        # Подготовка для Plotly
        plot_df = cumulative_df.melt(
            id_vars=[time_col],
            value_vars=selected_columns,
            var_name='Strategy',
            value_name='Cumulative returns'
        )

        # --- График с кастомными цветами ---
        st.subheader("Strategies cumulative returns")

        fig = px.line(
            plot_df,
            x=time_col,
            y='Cumulative returns',
            color='Strategy',
            title=f"Strategy: {', '.join(selected_columns)} | {start} – {end}",
            labels={time_col: "Time", "Cumulative returns": "Portfolio value"},
            markers=False
        )

        # --- Кастомизация цветов ---
        # Сделаем первую выбранную стратегию (или дефолтную) зелёной
        default_col = selected_columns[0]  # первая из выбранных

        # Создаём словарь цветов
        colors = {}
        for col in selected_columns:
            if col == default_col:
                colors[col] = "blue"
            else:
                colors[col] = px.colors.qualitative.Plotly[len(colors) % 10]  # остальные — из стандартной палитры

        # Применяем цвета
        for i, trace in enumerate(fig.data):
            strategy_name = trace.name
            if strategy_name in colors:
                trace.update(line=dict(color=colors[strategy_name], width=3 if strategy_name == default_col else 2.5))
            else:
                trace.update(line=dict(width=2.5))

        # Улучшаем внешний вид
        fig.update_layout(
            hovermode="x unified",
            xaxis_title="Time",
            yaxis_title="Portfolio Value ($)",
            height=650,
            title_font_size=16,
            legend_title_text="Стратегии:",
            margin=dict(l=40, r=40, t=80, b=60),
            legend=dict(itemclick="toggleothers")  # клик по легенде: скрывает всё кроме одного
        )

        st.plotly_chart(fig, use_container_width=True)

        # Показать итоговые значения
        st.write("### 💰 Итоговое значение $1")
        final_values = cumulative_df[selected_columns].iloc[-1]
        st.dataframe(final_values.to_frame(name="Final Value").style.format("{:.4f}"))

except FileNotFoundError as e:
    st.error(f"Файл не найден: убедитесь, что sl_returns.xlsx и sl_metrics.xlsx находятся в папке приложения.")
except Exception as e:
    st.error(f"Ошибка при загрузке данных: {e}")
    st.exception(e)
