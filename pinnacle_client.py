import csv
import os
import datetime
import pinnacle
import slackweb


class PinnacleClient():
    USERNAME = os.environ.get('PINNACLE_USERNAME')
    PASSWORD = os.environ.get('PINNACLE_PASSWORD')
    SLACK = slackweb.Slack(url=os.environ.get('SLACK_WEBHOOK_URL'))
    TENNIS_ID = 33
    PERIOD_NUMBER = 0
    MAX_BET_PRICE = 200
    IGNORE_WORD = ["ITF", "Doubles"]
    TODAY = datetime.datetime.today()
    MATCH_FILE = "./data/next_48_hours_match.csv"
    api = pinnacle.APIClient(USERNAME, PASSWORD)

    def execute(self):
        self.load_matches()
        bet_list = self.api.betting.get_bets(
            from_date=self.TODAY, to_date=self.TODAY, betlist=pinnacle.enums.BetListType.Running.value)
        for match in self.matches:
            tour = match["tour"]
            if tour != "wta":
                continue
            home = match["player1_name"]
            away = match["player2_name"]
            predict = int(match["predict"])
            print(tour, home, away, predict)
            league_id, event_id = self.search_event(home, away)
            line = self.get_line(league_id, event_id, f"Team{predict}")
            if not any([bet for bet in bet_list["straightBets"] if bet['eventId'] == event_id]):
                self.SLACK.notify(self.place_bet(
                    line, event_id, f"TEAM{predict}"))

    def load_matches(self):
        with open(self.MATCH_FILE) as f:
            reader = csv.reader(f, skipinitialspace=True)
            header = next(reader)
            self.matches = [dict(zip(header, row)) for row in reader]

    def search_event(self, home, away):
        tennis_events = self.api.market_data.get_fixtures(self.TENNIS_ID)
        for league in tennis_events["league"]:
            if any(word in league["name"] for word in self.IGNORE_WORD):
                continue
            for event in league["events"]:
                if("Lauren Davis" == event["home"] or "Lauren Davis" == event["away"]):
                    return league["id"], event["id"]

    def get_line(self, league_id, event_id, team):
        return self.api.market_data.get_line(league_id=league_id,
                                             event_id=event_id,
                                             team=team,
                                             sport_id=self.TENNIS_ID,
                                             bet_type=pinnacle.enums.BetType.MoneyLine.value,
                                             period_number=self.PERIOD_NUMBER)

    def place_bet(self, line, event_id, team):
        return self.api.betting.place_bet(
            team=team,
            event_id=event_id,
            line_id=line["lineId"],
            stake=self.MAX_BET_PRICE,
            bet_type=pinnacle.enums.BetType.MoneyLine.value,
            sport_id=self.TENNIS_ID,
            period_number=self.PERIOD_NUMBER,
            fill_type=pinnacle.enums.FillType.Normal.value
        )
