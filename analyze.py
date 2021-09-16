from explanatory_variables import EXPLANATORY_VARIABLES
import pandas as pd
import statsmodels.api as sm
from sklearn.model_selection import train_test_split
import numpy as np
from datetime import datetime, timedelta, timezone
import lightgbm as lgb  # LightGBM
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
    for tour_type in ["atp", "wta", "merged"]:
        df_org = pd.read_csv(f"{tour_type}.csv")
        roi = df_org["prediction_roi"].sum()
        df = df_org[EXPLANATORY_VARIABLES]
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

        # 予想の値に応じた利益
        # 1.1以下もしくは1.9以上
        very_good_preedictions = df_org.query(
            '(predict > 1.9 or predict < 1.1) and (predict > 0)')
        very_good_preedictions_roi = very_good_preedictions['prediction_roi'].sum(
        )
        # 1.2以下もしくは1.8以上
        good_preedictions = df_org.query(
            '((predict < 1.9 and predict > 1.8) or (predict > 1.1 and predict < 1.2))')
        good_preedictions_roi = good_preedictions[
            'prediction_roi'].sum()
        # 1.3以下もしくは1.7以上
        normal_preedictions = df_org.query(
            '((predict < 1.8 and predict > 1.7) or (predict > 1.2 and predict < 1.3))')
        normal_preedictions_roi = normal_preedictions['prediction_roi'].sum()
        # 1.4以下もしくは1.6以上
        bad_preedictions = df_org.query(
            '((predict < 1.7 and predict > 1.5) or (predict > 1.3 and predict < 1.5))')
        bad_preedictions_roi = bad_preedictions[
            'prediction_roi'].sum()

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

        print(
            f'1.1以下もしくは1.9以上: {round(very_good_preedictions_roi, 2)} {len(very_good_preedictions)}試合 / {len(df_org)}試合中')
        print(
            f'1.2以下もしくは1.8以上: {round(good_preedictions_roi, 2)} {len(good_preedictions)}試合 / {len(df_org)}試合中')
        print(
            f'1.3以下もしくは1.7以上: {round(normal_preedictions_roi, 2)} {len(normal_preedictions)}試合 / {len(df_org)}試合中')
        print(
            f'1.4以下もしくは1.6以上: {round(bad_preedictions_roi, 2)} {len(bad_preedictions)}試合 / {len(df_org)}試合中')

        round_list = [
            "1. round", "2. round",
            "round of 16", "quarterfinal", "semifinal", "final"
        ]
        for r in round_list:
            roi = df_org.loc[df_org['round'] == r]['prediction_roi'].sum()
            print(f'{r} summary is: {round(roi, 2)}')

        # 年間ROIが高い選手に賭け続けた場合
        higher_roi_sum = 0
        lower_roi_sum = 0
        for index, row in df_org.iterrows():
            roi_higher = 1 if row['player1_roi'] > row['player2_roi'] else 2
            winner = row['winner']
            higher_roi_sum -= 1
            lower_roi_sum -= 1
            if np.isnan(row[f'player{winner}_odds']):
                continue
            if winner == roi_higher:
                higher_roi_sum += float(row[f'player{winner}_odds'])
            else:
                lower_roi_sum += float(row[f'player{winner}_odds'])

        print(f"higher_roi summary is: {round(higher_roi_sum, 2)}")
        print(f"lower_roi summary is: {round(lower_roi_sum, 2)}")

        # 年間ROIが5以上選手に賭け続けた場合。両者が超えている場合は高い方に賭ける
        goor_roi_sum = 0
        good_roi = 10
        for index, row in df_org.query(f'player1_roi > {good_roi} or player2_roi >{good_roi}').iterrows():
            winner = row['winner']
            good_roi_player = 1 if row["player1_roi"] > good_roi else 2
            goor_roi_sum -= 1
            if np.isnan(row[f'player{winner}_odds']):
                continue
            if winner == good_roi_player:
                goor_roi_sum += float(row[f'player{good_roi_player}_odds'])

        print(f"good_roi summary is: {round(goor_roi_sum, 2)}")

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
