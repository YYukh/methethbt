import pandas as pd
import time
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.dates as mdates
import math
from scipy.stats import kurtosis, norm, skew

def leverage_analysis(df, strategy_name='every_day', hedge_token='SOL', hedge_token_price='sol_close'):
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    # Получаем начальные значения
    initial_leverage = df['leverage'].iloc[0]
    initial_hedge_price = df[hedge_token_price].iloc[0]
    
    # Первый график (левая ось Y)
    color = 'tab:red'
    ax1.set_xlabel('Время')
    ax1.set_ylabel('Leverage', color=color)
    ax1.plot(df['leverage'], color=color)
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.grid(True, alpha=0.5)
    
    # Создаем вторую ось Y и выравниваем начальные точки
    ax2 = ax1.twinx()
    color = 'tab:blue'
    ax2.set_ylabel(f'{hedge_token} price', color=color)
    ax2.plot(df[hedge_token_price], color=color)
    
    # Вычисляем соотношение масштабов для начальных точек
    y1_min, y1_max = ax1.get_ylim()
    y2_min, y2_max = ax2.get_ylim()
    
    # Выравниваем оси так, чтобы initial_leverage и initial_sol_price визуально совпадали
    ax1.set_ylim(y1_min, y1_max)
    ax2.set_ylim(
        initial_hedge_price - (initial_leverage - y1_min) * (y2_max - y2_min) / (y1_max - y1_min),
        initial_hedge_price + (y1_max - initial_leverage) * (y2_max - y2_min) / (y1_max - y1_min)
    )
    
    ax2.tick_params(axis='y', labelcolor=color)
    ax2.grid(False)
    
    plt.title(f'Графики плеча для {strategy_name}')
    fig.tight_layout()
    plt.savefig(f"lev_{strategy_name}.png")
    plt.show()


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
