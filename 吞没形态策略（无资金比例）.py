import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import socket
device_name = socket.gethostname()

# 示例：读取历史数据
def load_data(file_path):
    """
    读取历史数据，假设数据包含日期、开盘价、收盘价、最高价、最低价、成交量等。
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件未找到: {file_path}")
    data = pd.read_csv(file_path, parse_dates=['Date'])
    data.set_index('Date', inplace=True)
    return data

# 示例策略逻辑
def simple_strategy(data, short_window=5, long_window=15):
    data['Short_MA'] = data['Close'].rolling(window=short_window).mean()
    data['Long_MA'] = data['Close'].rolling(window=long_window).mean()
    data['Signal'] = 0
    data.loc[data['Short_MA'] > data['Long_MA'], 'Signal'] = 1  # 买入信号
    data.loc[data['Short_MA'] <= data['Long_MA'], 'Signal'] = -1  # 卖出信号
    return data

def engul_strategy(data):
    data = detect_engulfing(data)
    data['Signal'] = 0
    data.loc[data['bullish_engulfing'], 'Signal'] = 1  # 买入信号
    data.loc[data['bearish_engulfing'], 'Signal'] = -1  # 卖出信号
    return data

# 模拟回测
def backtest(data, initial_balance=1000000, risk_per_trade=0.6):
    """
    回测策略，基于吞没形态策略的买入、止盈、止损逻辑。
    """
    balance = initial_balance
    positions = 0
    entry_price = 0
    equity_curve = []
    risk_curve = []
    trades = []

    for i in range(len(data)):
        if i == 0:
            equity_curve.append(balance)
            risk_curve.append(0)
            continue

        signal = data['Signal'].iloc[i - 1]  # 昨日的信号决定今日交易
        price_open = data['Open'].iloc[i]  # 今日开盘价
        price_close = data['Close'].iloc[i]  # 今日收盘价

        # 如果没有持仓，检查信号
        if positions == 0:
            if signal == 1:  # 买入信号（上涨吞没形态）
                risk_amount = balance * risk_per_trade
                positions = risk_amount // price_open
                entry_price = price_open
                balance -= positions * price_open
                trades.append({'Date': data.index[i], 'Type': 'Buy', 'Price': entry_price, 'Reason': 'Bullish Engulfing'})

            elif signal == -1:  # 卖出信号（下跌吞没形态）
                risk_amount = balance * risk_per_trade
                positions = risk_amount // price_open
                entry_price = price_open
                balance -= positions * price_open
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
        current_risk = (positions * price_close) / current_equity if current_equity > 0 else 0
        equity_curve.append(current_equity)
        risk_curve.append(current_risk)

    # 如果回测结束时仍有持仓，按最后一天的收盘价平仓
    if positions > 0:
        balance += positions * data['Close'].iloc[-1]
        trades.append({'Date': data.index[-1], 'Type': 'Sell', 'Price': data['Close'].iloc[-1], 'Reason': 'End of Backtest'})
        positions = 0

    data['Equity'] = equity_curve
    data['Risk'] = risk_curve

    return data, trades

# 计算回测指标
def calculate_metrics(data):
    equity = data['Equity']
    returns = equity.pct_change().dropna()
    rolling_max = equity.cummax()
    drawdown = (equity - rolling_max) / rolling_max
    max_drawdown = drawdown.min()
    sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252)
    return {
        "Final Equity": equity.iloc[-1],
        "Max Drawdown": max_drawdown,
        "Sharpe Ratio": sharpe_ratio
    }

# 可视化结果
def plot_results(data):
    plt.figure(figsize=(14, 7))
    plt.plot(data['Equity'], label='Equity Curve')
    plt.title('Equity Curve')
    plt.xlabel('Date')
    plt.ylabel('Equity')
    plt.legend()
    plt.grid()
    plt.show()

def detect_engulfing(data):
    """
    检测吞没形态信号。
    data: 包含开盘价(open), 收盘价(close), 最高价(high), 最低价(low)的DataFrame。
    """
    data['prev_open'] = data['open'].shift(1)
    data['prev_close'] = data['close'].shift(1)
    data['prev_high'] = data['high'].shift(1)
    data['prev_low'] = data['low'].shift(1)

    # 判断上涨吞没形态：前一根为阴线，后一根为阳线，且满足吞没条件
    data['bullish_engulfing'] = (
        (data['close'] > data['open']) &  # 当前K线为阳线
        (data['prev_close'] < data['prev_open']) &  # 前一根K线为阴线
        (data[['open', 'close']].max(axis=1) > data[['prev_open', 'prev_close']].max(axis=1)) &  # 当前K线最高价高于前一根K线最高价
        (data[['open', 'close']].min(axis=1) < data[['prev_open', 'prev_close']].min(axis=1))  # 当前K线最低价低于前一根K线最低价
    )

    # 判断下跌吞没形态：前一根为阳线，后一根为阴线，且满足吞没条件
    data['bearish_engulfing'] = (
        (data['close'] < data['open']) &  # 当前K线为阴线
        (data['prev_close'] > data['prev_open']) &  # 前一根K线为阳线
        (data[['open', 'close']].max(axis=1) > data[['prev_open', 'prev_close']].max(axis=1)) &  # 当前K线最高价高于前一根K线最高价
        (data[['open', 'close']].min(axis=1) < data[['prev_open', 'prev_close']].min(axis=1))  # 当前K线最低价低于前一根K线最低价
    )
    return data

def engulf_strategy(data):
    """
    根据用户定义的吞没形态策略生成交易信号。
    data: 包含开盘价(open), 收盘价(close), 最高价(high), 最低价(low)的DataFrame。
    """
    # 前三根的收盘价是否连续下跌
    data['prev_close_1'] = data['Close'].shift(1)
    data['prev_close_2'] = data['Close'].shift(2)
    data['prev_close_3'] = data['Close'].shift(3)

    data['three_day_downtrend'] = (
        (data['prev_close_1'] < data['prev_close_2']) &
        (data['prev_close_2'] < data['prev_close_3']) &
        (data['Close'] < data['prev_close_1'])
    )

    # 判断吞没形态
    data['bullish_engulfing'] = (
        data['three_day_downtrend'] &  # 连续三天下跌
        (data[['Open', 'Close']].max(axis=1) > data[['Open', 'Close']].shift(1).max(axis=1)) &  # 当前K线高点高于前一根K线
        (data[['Open', 'Close']].min(axis=1) < data[['Open', 'Close']].shift(1).min(axis=1)) &  # 当前K线低点低于前一根K线
        (data['Open'] < data['Close']) &  # 当前K线为阳线
        (data['Open'].shift(1) > data['Close'].shift(1))  # 前一根K线为阴线
    )

    data['bearish_engulfing'] = (
        (data['three_day_downtrend'] == False) &  # 非下跌趋势
        (data[['Open', 'Close']].max(axis=1) > data[['Open', 'Close']].shift(1).max(axis=1)) &  # 当前K线高点高于前一根K线
        (data[['Open', 'Close']].min(axis=1) < data[['Open', 'Close']].shift(1).min(axis=1)) &  # 当前K线低点低于前一根K线
        (data['Open'] > data['Close']) &  # 当前K线为阴线
        (data['Open'].shift(1) < data['Close'].shift(1))  # 前一根K线为阳线
    )

    # 生成交易信号
    data['Signal'] = 0
    data.loc[data['bullish_engulfing'], 'Signal'] = 1  # 买入信号（上涨吞没）
    data.loc[data['bearish_engulfing'], 'Signal'] = -1  # 卖出信号（下跌吞没）

    return data

# 筛选数据，从指定日期开始
start_date = '2024-08-01'  # 策略开始日期
data = data[data.index >= start_date]

if data is not None:
    data = data[data.index >= start_date]
else:
    raise ValueError("数据加载失败，无法进行筛选操作")

def load_data(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件未找到: {file_path}")
    try:
        data = pd.read_csv(file_path, parse_dates=['Date'])
        data.set_index('Date', inplace=True)
        return data
    except Exception as e:
        print(f"读取数据时发生错误: {e}")
        return None
    
# 主程序
if __name__ == '__main__':
    if device_name == 'DESKTOP-KKRIC7M':
        file_path = r'D:\resilio-goen\品种数据库\historical_data.csv'  # 替换为你的实际路径
    else:
        file_path = r'D:\resilio sync\品种数据库\historical_data.csv'

    # 检查文件路径是否存在
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件路径不存在: {file_path}")
    else:
        print(f"文件路径存在: {file_path}")

    # 加载数据
    try:
        data = load_data(file_path)
        print("数据加载成功！")
        print(f"数据列名: {data.columns}")
        print(data.head())
    except Exception as e:
        print(f"数据加载失败: {e}")
        data = None

    # 确保数据加载成功
    if data is not None:
        # 策略开始日期
        start_date = '2024-08-01'
        data = data[data.index >= start_date]
        print(f"筛选后数据日期范围: {data.index.min()} 至 {data.index.max()}")

        # 执行策略
        data = engulf_strategy(data)

        # 回测策略
        data, trades = backtest(data)

        # 计算回测指标
        metrics = calculate_metrics(data)

        # 输出回测结果
        print("回测指标：")
        for key, value in metrics.items():
            print(f"{key}: {value}")

        print("\n交易记录：")
        for trade in trades:
            print(trade)

        # 可视化结果
        plot_results(data)
    else:
        print("数据未成功加载，程序终止")