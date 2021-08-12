import pandas as pd
import statsmodels.api as sm
import wget

def handler(event, context):
  result = sm.load(wget.download("https://github.com/ebijun1007/tennis_major_tour_scraper/raw/main/learned_model.pkl"))

  df = pd.DataFrame.from_dict(event, orient='index').T
  df = df.dropna()

  x = df[[
      'player1_height',
      'player1_weight',
      'player1_age',
      'player1_current_rank',
      'player1_highest_rank',
      'player1_year_total_win',
      'player1_year_total_lose',
      'player1_year_surface_win',
      'player1_year_surface_lose',
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
      'player2_roi',
      'player2_odds',
      'player2_H2H',
      'player2_elo'
  ]]  # 説明変数

  try:
      score = round(result.predict(x.astype(float)).array[0],2)
  except:
      score = 0

  return {"score": score}