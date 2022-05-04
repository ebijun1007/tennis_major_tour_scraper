import os

import boto3
from boto3.dynamodb.conditions import Key
from get_roi import query_items_by_player_surface, query_h2h

dynamodb = boto3.resource(
    'dynamodb', endpoint_url=os.environ.get("DYNAMODB_HOST"), region_name="ap-northeast-1")
dynamo_table = dynamodb.Table("TennisPlayerROI")


def main():
    items = scan_all_items()
    balance_roi_career = 0
    count_career = 0

    for i, item in enumerate(items):
        try:
            surface = item["surfaceTimestamp"].split("#")[0]
            timestamp = item["surfaceTimestamp"].split("#")[1]

            roi_home = calc_roi(query_items_by_player_surface(
                item["playerName"], surface, to_date=timestamp))
            roi_enemy = calc_roi(query_items_by_player_surface(
                item["enemy"], surface, to_date=timestamp))

            if predict_home_win(roi_home, roi_enemy):
                balance_roi_career += bet(item,
                                          roi_home, roi_enemy)
                count_career += 1

        except Exception as e:
            print(e)
            continue


def predict_home_win(roi_home, roi_enemy):
    return roi_home - roi_enemy > 1


def bet(item, roi_home, roi_enemy):
    match_roi = item["roi"]
    h2h_win_count = h2h(item["playerName"], item["enemy"], item["timestamp"])
    player_roi_diff = roi_home - roi_enemy
    stake = player_roi_diff * (h2h_win_count + 1)
    result = stake * match_roi
    return result


def h2h(home, away, to_date=None):
    items = query_h2h(home, away, to_date=to_date)
    return len([item for item in items if item["roi"] > 0])


def scan_all_items():
    response = dynamo_table.scan()
    data = response['Items']
    while 'LastEvaluatedKey' in response:
        response = dynamo_table.scan(
            ExclusiveStartKey=response['LastEvaluatedKey'])
        data.extend(response['Items'])
    return data


def calc_roi(items):
    roi_career = 0
    for i, item in enumerate(items):
        roi_career += item["roi"]

    return roi_career


if __name__ == "__main__":
    main()
