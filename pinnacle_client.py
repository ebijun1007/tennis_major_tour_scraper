import os
import pinnacle

# -*- coding: utf-8 -*-
import uuid
import datetime

from pinnacle import resources
from pinnacle.enums import OddsFormat, Boolean, WinRiskType, FillType
from pinnacle.endpoints.baseendpoint import BaseEndpoint
from pinnacle.utils import clean_locals

USERNAME = os.environ.get('PINNACLE_USERNAME')
PASSWORD = os.environ.get('PINNACLE_PASSWORD')
TENNIS_ID = 33
PERIOD_NUMBER = 0
MAX_BET_PRICE = 200
IGNORE_WORD = ["ITF", "Doubles"]


class Betting(pinnacle.endpoints.baseendpoint.BaseEndpoint):
    def place_bet(self, sport_id, event_id, line_id, period_number, bet_type, stake, team=None, side=None,
                  alt_line_id=None, win_risk_stake=WinRiskType.Risk.value, accept_better_line=Boolean.TRUE.name,
                  odds_format=OddsFormat.Decimal.value, fill_type=FillType.Normal, pitcher1_must_start=None,
                  pitcher2_must_start=None, customer_reference=None, session=None):
        """
        Place bet in the system.

        :param sport_id: sport identification
        :param event_id: event identification
        :param line_id: Line identification
        :param period_number: This represents the period of the match. 
        :param bet_type: type of bet to be placed, see pinnacle.enums.BetType
        :param stake: Wagered amount in Clients currency
        :param team: Chosen team type. This is needed only for SPREAD, MONEYLINE and TEAM_TOTAL_POINTS bet types
        :param side: Chosen side. This is needed only for TOTAL_POINTS and TEAM_TOTAL_POINTS bet type
        :param alt_line_id: Alternate line identification
        :param win_risk_stake: Whether the stake amount is risk or win amount
        :param accept_better_line: Whether or not to accept a bet when there is a line change in favor of the client.
        :param odds_format: Bet is processed with this odds format.
        :param fill_type: FillAndKill, if stake > maxbet will fill max bet. FillMaxLimit, ignore stake and stake to max bet.
        :param pitcher1_must_start: Baseball only. Refers to the pitcher for TEAM_TYPE. Team1. 
                                    Only for MONEYLINE bet type, for all other bet types this has to be TRUE.
        :param pitcher2_must_start: Baseball only. Refers to the pitcher for TEAM_TYPE. Team2. 
                                    Only for MONEYLINE bet type, for all other bet types this has to be TRUE.
        :param customer_reference: Reference for customer to use.
        :param session: requests session to be used.
        :return: bet success/failure.
        """
        unique_request_id = str(uuid.uuid4())
        params = clean_locals(locals())
        date_time_sent = datetime.datetime.utcnow()
        response = self.request(
            "POST", method='/v2/bets/straight', data=params, session=session)
        return self.process_response(
            response.json(), resources.PlaceBetDetails, date_time_sent, datetime.datetime.utcnow()
        )


api = pinnacle.APIClient(USERNAME, PASSWORD)
api.betting = Betting(api)


def search_event(home, away):
    tennis_events = api.market_data.get_fixtures(TENNIS_ID)
    for league in tennis_events["league"]:
        if any(word in league["name"] for word in IGNORE_WORD):
            continue
        for event in league["events"]:
            if("Lauren Davis" == event["home"] or "Lauren Davis" == event["away"]):
                return league["id"], event["id"]


def get_line(league_id, event_id, team):
    return api.market_data.get_line(league_id=league_id,
                                    event_id=event_id,
                                    team=team,
                                    sport_id=TENNIS_ID,
                                    bet_type=pinnacle.enums.BetType.MoneyLine.value,
                                    period_number=PERIOD_NUMBER)


# api.betting.place_bet({sport_id: 33, bet_type: pinnacle.enums.BetType.MoneyLine.value,
#                       period_number: 0, stake: MAX_BET_PRICE, line_id: 1632108273, event_id: 1550157432})


def place_bet(line, event_id, team):
    return api.betting.place_bet(
        team=team,
        event_id=event_id,
        line_id=line["lineId"],
        stake=MAX_BET_PRICE,
        bet_type=pinnacle.enums.BetType.MoneyLine.value,
        sport_id=TENNIS_ID,
        period_number=PERIOD_NUMBER,
        fill_type=pinnacle.enums.FillType.Normal.value
    )


# >> > api.market_data.get_line(sport_id=33, bet_type=pinnacle.enums.BetType.MoneyLine.value, period_number=0, league_id=3931, event_id=1550157432, team="Team1")
# api.betting.place_bet(sport_id=33, bet_type=pinnacle.enums.BetType.MoneyLine.value, period_number=0, stake=MAX_BET_PRICE)

def main():
    name = "Lauren Davis"
    predict = 1
    league_id, event_id = search_event(name, name)
    line = get_line(league_id, event_id, f"Team{predict}")
    bet = place_bet(line, event_id, f"TEAM{predict}")
    # print(league_id, event_id)
    # print(line)
    print(bet)


if __name__ == "__main__":
    main()
