from explanatory_variables import EXPLANATORY_VARIABLES
import pandas as pd
import statsmodels.api as sm
from sklearn.model_selection import train_test_split
import numpy as np
from datetime import datetime, timedelta, timezone
import lightgbm as lgb  # LightGBM
import optuna
import matplotlib.pyplot as plt

from contextlib import contextmanager
import sys
import os


@contextmanager
def suppress_stdout():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout


if __name__ == "__main__":
    for tour_type in ["atp", "wta"]:
        df = pd.read_csv(f"{tour_type}.csv")
        roi = df["prediction_roi"].sum()
        df = df[EXPLANATORY_VARIABLES]
        df = df.dropna()

        x = pd.get_dummies(df.drop(columns='winner'))  # 説明変数

        y = df['winner']  # 目的変数

        X_train, X_test, y_train, y_test = train_test_split(
            x, y, train_size=0.7, random_state=0)

        lgb_train = lgb.Dataset(X_train, y_train)
        lgb_eval = lgb.Dataset(X_test, y_test, reference=lgb_train)

        params = {
            'boosting_type': 'gbdt',
            'objective': 'regression',
            'metric': {'l2', 'l1'},
            'num_leaves': 31,
            'learning_rate': 0.01,
            'feature_fraction': 0.9,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': 0,
            'max_depth': 3
        }

        evals_result = {}

        with suppress_stdout():
            gbm = lgb.train(params,
                            lgb_train,
                            num_boost_round=2000,
                            valid_sets=[lgb_train, lgb_eval],
                            evals_result=evals_result,
                            early_stopping_rounds=10,
                            )

        lgb.plot_metric(evals_result, metric='l1')
        plt.show()
        plt.savefig(f'{tour_type}.png')
        gbm.save_model(f"{tour_type}_lightbgm_model.pkl")

        predictions = gbm.predict(X_test)
        try:
            predictions = predictions.array
        except:
            pass
        good = 0
        bad = 0
        balance = 0

        for i in range(len(predictions)):
            balance -= 1
            # if(predictions[i] >= 1.2 and predictions[i] <= 1.8):
            #     continue
            if(round(predictions[i]) == int(y_test.array[i])):
                good += 1
                balance += X_test.iloc[i][f'player{int(y_test.array[i])}_odds']
            else:
                bad += 1

        print("=======================================================================================")
        print(f"tour_type: {tour_type}")
        print(f'good: {good}. bad: {bad}. win_rate: {good / (good + bad)}')
        print(f'virtual balance: {round(balance, 2)}')
        print(f'earnings per match: {round(balance, 2) / (good + bad)}')
        print(f'total prediction roi: {round(roi, 2)}')

    print("=======================================================================================")
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
    try:
        print(
            f'yesterday results: win:{yesterday_win} lose:{yesterday_lose} win_rate: {round(yesterday_win / (yesterday_win + yesterday_lose) ,2)} roi:{yesterday_roi}')
    except:
        pass
