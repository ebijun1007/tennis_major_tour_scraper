# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import os
import traceback


from decimal import Decimal
import json
import pandas as pd
import boto3
from boto3.dynamodb.types import TypeSerializer

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


class OddsPortalPipeline:
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
