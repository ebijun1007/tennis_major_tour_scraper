import pandas as pd
import statsmodels.api as sm
from sklearn.model_selection import train_test_split
import numpy as np


df = pd.read_csv('merged.csv')
df = df.dropna()

x = pd.get_dummies(df[[
    'player1_height',
    'player1_weight',
    'player1_age',
    'player1_current_rank',
    'player1_highest_rank',
    'player1_year_total_win',
    'player1_year_total_lose',
    'player1_year_surface_win',
    'player1_year_surface_lose',
    'player1_career_total_win',
    'player1_career_total_lose',
    'player1_career_surface_win',
    'player1_career_surface_lose',
    'player1_roi',
    'player1_odds',
    'player1_H2H',
    'player1_elo',
    'player2_height',
    'player2_weight',
    'player2_age',
    'player2_current_rank',
    'player2_highest_rank',
    'player2_year_total_win',
    'player2_year_total_lose',
    'player2_year_surface_win',
    'player2_year_surface_lose',
    'player2_career_total_win',
    'player2_career_total_lose',
    'player2_career_surface_win',
    'player2_career_surface_lose',
    'player2_roi',
    'player2_odds',
    'player2_H2H',
    'player2_elo'
]])  # 説明変数
y = df['winner']  # 目的変数

# X_train, X_test, y_train, y_test = train_test_split(
#     x, y, train_size=0.8, random_state=0)

# 定数項(y切片)を必要とする線形回帰のモデル式ならば必須
X = sm.add_constant(x)

# 最小二乗法でモデル化
model = sm.OLS(y, X.astype(float))
result = model.fit()

# 重回帰分析の結果を表示する
print(result.summary())
