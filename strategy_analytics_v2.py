import pandas as pd
import time
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.dates as mdates
import math
from scipy.stats import kurtosis, norm, skew
from var import VaR

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

# Sharpe Ratio (годовой)
def sharpe_ratio(returns, risk_free=0, periods=365):
    returns = pd.Series(returns)
    excess_returns = returns - risk_free / periods
    return np.sqrt(periods) * excess_returns.mean() / excess_returns.std()

# Sortino Ratio (годовой)
def sortino_ratio(returns, risk_free=0, periods=365):
    returns = pd.Series(returns)
    excess_returns = returns - risk_free / periods
    downside_deviation = np.sqrt((np.minimum(0, excess_returns)**2).mean()) * np.sqrt(periods)
    return (excess_returns.mean() * periods) / downside_deviation if downside_deviation != 0 else np.nan

# Annualized Volatility
def annualized_volatility(returns, periods=365):
    return returns.std() * np.sqrt(periods)

# Best/Worst Month
def best_worst_month(returns):
    monthly = returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
    return {
        'Best Month': monthly.max(),
        'Worst Month': monthly.min()
    }

# Monthly Turnover (пример: если у вас есть веса позиций)
def monthly_turnover(weights_df):
    """
    weights_df - DataFrame с весами позиций по дням
    """
    turnover = weights_df.diff().abs().sum(axis=1).resample('M').mean()
    return turnover.mean()

# Monthly Return
def monthly_return(returns):
    monthly = returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
    return monthly.mean()

# Total Return
def total_return(returns):
    return (1 + returns).prod() - 1

# Max Drawdown (уже есть)
def max_drawdown(series):
    cumulative = (1 + series).cumprod()
    peak = cumulative.cummax()
    drawdown = (peak - cumulative) / peak
    return drawdown.max()

def cvar(series):   
   var = VaR(pd.DataFrame(series), weights=np.array([1]))
   var_h = var.backtest(method='h')
   return var_h['ES(95.0)'].iloc[-1]*100
    

def calculate_metrics(df_returns, weights_df=None, risk_free_rate=0.047, periods=365):
    """
    df_returns - DataFrame с дневными доходностями стратегий (колонки - стратегии)
    weights_df - DataFrame с весами позиций (опционально, для turnover)
    risk_free_rate - безрисковая ставка
    """
    results = []

    for col in df_returns.columns:
        returns = df_returns[col].dropna()
        metrics = {
            'Strategy': col,
            'Sharpe Ratio (US Treasury)': sharpe_ratio(returns, risk_free_rate, periods),
            'Sharpe Ratio (AAVE)': sharpe_ratio(returns, 0.0677, periods),
            'Sharpe Ratio (Coinbase)': sharpe_ratio(returns, 0.06, periods),
            'Sharpe Ratio (Lido)': sharpe_ratio(returns, 0.028, periods),
            'Sharpe Ratio (Jupiter)': sharpe_ratio(returns, 0.0211, periods),
            'Sharpe Ratio (Kamino)': sharpe_ratio(returns, 0.0721, periods),
            'Sortino Ratio (US Treasury)': sortino_ratio(returns, risk_free_rate, periods),
            'Sortino Ratio (AAVE)': sortino_ratio(returns, 0.0677, periods),
            'Sortino Ratio (Coinbase)': sortino_ratio(returns, 0.06, periods),
            'Sortino Ratio (Lido)': sortino_ratio(returns, 0.028, periods),
            'Sortino Ratio (Jupiter)': sortino_ratio(returns, 0.0211, periods),
            'Sortino Ratio (Kamino)': sortino_ratio(returns, 0.0721, periods),
            'Volatility (ann)': annualized_volatility(returns, periods),
            'Max Drawdown': max_drawdown(returns),
            'Total Return': total_return(returns),
            'Monthly Return': monthly_return(returns),
        }

        # Best/Worst Month
        bw = best_worst_month(returns)
        metrics.update(bw)

        # Monthly Turnover (если передан weights_df)
        if weights_df is not None and col in weights_df.columns:
            turnover = monthly_turnover(weights_df[[col]])
            metrics['Monthly Turnover'] = turnover
        else:
            metrics['Monthly Turnover'] = np.nan

        results.append(metrics)

    df_metrics = pd.DataFrame(results)
    return df_metrics


def get_top_strategies(metrics_table, metric_name, top_n=5, ascending=False):
    """
    Возвращает топ-N стратегий по указанной метрике
    
    Параметры:
    metrics_table - таблица метрик из calculate_all_metrics
    metric_name - название метрики ('Average Return (%)', 'Daily Sharpe' и т.д.)
    top_n - количество топовых стратегий
    ascending - сортировка по возрастанию (False для убывания)
    
    Возвращает:
    Series с названиями стратегий и значениями метрики
    """
    # Получаем строку с нужной метрикой
    metric_row = metrics_table.loc[metric_name]
    
    # Преобразуем строку в числовой формат (убираем форматирование)
    metric_values = metric_row.replace('%', '', regex=True).astype(float)
    
    # Сортируем и выбираем топ-N
    if ascending:
        top_strategies = metric_values.nsmallest(top_n)
    else:
        top_strategies = metric_values.nlargest(top_n)
    
    return top_strategies