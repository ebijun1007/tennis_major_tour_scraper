from explanatory_variables import EXPLANATORY_VARIABLES
import pandas as pd
import statsmodels.api as sm
from sklearn.model_selection import train_test_split
import sklearn.datasets
import sklearn.metrics
import numpy as np
from datetime import datetime, timedelta, timezone
import lightgbm as lgb  # LightGBM
import matplotlib.pyplot as plt

from contextlib import contextmanager
import sys
import os

import optuna
from optuna.visualization import plot_contour
from optuna.visualization import plot_edf
from optuna.visualization import plot_intermediate_values
from optuna.visualization import plot_optimization_history
from optuna.visualization import plot_parallel_coordinate
from optuna.visualization import plot_param_importances
from optuna.visualization import plot_slice


@contextmanager
def suppress_stdout():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout


def objective(trial, tour_type):
    with suppress_stdout():
        """
        An objective function that accepts multiple parameters.
        """
        df = pd.read_csv(f"{tour_type}.csv")
        df = df[EXPLANATORY_VARIABLES]
        df = df.dropna()
        data = pd.get_dummies(df.drop(columns='winner'))  # 説明変数

        target = df['winner']  # 目的変数
        train_x, valid_x, train_y, valid_y = train_test_split(
            data, target, test_size=0.25)
        dtrain = lgb.Dataset(train_x, label=train_y)
        dvalid = lgb.Dataset(valid_x, label=valid_y)

        param = {
            "objective": "binary",
            "metric": "auc",
            "verbosity": -1,
            "boosting_type": "gbdt",
            "lambda_l1": trial.suggest_float("lambda_l1", 1e-8, 10.0, log=True),
            "lambda_l2": trial.suggest_float("lambda_l2", 1e-8, 10.0, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 2, 256),
            "feature_fraction": trial.suggest_float("feature_fraction", 0.4, 1.0),
            "bagging_fraction": trial.suggest_float("bagging_fraction", 0.4, 1.0),
            "bagging_freq": trial.suggest_int("bagging_freq", 1, 7),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 100),
        }

        evals_result = {}

        # Add a callback for pruning.
        pruning_callback = optuna.integration.LightGBMPruningCallback(
            trial, "auc")
        gbm = lgb.train(
            param, dtrain, valid_sets=[dvalid], verbose_eval=False, callbacks=[pruning_callback], evals_result=evals_result,
        )

        preds = gbm.predict(valid_x)
        pred_labels = np.rint(preds)
        accuracy = sklearn.metrics.accuracy_score(valid_y, pred_labels)
        return accuracy


def main():
    for tour_type in ["atp", "wta"]:
        study = optuna.create_study(
            pruner=optuna.pruners.MedianPruner(n_warmup_steps=10), direction="maximize"
        )
        def func(trial): return objective(trial, tour_type)
        study.optimize(func, n_trials=100)

        print("Number of finished trials: {}".format(len(study.trials)))

        print("Best trial:")
        trial = study.best_trial

        print("  Value: {}".format(trial.value))

        print("  Params: ")
        for key, value in trial.params.items():
            print("    {}: {}".format(key, value))

        # fig = plot_optimization_history(study)
        fig = optuna.visualization.plot_param_importances(study)
        fig.write_image(f'{tour_type}.png')

    #     x = pd.get_dummies(df.drop(columns='winner'))  # 説明変数

    #     y = df['winner']  # 目的変数

    #     X_train, X_test, y_train, y_test = train_test_split(
    #         x, y, train_size=0.7, random_state=0)

    #     lgb_train = lgb.Dataset(X_train, y_train)
    #     lgb_eval = lgb.Dataset(X_test, y_test, reference=lgb_train)

    #     params = {
    #         'boosting_type': 'gbdt',
    #         'objective': 'regression',
    #         'metric': {'l2', 'l1'},
    #         'num_leaves': 31,
    #         'learning_rate': 0.05,
    #         'feature_fraction': 0.9,
    #         'bagging_fraction': 0.8,
    #         'bagging_freq': 5,
    #         'verbose': 0
    #     }

    #     evals_result = {}

    #     with suppress_stdout():
    #         gbm = lgb.train(params,
    #                         lgb_train,
    #                         num_boost_round=2000,
    #                         valid_sets=[lgb_train, lgb_eval],
    #                         evals_result=evals_result,
    #                         early_stopping_rounds=10,
    #                         )

    #     lgb.plot_metric(evals_result, metric='l1')
    #     plt.show()
    #     plt.savefig(f'{tour_type}.png')
    #     gbm.save_model(f"{tour_type}_lightbgm_model.pkl")

    #     predictions = gbm.predict(X_test)
    #     try:
    #         predictions = predictions.array
    #     except:
    #         pass
    #     good = 0
    #     bad = 0
    #     balance = 0

    #     for i in range(len(predictions)):
    #         balance -= 1
    #         if(round(predictions[i]) == int(y_test.array[i])):
    #             good += 1
    #             balance += X_test.iloc[i][f'player{int(y_test.array[i])}_odds']
    #         else:
    #             bad += 1

    #     print("=======================================================================================")
    #     print(f"tour_type: {tour_type}")
    #     print(f'good: {good}. bad: {bad}. win_rate: {good / (good + bad)}')
    #     print(f'virtual balance: {round(balance, 2)}')
    #     print(f'earnings per match: {round(balance, 2) / (good + bad)}')
    #     print(f'total prediction roi: {round(roi, 2)}')

    # print("=======================================================================================")
    # jst = timezone(timedelta(hours=9), 'JST')
    # yesterday = datetime.now(jst) - timedelta(days=1)
    # try:
    #     yesterday_result_df = pd.read_csv(
    #         f'./data/{yesterday.year:04}-{yesterday.month:02}-{yesterday.day:02}.csv')
    #     yesterday_win = len(
    #         yesterday_result_df.loc[yesterday_result_df['prediction_roi'] > 0].index)
    #     yesterday_lose = len(
    #         yesterday_result_df.loc[yesterday_result_df['prediction_roi'] < 0].index)
    #     yesterday_roi = round(yesterday_result_df["prediction_roi"].sum(), 2)
    # except:
    #     pass
    # try:
    #     print(
    #         f'yesterday results: win:{yesterday_win} lose:{yesterday_lose} win_rate: {round(yesterday_win / (yesterday_win + yesterday_lose) ,2)} roi:{yesterday_roi}')
    # except:
    #     pass


if __name__ == "__main__":
    main()
