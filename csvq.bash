csvq '''
SELECT
  SUM(
    CASE
      WHEN winner = 2 AND predict > 1.5
        THEN player2_odds
      WHEN winner = 1 AND predict > 1.5
        THEN -1
    END
  ),
  SUM(
    CASE
      WHEN winner = 1 AND predict < 1.5
        THEN player1_odds
      WHEN winner = 2 AND predict < 1.5
        THEN -1
    END
  )
FROM `merged.csv`
WHERE predict IS NOT NULL
'''


