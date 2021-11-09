from explanatory_variables import EXPLANATORY_VARIABLES
import pandas as pd
import statsmodels.api as sm
from sklearn.model_selection import train_test_split
import numpy as np
from datetime import datetime, timedelta, timezone
import lightgbm as lgb  # LightGBM
import matplotlib.pyplot as plt
import sklearn.metrics
import optuna

from contextlib import contextmanager


def calc_history():
    import os
    import pandas as pd
    for csv_data in os.listdir("data"):
        try:
            df = pd.read_csv(f'./data/{csv_data}')
            win = len(
                df.loc[df['prediction_roi'] > 0].index)
            lose = len(
                df.loc[df['prediction_roi'] < 0].index)
            roi = round(
                df["prediction_roi"].sum(), 2)
            print(
                f'{csv_data}: win:{win} lose:{lose} win_rate: {round(win / (win + lose) ,2)} roi:{roi}')
        except Exception as e:
            print(e)
            continue


def objective(trial, X_train, X_test, y_train, y_test):
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    dtrain = lgb.Dataset(X_train, label=y_train)
    dvalid = lgb.Dataset(X_test, label=y_test)

    param = {
        "objective": "regression",
        "boosting_type": "gbdt",
        'verbose': -1,
        'metric': {'l2', 'l1'},
        "lambda_l1": trial.suggest_float("lambda_l1", 1e-8, 10.0),
        "lambda_l2": trial.suggest_float("lambda_l2", 1e-8, 10.0),
        "num_leaves": trial.suggest_int("num_leaves", 2, 256),
        "feature_fraction": trial.suggest_float("feature_fraction", 0.4, 1.0),
        "bagging_fraction": trial.suggest_float("bagging_fraction", 0.4, 1.0),
        "bagging_freq": trial.suggest_int("bagging_freq", 1, 7),
        "min_child_samples": trial.suggest_int("min_child_samples", 5, 100),
    }

    # Add a callback for pruning.
    gbm = lgb.train(
        param, dtrain, valid_sets=[dtrain, dvalid], verbose_eval=False
    )

    preds = gbm.predict(X_test)
    pred_labels = np.rint(preds)
    accuracy = sklearn.metrics.accuracy_score(y_test, pred_labels)
    return accuracy


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

        study = optuna.create_study(direction="maximize")
        study.optimize(lambda trial: objective(
            trial, X_train, X_test, y_train, y_test), n_trials=100)

        trial = study.best_trial

        lgb_train = lgb.Dataset(X_train, y_train)
        lgb_eval = lgb.Dataset(X_test, y_test, reference=lgb_train)

        evals_result = {}
        params = trial.params
        params.update({
            'boosting_type': 'gbdt',
            'objective': 'regression',
            'metric': {'l2', 'l1'},
            'verbose': -1,
        })

        gbm = lgb.train(params,
                        lgb_train,
                        num_boost_round=2000,
                        valid_sets=[lgb_train, lgb_eval],
                        evals_result=evals_result,
                        early_stopping_rounds=7,
                        verbose_eval=False,
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
        calc_history()
        print("=======================================================================================")

        print(f"tour_type: {tour_type}")

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

        print(f"good_roi(over 10) summary is: {round(goor_roi_sum, 2)}")
