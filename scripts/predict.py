import os

import boto3
from boto3.dynamodb.conditions import Key
from get_roi import query_items_by_player_surface, query_h2h

dynamodb = boto3.resource(
    'dynamodb', endpoint_url=os.environ.get("DYNAMODB_HOST"), region_name="ap-northeast-1")
dynamo_table = dynamodb.Table("TennisPlayerROI")


def main():
    items = scan_all_items()
    sum_roi_recent3 = 0
    sum_roi_recent5 = 0
    sum_roi_recent10 = 0
    sum_roi_career = 0

    count_recent3 = 0
    count_recent5 = 0
    count_recent10 = 0
    count_career = 0

    for i, item in enumerate(items):
        try:
            if i > 1000:
                break

            surface = item["surfaceTimestamp"].split("#")[0]
            timestamp = item["surfaceTimestamp"].split("#")[1]

            if "WTA" not in item["title"]:
                continue
            if "grass" not in surface:
                continue

            roi_home = calc_roi(query_items_by_player_surface(
                item["playerName"], surface, to_date=timestamp))
            roi_enemy = calc_roi(query_items_by_player_surface(
                item["enemy"], surface, to_date=timestamp))

            predict_recent3 = predict(
                roi_home["roi_recent3"], roi_enemy["roi_recent3"], item)
            predict_recent5 = predict(
                roi_home["roi_recent5"], roi_enemy["roi_recent5"], item)
            predict_recent10 = predict(
                roi_home["roi_recent10"], roi_enemy["roi_recent10"], item)
            predict_career = predict(
                roi_home["roi_career"], roi_enemy["roi_career"], item)

            if predict_recent3:
                sum_roi_recent3 += bet(item,
                                       roi_home["roi_recent3"], roi_enemy["roi_recent3"])
                count_recent3 += 1

            if predict_recent5:
                sum_roi_recent5 += bet(item,
                                       roi_home["roi_recent5"], roi_enemy["roi_recent5"])
                count_recent5 += 1

            if predict_recent10:
                sum_roi_recent10 += bet(item,
                                        roi_home["roi_recent10"], roi_enemy["roi_recent10"])
                count_recent10 += 1

            if predict_career:
                sum_roi_career += bet(item,
                                      roi_home["roi_career"], roi_enemy["roi_career"])
                count_career += 1

            # print(sum_roi_recent3,
            #       sum_roi_recent5, sum_roi_recent10, sum_roi_career)
            # print(" ", "roi:", item["roi"], " odds:",
            #       item["odds"], " bet: ", bet(item))

        except Exception as e:
            print(e)
            continue


def predict(roi_home, roi_enemy, item):
    return roi_home - roi_enemy > 1


def bet(item, roi_home, roi_enemy):
    match_roi = item["roi"]
    h2h_win_count = h2h(item["playerName"], item["enemy"], item["timestamp"])
    player_roi_diff = roi_home - roi_enemy
    stake = player_roi_diff * (h2h_win_count + 1)
    result = stake * match_roi
    print(item["playerName"], item["enemy"], item["title"],
          item["timestamp"], f" player_roi_diff: {player_roi_diff}", f" match_roi: {match_roi}", f" h2h_win_count: {h2h_win_count}", f" stake: {stake}", f" result: {result}")
    return result


def h2h(home, away, to_date=None):
    items = query_h2h(home, away, to_date=to_date)
    return len([item for item in items if item["roi"] > 0])


def scan_all_items():
    response = dynamo_table.scan()
    data = response['Items']
    # print(response['LastEvaluatedKey'])
    # レスポンスに LastEvaluatedKey が含まれなくなるまでループ処理を実行する
    while 'LastEvaluatedKey' in response:
        response = dynamo_table.scan(
            ExclusiveStartKey=response['LastEvaluatedKey'])
        # if 'LastEvaluatedKey' in response:
        #     print("LastEvaluatedKey: {}".format(response['LastEvaluatedKey']))
        data.extend(response['Items'])
    return data


def calc_roi(items):
    roi_recent3 = 0
    roi_recent5 = 0
    roi_recent10 = 0
    roi_career = 0

    for i, item in enumerate(items):
        if(i < 3):
            roi_recent3 += item["roi"]
        if(i < 5):
            roi_recent5 += item["roi"]
        if(i < 10):
            roi_recent10 += item["roi"]
        roi_career += item["roi"]

    return {
        "roi_recent3": roi_recent3,
        "roi_recent5": roi_recent5,
        "roi_recent10": roi_recent10,
        "roi_career": roi_career,
    }


if __name__ == "__main__":
    main()
