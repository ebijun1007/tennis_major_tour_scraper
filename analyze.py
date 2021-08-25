import pandas as pd
import statsmodels.api as sm
from sklearn.model_selection import train_test_split
import numpy as np
from datetime import datetime, timedelta, timezone

df = pd.read_csv('merged.csv')
roi = df["prediction_roi"].sum()
df = df[[
    'winner',
    'player1_age',
    'player1_year_surface_win',
    'player1_year_surface_lose',
    'player1_odds',
    'player1_H2H',
    'player2_age',
    'player2_year_surface_win',
    'player2_year_surface_lose',
    'player2_odds',
    'player2_H2H',
]]
df = df.dropna()

x = pd.get_dummies(df[[
    'player1_age',
    'player1_year_surface_win',
    'player1_year_surface_lose',
    'player1_odds',
    'player1_H2H',
    'player2_age',
    'player2_year_surface_win',
    'player2_year_surface_lose',
    'player2_odds',
    'player2_H2H',
]])  # 説明変数

y = df['winner']  # 目的変数

X_train, X_test, y_train, y_test = train_test_split(
    x, y, train_size=0.7, random_state=0)

# 定数項(y切片)を必要とする線形回帰のモデル式ならば必須
X = sm.add_constant(x)

# 最小二乗法でモデル化
model = sm.OLS(y_train, X_train.drop(
    columns=['player1_odds', 'player2_odds']).astype(float))
result = model.fit()
result.save('learned_model.pkl')
# new_results = sm.load('learned_model.pkl')

# # 重回帰分析の結果を表示する
# print(result.summary())

jst = timezone(timedelta(hours=9), 'JST')
yesterday = datetime.now(jst) - timedelta(days=1)
try:
    yesterday_result_df = pd.read_csv(
        f'./data/{yesterday.year:04}-{yesterday.month:02}-{yesterday.day:02}.csv')
    yesterday_win = len(
        yesterday_result_df.loc[yesterday_result_df['prediction_roi'] > 0].index)
    yesterday_lose = len(
        yesterday_result_df.loc[yesterday_result_df['prediction_roi'] < 0].index)
    yesterday_roi = round(yesterday_result_df["prediction_roi"].sum(), 2)
except:
    pass
predictions = result.predict(X_test.drop(
    columns=['player1_odds', 'player2_odds'])).array
good = 0
bad = 0
balance = 0
print("=======================================================================================")
for i in range(len(predictions)):
    balance -= 1
    # if(predictions[i] >= 1.2 and predictions[i] <= 1.8):
    #     continue
    if(round(predictions[i]) == int(y_test.array[i])):
        good += 1
        balance += X_test.iloc[i][f'player{int(y_test.array[i])}_odds']
        print(
            f"odds: {X_test.iloc[i][f'player{int(y_test.array[i])}_odds']}.    balance: {round(balance, 2)}")
    else:
        bad += 1
        print(f"odds: -1.   balance: {round(balance, 2)}")

print("=======================================================================================")
print(f'good: {good}. bad: {bad}. win_rate: {good / (good + bad)}')
print(f'virtual balance: {round(balance, 2)}')
print(f'earnings per match: {round(balance, 2) / (good + bad)}')
print(f'total prediction roi: {round(roi, 2)}')
try:
    print(
        f'yesterday results: win:{yesterday_win} lose:{yesterday_lose} win_rate: {round(yesterday_win / (yesterday_win + yesterday_lose) ,2)} roi:{yesterday_roi}')
except:
    pass
print("=======================================================================================")
print(result.summary())
