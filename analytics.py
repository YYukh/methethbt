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


def pnl_decompose(df, resample='W', bar_width = 1.5, strategy_name = 'every_day'):
    
    pnl_df = df[['lst_pnl', 'fund_pnl', 'hedge_pnl', 'total_pnl', 'capital']]
    pnl_df['net_pnl'] = ((pnl_df['lst_pnl'] + pnl_df['hedge_pnl']) / pnl_df['capital'].shift()).fillna(0)
    pnl_df['fund_pnl'] = (pnl_df['fund_pnl'] / pnl_df['capital'].shift()).fillna(0)
    pnl_df['total_pnl'] = (pnl_df['total_pnl'] / pnl_df['capital'].shift()).fillna(0)
    pnl_df['spot_pnl'] = (pnl_df['lst_pnl'] / pnl_df['capital'].shift()).fillna(0)
    pnl_df['hedge_pnl'] = (pnl_df['hedge_pnl'] / pnl_df['capital'].shift()).fillna(0)

    plt.figure(figsize=(14, 7))

    # Кумулятивные суммы
    cum_net = (1+pnl_df['net_pnl']).cumprod()
    cum_funding = (1+pnl_df['fund_pnl']).cumprod()
    cum_total = (1+pnl_df['total_pnl']).cumprod()

    # Границы для заливки
    plt.fill_between(pnl_df.index, cum_net, where=cum_net >= 1, facecolor='blue', alpha=0.3, label='Актив+Хедж (+)')
    plt.fill_between(pnl_df.index, cum_net, where=cum_net < 1, facecolor='red', alpha=0.3, label='Актив+Хедж (-)')
    plt.fill_between(pnl_df.index, cum_total, cum_net, where=cum_funding >= 1, 
                    facecolor='green', alpha=0.3, label='Фандинг (+)')
    plt.fill_between(pnl_df.index, cum_total, cum_net, where=cum_funding < 1, 
                    facecolor='orange', alpha=0.3, label='Фандинг (-)')

    # Линии для наглядности
    plt.plot(cum_net, color='blue', linewidth=1, linestyle='--')
    plt.plot(cum_total, color='black', linewidth=2, label='Общий PnL')
    plt.ylim(0.98, None)

    plt.title(f'Факторный анализ прибыли {strategy_name}')
    plt.ylabel('Кумулятивный PnL')
    plt.grid(True)
    plt.legend()
    plt.savefig(f"factor_{strategy_name}.png")
    plt.show()
    

    # Агрегируем по неделям
    weekly = pnl_df.resample(resample).sum()

    fig, ax = plt.subplots(figsize=(14, 7))  # Увеличиваем размер фигуры

    # Положительные и отрицательные части
    weekly_pos = weekly.clip(lower=0)
    weekly_neg = weekly.clip(upper=0)

    # Настройки ширины столбцов
    bar_width = bar_width  # Ширина столбцов (по умолчанию 0.8, можно увеличить до 1.0)
    pos_positions = weekly_pos.index
    neg_positions = weekly_neg.index

    # Столбцы для позиции (делаем толще)
    ax.bar(pos_positions, weekly_pos['net_pnl'], 
        width=bar_width, color='blue', label='Актив+Хедж (+)')
    ax.bar(neg_positions, weekly_neg['net_pnl'], 
        width=bar_width, color='red', label='Актив+Хедж (-)')

    # Столбцы для фандинга (тоже толще)
    ax.bar(pos_positions, weekly_pos['fund_pnl'], 
        width=bar_width, bottom=weekly_pos['net_pnl'],
        color='green', label='Фандинг (+)')
    ax.bar(neg_positions, weekly_neg['fund_pnl'], 
        width=bar_width, bottom=weekly_neg['net_pnl'],
        color='orange', label='Фандинг (-)')

    # Улучшаем подписи дат
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))  # Формат даты
    plt.xticks(rotation=45)  # Поворачиваем подписи для читаемости

    plt.title(f'Вклад компонент по неделям {strategy_name}', pad=20)
    plt.ylabel('PnL')
    # plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')  # Выносим легенду справа
    plt.legend()
    plt.grid(True, axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()  # Автоматическая подгонка layout
    plt.savefig(f"week_{strategy_name}.png")
    plt.show()
    

def fees_decompose(df, strategy_name = 'every_day'):
    
    cost_df = df[['lst_fees', 'hedge_fees', 'total_fees', 'capital']]
    cost_df['lst_fees'] = -cost_df['lst_fees'] / cost_df['capital'].shift()
    cost_df['lst_fees'][0] = -df['lst_fees'][0] / cost_df['capital'][0]
    cost_df['hedge_fees'] = -cost_df['hedge_fees'] / cost_df['capital'].shift()
    cost_df['hedge_fees'][0] = -df['hedge_fees'][0] / cost_df['capital'][0]
    cost_df['total_fees'] = -cost_df['total_fees'] / cost_df['capital'].shift()
    cost_df['total_fees'][0] = -df['total_fees'][0] / cost_df['capital'][0]

    plt.figure(figsize=(14, 7))

    # Кумулятивные суммы
    cum_lst = cost_df['lst_fees'].cumsum()
    cum_hedge = cost_df['hedge_fees'].cumsum()
    cum_total = cost_df['total_fees'].cumsum()

    # Границы для заливки
    plt.fill_between(cost_df.index, cum_lst, where=cum_lst < 1, facecolor='red', alpha=0.3, label='Спот')
    plt.fill_between(cost_df.index, cum_total, cum_lst, where=cum_hedge < 1, 
                    facecolor='orange', alpha=0.3, label='Хедж')

    # Линии для наглядности
    plt.plot(cum_lst, color='blue', linewidth=1, linestyle='--')
    plt.plot(cum_total, color='black', linewidth=2, label='Общие комиссии')

    plt.title(f'Накопленные расходы {strategy_name}')
    plt.ylabel('Кумулятивные Fees')
    plt.grid(True)
    plt.legend()
    plt.savefig(f"costs_{strategy_name}.png")
    plt.show()
    

    plt.figure(figsize=(14, 7))

    cum_lst = cost_df['lst_fees'][1:] * 100
    cum_hedge = cost_df['hedge_fees'][1:] * 100
    cum_total = cost_df['total_fees'][1:] * 100

    # Границы для заливки
    plt.fill_between(cost_df.index[1:], cum_lst, where=cum_lst < 1, facecolor='red', alpha=0.3, label='Спот')
    plt.fill_between(cost_df.index[1:], cum_total, cum_lst, where=cum_hedge < 1, 
                    facecolor='orange', alpha=0.3, label='Хедж')

    # Линии для наглядности
    plt.plot(cum_lst, color='blue', linewidth=1, linestyle='--')
    plt.plot(cum_total, color='black', linewidth=2, label='Общие комиссии')

    plt.title(f'Факторный анализ расходов {strategy_name}')
    plt.ylabel('Fees')
    plt.grid(True)
    plt.legend()
    plt.savefig(f"fees_{strategy_name}.png")
    plt.show()
