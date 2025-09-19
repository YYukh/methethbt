import pandas as pd
import time
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.dates as mdates
import math
from scipy.stats import kurtosis, norm, skew

def leverage_analysis(df, strategy_name='every_day', hedge_token='ETH', hedge_token_price='eth_fut_close'):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    # Проверим наличие нужных столбцов
    if 'leverage' not in df.columns or hedge_token_price not in df.columns:
        raise ValueError("Missing required columns for leverage analysis")

    # Создаём subplot с общей X
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Основная ось: Leverage
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['leverage'],
            name="Leverage",
            line=dict(color="red", width=2),
            hovertemplate="Leverage: %{y:.2f}<extra></extra>"
        ),
        secondary_y=False,
    )

    # Вторичная ось: Цена токена
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[hedge_token_price],
            name=f"{hedge_token} Price",
            line=dict(color="blue", width=2),
            hovertemplate=f"{hedge_token}: %{{y:.4f}}<extra></extra>"
        ),
        secondary_y=True,
    )

    # Настройка осей
    fig.update_xaxes(title_text="Time")
    fig.update_yaxes(title_text="Leverage", color="red", secondary_y=False)
    fig.update_yaxes(title_text=f"{hedge_token} Price", color="blue", secondary_y=True)

    fig.update_layout(
        title=f"Графики плеча и цены {hedge_token} для {strategy_name}",
        hovermode="x unified",
        height=600,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=80, b=60)
    )

    fig.show()
    # Чтобы сохранить: fig.write_image(f"lev_{strategy_name}.png", width=1200, height=600)


def pnl_decompose(df, resample='W', strategy_name='every_day'):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.express as px

    # Расчёт нормированных PnL
    pnl_df = df[['lst_pnl', 'fund_pnl', 'hedge_pnl', 'total_pnl', 'capital']].copy()
    pnl_df['net_pnl'] = (pnl_df['lst_pnl'] + pnl_df['hedge_pnl']) / pnl_df['capital'].shift()
    pnl_df['fund_pnl'] = pnl_df['fund_pnl'] / pnl_df['capital'].shift()
    pnl_df['total_pnl'] = pnl_df['total_pnl'] / pnl_df['capital'].shift()

    pnl_df = pnl_df.fillna(0)

    # Кумулятивные значения
    cum_net = (1 + pnl_df['net_pnl']).cumprod()
    cum_funding = (1 + pnl_df['fund_pnl']).cumprod()
    cum_total = (1 + pnl_df['total_pnl']).cumprod()

    # === ГРАФИК 1: Кумулятивный PnL (заполненные области) ===
    fig1 = go.Figure()

    # Область: net_pnl (положительная/отрицательная)
    fig1.add_trace(go.Scatter(
        x=pnl_df.index, y=cum_net,
        fill=None,
        mode='lines',
        line=dict(color='gray', dash='dot'),
        showlegend=False,
        hoverinfo='skip'
    ))

    fig1.add_trace(go.Scatter(
        x=pnl_df.index, y=cum_net,
        fill='tonexty',
        fillcolor='rgba(0,0,255,0.3)',
        name='Актив+Хедж (+)',
        mode='lines',
        line=dict(color='blue'),
        hovertemplate='Net PnL: %{y:.4f}<extra></extra>'
    ))

    fig1.add_trace(go.Scatter(
        x=pnl_df.index, y=[1]*len(cum_net),
        mode='lines',
        line=dict(width=0),
        showlegend=False,
        hoverinfo='skip'
    ))

    fig1.add_trace(go.Scatter(
        x=pnl_df.index, y=cum_net,
        fill='y',
        fillcolor='rgba(255,0,0,0.3)',
        name='Актив+Хедж (-)',
        mode='lines',
        line=dict(color='red'),
        hovertemplate='Net PnL: %{y:.4f}<extra></extra>'
    ))

    # Funding: разница между total и net
    fig1.add_trace(go.Scatter(
        x=pnl_df.index, y=cum_total,
        fill='tonexty',
        fillcolor='rgba(0,255,0,0.3)',
        name='Фандинг (+)',
        mode='lines',
        line=dict(color='green'),
        hovertemplate='Funding (+): %{y:.4f}<extra></extra>'
    ))

    fig1.add_trace(go.Scatter(
        x=pnl_df.index, y=cum_net,
        mode='lines',
        line=dict(width=0),
        showlegend=False,
        hoverinfo='skip'
    ))

    fig1.add_trace(go.Scatter(
        x=pnl_df.index, y=cum_total,
        fill='tonexty',
        fillcolor='rgba(255,165,0,0.3)',
        name='Фандинг (-)',
        mode='lines',
        line=dict(color='orange'),
        hovertemplate='Funding (-): %{y:.4f}<extra></extra>'
    ))

    # Общая линия
    fig1.add_trace(go.Scatter(
        x=pnl_df.index, y=cum_total,
        name='Общий PnL',
        mode='lines',
        line=dict(color='black', width=2.5),
        hovertemplate='Total PnL: %{y:.4f}<extra></extra>'
    ))

    fig1.update_layout(
        title=f"Факторный анализ прибыли {strategy_name}",
        xaxis_title="Время",
        yaxis_title="Кумулятивный PnL",
        hovermode="x unified",
        height=600,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        margin=dict(l=40, r=40, t=80, b=60)
    )
    fig1.show()
    # fig1.write_image(f"factor_{strategy_name}.png", width=1200, height=600)

    # === ГРАФИК 2: Недельные бары (stacked) ===
    weekly = pnl_df.resample(resample).sum()

    # Разделяем положительные и отрицательные
    weekly_pos = weekly.clip(lower=0)
    weekly_neg = weekly.clip(upper=0)

    fig2 = go.Figure()

    # Net PnL
    fig2.add_trace(go.Bar(
        x=weekly_pos.index,
        y=weekly_pos['net_pnl'],
        name='Актив+Хедж (+)',
        marker_color='blue',
        width=0.8
    ))
    fig2.add_trace(go.Bar(
        x=weekly_neg.index,
        y=weekly_neg['net_pnl'],
        name='Актив+Хедж (-)',
        marker_color='red',
        width=0.8
    ))

    # Funding PnL (с опорой на net)
    fig2.add_trace(go.Bar(
        x=weekly_pos.index,
        y=weekly_pos['fund_pnl'],
        name='Фандинг (+)',
        marker_color='green',
        width=0.8,
        base=weekly_pos['net_pnl']
    ))
    fig2.add_trace(go.Bar(
        x=weekly_neg.index,
        y=weekly_neg['fund_pnl'],
        name='Фандинг (-)',
        marker_color='orange',
        width=0.8,
        base=weekly_neg['net_pnl']
    ))

    fig2.update_layout(
        title=f"Вклад компонент по неделям {strategy_name}",
        xaxis_title="Неделя",
        yaxis_title="PnL",
        barmode='relative',
        hovermode="x unified",
        height=600,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        margin=dict(l=40, r=40, t=80, b=60),
        xaxis_tickformat='%Y-%m-%d'
    )

    fig2.update_xaxes(tickangle=45)
    fig2.show()
    # fig2.write_image(f"week_{strategy_name}.png", width=1200, height=600)
    

def fees_decompose(df, strategy_name='every_day'):
    import plotly.graph_objects as go

    cost_df = df[['lst_fees', 'hedge_fees', 'total_fees', 'capital']].copy()
    cost_df['lst_fees'] = -cost_df['lst_fees'] / cost_df['capital'].shift()
    cost_df['lst_fees'].iloc[0] = -df['lst_fees'].iloc[0] / cost_df['capital'].iloc[0]
    cost_df['hedge_fees'] = -cost_df['hedge_fees'] / cost_df['capital'].shift()
    cost_df['hedge_fees'].iloc[0] = -df['hedge_fees'].iloc[0] / cost_df['capital'].iloc[0]
    cost_df['total_fees'] = -cost_df['total_fees'] / cost_df['capital'].shift()
    cost_df['total_fees'].iloc[0] = -df['total_fees'].iloc[0] / cost_df['capital'].iloc[0]

    cum_lst = cost_df['lst_fees'].cumsum()
    cum_hedge = cost_df['hedge_fees'].cumsum()
    cum_total = cost_df['total_fees'].cumsum()

    # === График 1: Кумулятивные расходы ===
    fig1 = go.Figure()

    fig1.add_trace(go.Scatter(
        x=cost_df.index, y=cum_lst,
        fill='tozeroy',
        fillcolor='rgba(255,0,0,0.3)',
        name='Спот',
        mode='lines',
        line=dict(color='red'),
        hovertemplate='Spots Fees: %{y:.6f}<extra></extra>'
    ))

    fig1.add_trace(go.Scatter(
        x=cost_df.index, y=cum_total,
        fill='tonexty',
        fillcolor='rgba(255,165,0,0.3)',
        name='Хедж',
        mode='lines',
        line=dict(color='orange'),
        hovertemplate='Hedge Fees: %{y:.6f}<extra></extra>'
    ))

    fig1.add_trace(go.Scatter(
        x=cost_df.index, y=cum_total,
        name='Общие комиссии',
        mode='lines',
        line=dict(color='black', width=2.5),
        hovertemplate='Total Fees: %{y:.6f}<extra></extra>'
    ))

    fig1.update_layout(
        title=f"Накопленные расходы {strategy_name}",
        xaxis_title="Время",
        yaxis_title="Кумулятивные комиссии",
        hovermode="x unified",
        height=600,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        margin=dict(l=40, r=40, t=80, b=60)
    )
    fig1.show()
    # fig1.write_image(f"costs_{strategy_name}.png", width=1200, height=600)

    # === График 2: Комиссии в процентах (x100) без первой точки ===
    cum_lst_pct = cost_df['lst_fees'].iloc[1:] * 100
    cum_total_pct = cost_df['total_fees'].iloc[1:] * 100

    fig2 = go.Figure()

    fig2.add_trace(go.Scatter(
        x=cost_df.index[1:], y=cum_lst_pct,
        fill='tozeroy',
        fillcolor='rgba(255,0,0,0.3)',
        name='Спот',
        mode='lines',
        line=dict(color='red'),
        hovertemplate='Spots Fees: %{y:.4f}%<extra></extra>'
    ))

    fig2.add_trace(go.Scatter(
        x=cost_df.index[1:], y=cum_total_pct,
        fill='tonexty',
        fillcolor='rgba(255,165,0,0.3)',
        name='Хедж',
        mode='lines',
        line=dict(color='orange'),
        hovertemplate='Hedge Fees: %{y:.4f}%<extra></extra>'
    ))

    fig2.add_trace(go.Scatter(
        x=cost_df.index[1:], y=cum_total_pct,
        name='Общие комиссии',
        mode='lines',
        line=dict(color='black', width=2.5),
        hovertemplate='Total Fees: %{y:.4f}%<extra></extra>'
    ))

    fig2.update_layout(
        title=f"Факторный анализ расходов {strategy_name}",
        xaxis_title="Время",
        yaxis_title="Комиссии (%)",
        hovermode="x unified",
        height=600,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        margin=dict(l=40, r=40, t=80, b=60)
    )
    fig2.show()
    # fig2.write_image(f"fees_{strategy_name}.png", width=1200, height=600)
