import os
import glob
import pandas as pd
import lightgbm as lgb  # LightGBM
from explanatory_variables import EXPLANATORY_VARIABLES

atp_prediction_model = lgb.Booster(
    model_file="atp_lightbgm_model.pkl")  # load from local
wta_prediction_model = lgb.Booster(
    model_file="wta_lightbgm_model.pkl")  # load from local

path = "./data/"


def predict(match_type, data):
    if match_type == "atp":
        prediction_model = atp_prediction_model
    elif match_type == "wta":
        prediction_model = wta_prediction_model
    df = data

    x = df[EXPLANATORY_VARIABLES].drop(columns='winner')  # 説明変数

    try:
        predict = round(prediction_model.predict(
            x.astype(float)).array[0], 2)
    except AttributeError:
        predict = round(prediction_model.predict(
            x.astype(float))[0], 2)
    except Exception as e:
        return 0

    try:
        if predict != 0 and predict < 1:
            predict = 1.00
        elif predict > 2:
            predict = 2.00
        return predict
    except Exception as e:
        return 0


all_files = glob.glob(os.path.join(path, "20*.csv"))
for f in all_files:
    df = pd.read_csv(f, sep=',')
    try:
        df['predict']
    except KeyError:
        df['predict'] = [0.0] * len(df)
    for i in df.index:
        # print(df.iloc[i].to_dict())
        df.at[i, "title"] = df.at[i, "title"].split(',')[0]
        df.at[i, "round"] = df.at[i,
                                  "round"] or df.at[i, "title"].split(',')[1]
        df.at[i, "surface"] = df.at[i,
                                    "surface"] or df.at[i, "title"].split(',')[2]
        df.at[i, "predict"] = predict(
            df.at[i, "tour"], df.iloc[[i]])
        predicted_winner = round(df.at[i, "predict"], 0)

        if(predicted_winner > 0):
            winner = df.at[i, "title"] = df.at[i, "winner"]
            if predicted_winner == winner:
                df.at[i, "prediction_roi"] = df.at[i, f"player{winner}_odds"]
            else:
                df.at[i, "prediction_roi"] = -1
        else:
            df.at[i, "prediction_roi"] = 0

    df.drop_duplicates().to_csv(f, index=False)
