# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import re
import os
import traceback
from datetime import datetime, timedelta


from decimal import Decimal
import json
import pandas as pd
import boto3
from boto3.dynamodb.conditions import Key, Attr
from tennis_explorer.pinnacle_client import PinnacleClient

# useful for handling different item types with a single interface
from tennis_explorer.sort_csv import sort_csv


class TennisExplorerPipeline:
    def process_item(self, item, spider):
        return item

    def close_spider(self, spider):
        try:
            print(spider.NEXT_24_HOURS_MATCHES)
            sort_csv(spider.NEXT_24_HOURS_MATCHES, 1, False)
        except Exception as e:
            pass


class OddsHistoryPipeline:
    def open_spider(self, spider):
        self.history = []
        self.dynamodb = boto3.resource(
            'dynamodb', endpoint_url=os.environ.get("DYNAMODB_HOST"), region_name="ap-northeast-1")

    def process_item(self, item, spider):
        self.history.append(item)
        self.put_item(item)
        return item

    def put_item(self, item):
        dynamo_table = self.dynamodb.Table("TennisPlayerROI")
        try:
            for i in range(1, 3):
                params = {
                    "playerName": item[f"player{i}_name"],
                    "timestamp": item["timestamp"],
                    "enemy": item[f"player{3 - i}_name"],
                    "surfaceTimestamp": f"{item['surface']}#{item['timestamp'].split(' ')[0]}",
                    "odds": item[f"player{i}_odds"],
                    "roi": round(item[f"player{i}_odds"] - 1, 2) if int(item["winner"]) == i else -1,
                    "title": item["title"],
                    "surface": item["surface"],
                }
                ddb_data = json.loads(json.dumps(params), parse_float=Decimal)
                print(ddb_data)
                dynamo_table.put_item(Item=ddb_data)
        except Exception:
            print(traceback.format_exc())

    def close_spider(self, spider):
        df = pd.DataFrame.from_dict(self.history)
        df = df.dropna()  # NaNを含むレコードを削除
        df = df[(df["player1_odds"] != "-") & (df["player2_odds"] != "-")]
        df = df.sort_values(by=['timestamp'])
        df.to_csv(r'odds_history.csv', index=False, header=True)


class AutobetPipeline:
    def open_spider(self, spider):
        self.dynamodb = boto3.resource(
            'dynamodb', endpoint_url=os.environ.get("DYNAMODB_HOST"), region_name="ap-northeast-1")
        self.dynamo_table = self.dynamodb.Table("TennisPlayerROI")
        self.pinnacle_client = PinnacleClient()
        self.pinnacle_match_list = self.pinnacle_client.load_matches()

    def process_item(self, item, spider):
        self.predict(item)
        return(item)

    def predict(self, item):
        player1 = item["player1_name"]
        player2 = item["player2_name"]
        player1_name = re.sub("\\s[A-Z]+\\.", "", player1)
        player2_name = re.sub("\\s[A-Z]+\\.", "", player2)
        league_id = event_id = team = stake = None

        if self.pinnacle_client.check_dup(player1_name, player2_name):
            return

        try:
            roi1 = self._calc_roi(
                self._query_items_by_player_surface(player1, item["surface"]))
            roi2 = self._calc_roi(
                self._query_items_by_player_surface(player2, item["surface"]))

            if self._predict_first_player_win(roi1, roi2):
                stake = self._calc_stake(player1, player2, roi1, roi2)
                team = "Team1"
                print(stake, team)

                league_id, event_id = self.pinnacle_client.search_event(
                    player1_name, player2_name)

            if self._predict_first_player_win(roi2, roi1):
                stake = self._calc_stake(player2, player1, roi2, roi1)
                team = "Team2"
                league_id, event_id = self.pinnacle_client.search_event(
                    player1_name, player2_name)

            line = self.pinnacle_client.get_line(
                league_id, event_id, team)
            # print(player1_name, player2_name, line, event_id, team, stake)
            # self.place_bet(line, event_id, team, stake)
        except:
            print(traceback.format_exc())

    def _calc_roi(self, items):
        return sum(item["roi"] for item in items)

    def _predict_first_player_win(self, first_player_roi, second_player_roi):
        return first_player_roi - second_player_roi > 1

    def _calc_stake(self, player1, player2, roi_player1, roi_player2):
        h2h_win_count = self._h2h(player1, player2)
        player_roi_diff = roi_player1 - roi_player2
        return player_roi_diff * (h2h_win_count + 1)

    def _h2h(self, player1, player2, to_date=None):
        items = self._query_h2h(player1, player2, to_date=to_date)
        return len([item for item in items if item["roi"] > 0])

    def _query_h2h(self, player1, player2, from_date="0000-00-00", to_date="9999-12-31"):
        result = self.dynamo_table.query(
            IndexName='head-to-head',
            KeyConditionExpression=Key('playerName').eq(
                player1) & Key('enemy').eq(player2),
            FilterExpression=Attr('timestamp').between(from_date, to_date),
            ScanIndexForward=False,  # 昇順か降順か(デフォルトはTrue=昇順),
        )
        return result["Items"]

    def _query_items_by_player_surface(self, player_name, surface, from_date="0000-00-00", to_date="9999-12-31", limit=999999):
        to_date = self.__decrement_date(to_date)
        result = self.dynamo_table.query(
            KeyConditionExpression=Key('playerName').eq(player_name) &
            Key('surfaceTimestamp').between(
                f"{surface}#{from_date}", f"{surface}#{to_date}"),
            ScanIndexForward=False,  # 昇順か降順か(デフォルトはTrue=昇順),
            Limit=limit
        )
        return result["Items"]

    def __decrement_date(self, given_date):
        date_format = '%Y-%m-%d'
        dtObj = datetime.strptime(given_date, date_format)
        past_date = dtObj - timedelta(days=1)
        return past_date.strftime(date_format)
