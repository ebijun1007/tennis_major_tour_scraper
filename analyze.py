import pandas as pd
import os
import numpy as np
from datetime import datetime, timedelta, timezone
import matplotlib.pyplot as plt


def calc_history():
    plot_x = []
    plot_y = []
    sum = 0.0
    for csv_data in sorted(os.listdir("data")):
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
            sum += float(roi)
            plot_x.append(csv_data)
            plot_y.append(sum)
        except Exception as e:
            print(e)
            continue

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(plot_x, plot_y)
    plt.savefig("roi")


if __name__ == "__main__":
    calc_history()
    for tour_type in ["atp", "wta", "merged"]:
        count = 0
        df = pd.read_csv(f"{tour_type}.csv")
        roi = df["prediction_roi"].sum()

        good = 0
        bad = 0
        balance = 0
        the_bookmamkers_roi = 0  # result set of odds >= 1.7

        print(f"tour_type: {tour_type}")
        print(f"roi: {roi}")
        print(f"roi per title: {df.groupby('title')['prediction_roi'].sum()}")

        # 年間ROIが高い選手に賭け続けた場合
        higher_roi_sum = 0
        lower_roi_sum = 0
        for index, row in df.iterrows():
            roi_higher = 1 if row['player1_roi'] > row['player2_roi'] else 2
            prediction = int(row["predict"])
            predicted_reteurn_odds = float(
                row[f'player{prediction}_odds']) if prediction != 0 else 0
            if(row["prediction_roi"] <= 0.1 or row["prediction_roi"] == -1):
                count += 1
                winner = row['winner']
                higher_roi_sum -= 1
                lower_roi_sum -= 1
                if np.isnan(row[f'player{winner}_odds']):
                    continue
                if winner == roi_higher:
                    higher_roi_sum += float(row[f'player{winner}_odds'])
                else:
                    lower_roi_sum += float(row[f'player{winner}_odds'])
            if(predicted_reteurn_odds >= 1.7):
                the_bookmamkers_roi += row["prediction_roi"]

        print(f"higher_roi summary is: {round(higher_roi_sum, 2)}")
        print(f"lower_roi summary is: {round(lower_roi_sum, 2)}")
        print(
            f"the_bookmamkers_roi summary is: {round(the_bookmamkers_roi, 2)}")
        print(f"count: {count}")
