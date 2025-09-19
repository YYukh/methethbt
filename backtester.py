import pandas as pd
import time
import numpy as np
import warnings
warnings.filterwarnings("ignore")  # Игнорировать все warnings

def run_strategy(
    data, 
    lst_token, 
    lst_token_ret, 
    hedge_token, 
    hedge_token_ret,
    cross_token,  
    funding_type, 
    strategy_type, 
    deviation, 
    init_capital, 
    fut_fees, 
    spot_fees, 
    lst_collateral=1,
    rebalance_hours=None,   # None = только по отклонению; число = каждые N часов
    start_hour=0,
    cross_ex = 0          # Час, с которого начинается цикл (например 12:00)
):
    # Создаем копию данных, чтобы не изменять оригинальный датафрейм
    data = data.copy()
    
    # Находим первый не-NaN индекс
    start_bt = data[lst_token].first_valid_index()
    data = data[start_bt:]
    data[f'{lst_token}_ex'] = data[lst_token] * (np.maximum(1, (cross_ex * data[cross_token]))) / data[hedge_token]
    init_capital = init_capital
    fut_fees = fut_fees
    spot_fees = spot_fees
    data['capital'] = init_capital
    data['capital_diff'] = 0
    data['hedge_w'] = 0.2
    data['lst_w'] = 1 - data['hedge_w']
    data['count_hedge'] = 0 
    data['count_loop'] = 0 
    data['loop_ret'] = 0
    data['hedge_ret'] = 0
    data['lst_ret'] = 0 
    data['fund_ret'] = 0 
    data['lst_cash'] = 0
    data['hedge_cash'] = 0
    data['lst_cash_end'] = 0
    data['hedge_cash_end'] = 0
    data['diff_lst'] = 0
    data['diff_hedge'] = 0
    data['lst_fees'] = 0
    data['hedge_fees'] = 0
    data['total_fees'] = 0
    data['lst_pnl'] = 0
    data['hedge_pnl'] = 0
    data['hedge_pnl_test'] = 0
    data['fund_pnl'] = 0
    data['free_pnl'] = 0
    data['total_pnl'] = 0
    data['cum_pnl'] = 0
    data['capital_dev'] = 0
    data['position_dev'] = 0
    data['leverage'] = 0
    data['strategy_ret'] = 0
    data['strategy_cumret'] = 0

    data.iloc[0, data.columns.get_loc('capital')] = init_capital
    data.iloc[0, data.columns.get_loc('count_hedge')] = init_capital * (data.iloc[0, data.columns.get_loc('hedge_w')] * ((data.iloc[0, data.columns.get_loc('lst_w')] + ((1 - data.iloc[0, data.columns.get_loc('lst_w')]) * lst_collateral)) / data.iloc[0, data.columns.get_loc('hedge_w')])) / data.iloc[0, data.columns.get_loc(hedge_token)]
    data.iloc[0, data.columns.get_loc('count_loop')] = init_capital * ((data.iloc[0, data.columns.get_loc('lst_w')] + ((1 - data.iloc[0, data.columns.get_loc('lst_w')]) * lst_collateral))) / (np.maximum(1, (cross_ex * data.iloc[0, data.columns.get_loc(cross_token)]))) / data.iloc[0, data.columns.get_loc(lst_token)]
    data.iloc[0, data.columns.get_loc('lst_cash')] = data.iloc[0, data.columns.get_loc('count_loop')] * data.iloc[0, data.columns.get_loc(lst_token)] * (np.maximum(1, (cross_ex * data.iloc[0, data.columns.get_loc(cross_token)])))
    data.iloc[0, data.columns.get_loc('hedge_cash')] = data.iloc[0, data.columns.get_loc('count_hedge')] * data.iloc[0, data.columns.get_loc(hedge_token)]
    data.iloc[0, data.columns.get_loc('strategy_ret')] = 0
    data.iloc[0, data.columns.get_loc('strategy_cumret')] = 1
    data.iloc[0, data.columns.get_loc('leverage')] = data.iloc[0, data.columns.get_loc('lst_cash')] / data.iloc[0, data.columns.get_loc('capital')]
    data.iloc[0, data.columns.get_loc('lst_fees')] = init_capital * spot_fees + init_capital * (max(0,cross_ex) * spot_fees)
    data.iloc[0, data.columns.get_loc('hedge_fees')] = init_capital * fut_fees
    data.iloc[0, data.columns.get_loc('total_fees')] = data.iloc[0, data.columns.get_loc('lst_fees')] + data.iloc[0, data.columns.get_loc('hedge_fees')]

    # === ДОБАВЛЕНО: Определение моментов временной ребалансировки ===
    if rebalance_hours is not None:
        # Получаем час из индекса (предполагается DatetimeIndex)
        current_hour = data.index.hour
        # Проверяем, попадает ли текущий час в сетку: start_hour, start_hour + N, start_hour + 2N...
        time_rebalance_condition = ((current_hour - start_hour) % rebalance_hours == 0)
    else:
        time_rebalance_condition = [False] * len(data)

    for i in range(1, len(data)):
        data.iloc[i, data.columns.get_loc('loop_ret')] = (data.iloc[i, data.columns.get_loc(lst_token_ret)])
        data.iloc[i, data.columns.get_loc('fund_ret')] = data.iloc[i, data.columns.get_loc(funding_type)] * data.iloc[i, data.columns.get_loc('hedge_w')] * ((data.iloc[i, data.columns.get_loc('lst_w')] + ((1 - data.iloc[i, data.columns.get_loc('lst_w')]) * lst_collateral)) / data.iloc[i, data.columns.get_loc('hedge_w')])
        data.iloc[i, data.columns.get_loc('hedge_ret')] = -data.iloc[i, data.columns.get_loc(hedge_token_ret)] * data.iloc[i, data.columns.get_loc('hedge_w')] * ((data.iloc[i, data.columns.get_loc('lst_w')] + ((1 - data.iloc[i, data.columns.get_loc('lst_w')]) * lst_collateral)) / data.iloc[i, data.columns.get_loc('hedge_w')])
        data.iloc[i, data.columns.get_loc('lst_ret')] = data.iloc[i, data.columns.get_loc('loop_ret')] * (data.iloc[i, data.columns.get_loc('lst_w')] + ((1 - data.iloc[i, data.columns.get_loc('lst_w')]) * lst_collateral))
        data.iloc[i, data.columns.get_loc('lst_pnl')] = data.iloc[i-1, data.columns.get_loc('count_loop')] * data.iloc[i, data.columns.get_loc(lst_token)] * (np.maximum(1, (cross_ex * data.iloc[i, data.columns.get_loc(cross_token)]))) - data.iloc[i-1, data.columns.get_loc('count_loop')] * data.iloc[i-1, data.columns.get_loc(lst_token)] * (np.maximum(1, (cross_ex * data.iloc[i-1, data.columns.get_loc(cross_token)])))
        data.iloc[i, data.columns.get_loc('fund_pnl')] = data.iloc[i-1, data.columns.get_loc('count_hedge')] * data.iloc[i-1, data.columns.get_loc(hedge_token)] * data.iloc[i, data.columns.get_loc('fund_ret')]
        data.iloc[i, data.columns.get_loc('hedge_pnl')] = data.iloc[i-1, data.columns.get_loc('count_hedge')] * data.iloc[i-1, data.columns.get_loc(hedge_token)] * -data.iloc[i, data.columns.get_loc(hedge_token_ret)]
        data.iloc[i, data.columns.get_loc('hedge_pnl_test')] = data.iloc[i-1, data.columns.get_loc('count_hedge')] * data.iloc[i-1, data.columns.get_loc(hedge_token)] - data.iloc[i-1, data.columns.get_loc('count_hedge')] * data.iloc[i, data.columns.get_loc(hedge_token)]
        data.iloc[i, data.columns.get_loc('free_pnl')] = data.iloc[i, data.columns.get_loc('hedge_pnl')] + data.iloc[i, data.columns.get_loc('fund_pnl')]
        data.iloc[i, data.columns.get_loc('total_pnl')] = data.iloc[i, data.columns.get_loc('lst_pnl')] + data.iloc[i, data.columns.get_loc('hedge_pnl')] + data.iloc[i, data.columns.get_loc('fund_pnl')]
        data.iloc[i, data.columns.get_loc('lst_cash')] = data.iloc[i-1, data.columns.get_loc('count_loop')] * data.iloc[i, data.columns.get_loc(lst_token)] * (np.maximum(1, (cross_ex * data.iloc[i, data.columns.get_loc(cross_token)])))
        data.iloc[i, data.columns.get_loc('hedge_cash')] = data.iloc[i-1, data.columns.get_loc('count_hedge')] * data.iloc[i, data.columns.get_loc(hedge_token)]     
        data.iloc[i, data.columns.get_loc('cum_pnl')] = data.iloc[i-1, data.columns.get_loc('cum_pnl')] + data.iloc[i, data.columns.get_loc('free_pnl')]
        data.iloc[i, data.columns.get_loc('capital_dev')] = data.iloc[i, data.columns.get_loc('cum_pnl')] / data.iloc[0, data.columns.get_loc('capital')]
        data.iloc[i, data.columns.get_loc('position_dev')] = (data.iloc[i, data.columns.get_loc('lst_cash')] / data.iloc[i, data.columns.get_loc('hedge_cash')])-1

        # === МОДИФИЦИРОВАНО: Условие ребалансировки ===
        should_rebalance_by_time = rebalance_hours is not None and time_rebalance_condition[i]

        if strategy_type == 'cap_dev':
            should_rebalance = abs(data.iloc[i, data.columns.get_loc('capital_dev')]) >= deviation or should_rebalance_by_time
            if should_rebalance:
                if data.iloc[i, data.columns.get_loc('cum_pnl')] > 0:
                    data.iloc[i, data.columns.get_loc('diff_lst')] = data.iloc[i, data.columns.get_loc('cum_pnl')] / (np.maximum(1, (cross_ex * data.iloc[i, data.columns.get_loc(cross_token)]))) / data.iloc[i, data.columns.get_loc(lst_token)]
                    data.iloc[i, data.columns.get_loc('cum_pnl')] = 0
                else:
                    data.iloc[i, data.columns.get_loc('diff_lst')] = 0
            else:
                data.iloc[i, data.columns.get_loc('diff_lst')] = 0

        elif strategy_type == 'cap_dev_only_buy':
            should_rebalance = (data.iloc[i, data.columns.get_loc('capital_dev')] >= deviation or should_rebalance_by_time) and data.iloc[i, data.columns.get_loc('cum_pnl')] > 0
            if should_rebalance:
                data.iloc[i, data.columns.get_loc('diff_lst')] = data.iloc[i, data.columns.get_loc('cum_pnl')] / (np.maximum(1, (cross_ex * data.iloc[i, data.columns.get_loc(cross_token)]))) / data.iloc[i, data.columns.get_loc(lst_token)]
                if data.iloc[i, data.columns.get_loc('diff_lst')] < 0:
                    data.iloc[i, data.columns.get_loc('diff_lst')] = 0
                data.iloc[i, data.columns.get_loc('cum_pnl')] = 0
            else:
                data.iloc[i, data.columns.get_loc('diff_lst')] = 0

        elif strategy_type == 'pos_dev':
            should_rebalance = abs(data.iloc[i, data.columns.get_loc('position_dev')]) >= deviation or should_rebalance_by_time
            if should_rebalance:
                if data.iloc[i, data.columns.get_loc('cum_pnl')] > 0:
                    data.iloc[i, data.columns.get_loc('diff_lst')] = data.iloc[i, data.columns.get_loc('cum_pnl')] / (np.maximum(1, (cross_ex * data.iloc[i, data.columns.get_loc(cross_token)]))) / data.iloc[i, data.columns.get_loc(lst_token)]
                    data.iloc[i, data.columns.get_loc('cum_pnl')] = 0
                else:
                    data.iloc[i, data.columns.get_loc('diff_lst')] = 0
            else:
                data.iloc[i, data.columns.get_loc('diff_lst')] = 0

        elif strategy_type == 'pos_dev_only_buy':
            should_rebalance = (data.iloc[i, data.columns.get_loc('position_dev')] >= deviation or should_rebalance_by_time) and data.iloc[i, data.columns.get_loc('cum_pnl')] > 0
            if should_rebalance:
                data.iloc[i, data.columns.get_loc('diff_lst')] = data.iloc[i, data.columns.get_loc('cum_pnl')] / (np.maximum(1, (cross_ex * data.iloc[i, data.columns.get_loc(cross_token)]))) / data.iloc[i, data.columns.get_loc(lst_token)]
                if data.iloc[i, data.columns.get_loc('diff_lst')] < 0:
                    data.iloc[i, data.columns.get_loc('diff_lst')] = 0
                data.iloc[i, data.columns.get_loc('cum_pnl')] = 0
            else:
                data.iloc[i, data.columns.get_loc('diff_lst')] = 0
        else:
            should_rebalance = should_rebalance_by_time
            if should_rebalance:
                data.iloc[i, data.columns.get_loc('diff_lst')] = data.iloc[i, data.columns.get_loc('total_pnl')] / (np.maximum(1, (cross_ex * data.iloc[i, data.columns.get_loc(cross_token)]))) / data.iloc[i, data.columns.get_loc(lst_token)]

        data.iloc[i, data.columns.get_loc('count_loop')] = data.iloc[i-1, data.columns.get_loc('count_loop')] + data.iloc[i, data.columns.get_loc('diff_lst')]
        data.iloc[i, data.columns.get_loc('lst_fees')] = abs(data.iloc[i, data.columns.get_loc('diff_lst')] * data.iloc[i, data.columns.get_loc(lst_token)] * (np.maximum(1, (cross_ex * data.iloc[i, data.columns.get_loc(cross_token)]))) * spot_fees)
        data.iloc[i, data.columns.get_loc('count_hedge')] = data.iloc[i, data.columns.get_loc('count_loop')] * data.iloc[i, data.columns.get_loc(f'{lst_token}_ex')]
        data.iloc[i, data.columns.get_loc('diff_hedge')] = data.iloc[i, data.columns.get_loc('count_hedge')] - data.iloc[i-1, data.columns.get_loc('count_hedge')]
        data.iloc[i, data.columns.get_loc('hedge_fees')] = abs(data.iloc[i, data.columns.get_loc('diff_hedge')] * data.iloc[i, data.columns.get_loc(hedge_token)] * fut_fees)
        data.iloc[i, data.columns.get_loc('total_fees')] = data.iloc[i, data.columns.get_loc('lst_fees')] + data.iloc[i, data.columns.get_loc('hedge_fees')]
        data.iloc[i, data.columns.get_loc('total_pnl')] = data.iloc[i, data.columns.get_loc('total_pnl')] - data.iloc[i, data.columns.get_loc('total_fees')]
        data.iloc[i, data.columns.get_loc('capital')] = data.iloc[i-1, data.columns.get_loc('capital')] + data.iloc[i, data.columns.get_loc('total_pnl')]
        data.iloc[i, data.columns.get_loc('lst_cash_end')] = data.iloc[i, data.columns.get_loc('count_loop')] * data.iloc[i, data.columns.get_loc(lst_token)] * (np.maximum(1, (cross_ex * data.iloc[0, data.columns.get_loc(cross_token)])))
        data.iloc[i, data.columns.get_loc('hedge_cash_end')] = data.iloc[i, data.columns.get_loc('count_hedge')] * data.iloc[i, data.columns.get_loc(hedge_token)] 
        data.iloc[i, data.columns.get_loc('leverage')] = data.iloc[i, data.columns.get_loc('lst_cash_end')] / data.iloc[i, data.columns.get_loc('capital')]
        data.iloc[i, data.columns.get_loc('strategy_cumret')] = data.iloc[i, data.columns.get_loc('capital')] / data.iloc[0, data.columns.get_loc('capital')]
        data.iloc[i, data.columns.get_loc('strategy_ret')] = data.iloc[i, data.columns.get_loc('capital')] / data.iloc[i-1, data.columns.get_loc('capital')] - 1
    
    return data
