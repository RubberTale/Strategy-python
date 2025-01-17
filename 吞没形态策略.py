def backtest(data, initial_balance=1000000, capital_allocation=0.3):
    """
    回测策略，基于吞没形态策略的买入、止盈、止损逻辑。
    使用固定比例资金进行交易。
    
    参数:
        data: 包含策略信号的 DataFrame。
        initial_balance: 初始资金。
        capital_allocation: 每笔交易使用的资金比例（默认 30%）。
    """
    balance = initial_balance
    positions = 0
    entry_price = 0
    equity_curve = []
    trades = []

    for i in range(len(data)):
        if i == 0:
            equity_curve.append(balance)
            continue

        signal = data['Signal'].iloc[i - 1]  # 昨日信号决定今日交易
        price_open = data['Open'].iloc[i]  # 今日开盘价
        price_close = data['Close'].iloc[i]  # 今日收盘价

        # 如果没有持仓，检查信号
        if positions == 0:
            allocated_balance = balance * capital_allocation  # 每笔交易分配的资金

            if signal == 1:  # 买入信号（上涨吞没形态）
                positions = allocated_balance // price_open  # 计算可以买入的数量
                entry_price = price_open
                balance -= positions * price_open  # 扣除成本
                trades.append({'Date': data.index[i], 'Type': 'Buy', 'Price': entry_price, 'Reason': 'Bullish Engulfing'})

            elif signal == -1:  # 卖出信号（下跌吞没形态）
                positions = allocated_balance // price_open  # 计算可以买入的数量
                entry_price = price_open
                balance -= positions * price_open  # 扣除成本
                trades.append({'Date': data.index[i], 'Type': 'Sell', 'Price': entry_price, 'Reason': 'Bearish Engulfing'})

        # 如果有持仓，检查止盈/止损
        elif positions > 0:
            # 计算浮动盈亏
            current_price = price_close
            profit_loss = (current_price - entry_price) / entry_price

            # 止盈条件
            if profit_loss >= 0.05:
                balance += positions * current_price
                trades.append({'Date': data.index[i], 'Type': 'Sell', 'Price': current_price, 'Reason': 'Take Profit'})
                positions = 0
                entry_price = 0

            # 止损条件
            elif profit_loss <= -0.01:
                balance += positions * current_price
                trades.append({'Date': data.index[i], 'Type': 'Sell', 'Price': current_price, 'Reason': 'Stop Loss'})
                positions = 0
                entry_price = 0

        # 更新权益曲线
        current_equity = balance + positions * price_close
        equity_curve.append(current_equity)

    # 如果回测结束时仍有持仓，按最后一天的收盘价平仓
    if positions > 0:
        balance += positions * data['Close'].iloc[-1]
        trades.append({'Date': data.index[-1], 'Type': 'Sell', 'Price': data['Close'].iloc[-1], 'Reason': 'End of Backtest'})
        positions = 0

    data['Equity'] = equity_curve

    return data, trades