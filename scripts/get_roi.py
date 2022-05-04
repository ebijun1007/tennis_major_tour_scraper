import os
from datetime import datetime, timedelta

import boto3
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource(
    'dynamodb', endpoint_url=os.environ.get("DYNAMODB_HOST"), region_name="ap-northeast-1")
dynamo_table = dynamodb.Table("TennisPlayerROI")


def main():
    # example
    items = query_items_by_player_surface(
        "Nishikori.K", "clay", from_date="2010-01-01", to_date="2017-01-01", limit=10)
    for item in items:
        print(item)


def query_items_by_player_surface(player_name, surface, from_date="0000-00-00", to_date="9999-99-99", limit=999999):
    to_date = decrement_date(to_date)
    result = dynamo_table.query(
        KeyConditionExpression=Key('playerName').eq(player_name) &
        Key('surfaceTimestamp').between(
            f"{surface}#{from_date}", f"{surface}#{to_date}"),
        ScanIndexForward=False,  # 昇順か降順か(デフォルトはTrue=昇順),
        Limit=limit
    )
    return result["Items"]


def query_h2h(home, away, from_date="0000-00-00", to_date="9999-99-99"):
    result = dynamo_table.query(
        IndexName='head-to-head',
        KeyConditionExpression=Key('playerName').eq(
            home) & Key('enemy').eq(away),
        FilterExpression=Attr('timestamp').between(from_date, to_date),
        ScanIndexForward=False,  # 昇順か降順か(デフォルトはTrue=昇順),
    )
    return result["Items"]


def decrement_date(given_date):
    date_format = '%Y-%m-%d'
    dtObj = datetime.strptime(given_date, date_format)
    past_date = dtObj - timedelta(days=1)
    return past_date.strftime(date_format)


if __name__ == "__main__":
    main()
