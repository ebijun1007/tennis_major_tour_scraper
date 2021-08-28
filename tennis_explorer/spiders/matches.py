from datetime import datetime, timedelta, timezone
from os import path
from prediction_model import EXPLANATORY_VARIABLES
import requests  # to get image from the web
import scrapy
from bs4 import BeautifulSoup
import re
import pandas as pd
import io
import statsmodels.api as sm
import wget
import csv
import os
import json


class MatchesExplorer(scrapy.Spider):
    name = "matches"
    HOME_PAGE = "https://www.tennisexplorer.com/"
    jst = timezone(timedelta(hours=9), 'JST')
    now = datetime.now(jst)
    tomorrow = now + timedelta(days=1)
    next_day_search_condition = f"&year={tomorrow.year}&month={tomorrow.month:02}&day={tomorrow.day:02}"
    TODAYS_MATCH = [
        "https://www.tennisexplorer.com/matches/?type=atp-single&timezone=+9",
        "https://www.tennisexplorer.com/matches/?type=wta-single&timezone=+9",
        f"https://www.tennisexplorer.com/next/?type=atp-single{next_day_search_condition}&timezone=+9",
        f"https://www.tennisexplorer.com/next/?type=wta-single{next_day_search_condition}&timezone=+9",
    ]
    CRAWL_FLAG = False

    LEARNED_MODEL = "learned_model.pkl"
    NEXT_24_HOURS_MATCHES = "./data/next_48_hours_match.csv"
    os.remove(NEXT_24_HOURS_MATCHES) if os.path.exists(
        NEXT_24_HOURS_MATCHES) else None
    prediction_model = sm.load("learned_model.pkl")  # load from local

    def start_requests(self):
        yield scrapy.Request(url=self.HOME_PAGE, callback=self.parse_main_tournaments, meta={"dont_cache": True})

    # get main tournament names
    def parse_main_tournaments(self, response):
        atp_competitions = self.get_main_tournaments(response.css(
            'div#idxActTour div.half-l'))
        wta_competitions = self.get_main_tournaments(
            response.css('div#idxActTour div.half-r'))
        self.main_competitions = list(dict.fromkeys(
            atp_competitions + wta_competitions))
        for url in self.TODAYS_MATCH:
            yield scrapy.Request(url=url, callback=self.parse_todays_match, meta={"dont_cache": True})

    # get only main tournaments from list. exclude lower level tournaments
    def get_main_tournaments(self, table):
        x = table.css('td::text').getall()
        lower_level_tournaments_index = list(
            filter(('\xa0').__ne__, x)).index('Lower level tournaments')
        match_list = list(filter(lambda name: name not in ['\xa0'], table.css(
            'td a::text').getall()))[0:lower_level_tournaments_index-1]
        return list(filter(lambda name: name not in ['Davis Cup'], match_list))

    def parse_todays_match(self, response):
        for tr in response.css('table.result tr'):
            if(tr.css('tr::attr(class)').get() == "head flags"):
                self.CRAWL_FLAG = tr.css(
                    'a::text').get() in self.main_competitions
            else:
                if(self.CRAWL_FLAG):
                    if not tr.css('td.nbr').get():
                        continue
                    detail_page = tr.css(
                        'a[title="Click for match detail"]::attr(href)').get()
                    if(detail_page):
                        yield scrapy.Request(url=response.urljoin(detail_page), callback=self.parse_detail)

    def parse_detail(self, response):
        player_profile_urls = response.css('th.plName a::attr(href)').getall()
        title = f'{response.css("#center > div:nth-child(2) > a ::text").get()}{response.xpath("/html/body/div[1]/div[1]/div/div[3]/div[3]/div[1]/text()[2]").get()}'
        if "Qualification" in title:
            return
        if "qualification" in title:
            return
        time_stamp = self.parse_timestamp(response.xpath(
            '//*[@id="center"]/div[1]/span/text()').get(), response.xpath('//*[@id="center"]/div[1]/text()[1]').get())
        surface = title.split(',')[2].lstrip()
        H2H = response.xpath('//*[@id="center"]/h2[1]').get()
        odds = self.get_odds(response.css('div#oddsMenu-1-data table'))
        player1 = self.parse_player_profile(
            response.urljoin(player_profile_urls[0]), surface)
        player1["H2H"] = get_integer(H2H.split(
            ":")[-1].split("-")[0])[0] if len(H2H.split(":")) == 2 else 0
        player1["elo"] = self.get_surface_elo(player1["name"], surface)
        player1["odds"] = odds[0]
        player2 = self.parse_player_profile(
            response.urljoin(player_profile_urls[1]), surface)
        player2["H2H"] = get_integer(H2H.split(
            ":")[-1].split("-")[1])[0] if len(H2H.split(":")) == 2 else 0
        player2["elo"] = self.get_surface_elo(player2["name"], surface)
        player2["odds"] = odds[1]
        player1_data = {f"player1_{key}": value for (
            key, value) in player1.items()}
        player2_data = {f"player2_{key}": value for (
            key, value) in player2.items()}
        data = {}
        data.update(player1_data)
        data.update(player2_data)
        predict = self.predict(data)
        base = {
            "match_id": str(response.url).split("id=")[1],
            "time_stamp": time_stamp,
            "title": title,
            "predict": predict,
        }
        base.update(data)

        with open(self.NEXT_24_HOURS_MATCHES, 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=base.keys())
            if csvfile.tell() == 0:
                writer.writeheader()
            writer.writerow(base)

    def parse_timestamp(self, date_string, time_string):
        time = time_string
        if date_string == "Today":
            date = f'{self.now.year:02}-{self.now.month:02}-{self.now.day:02}'
        else:
            date = get_integer(date_string)
            date = f'{date[2]}-{date[1]}-{date[0]}'

        return f'{date}-{"-".join(get_integer(time))}'

    # get elo rating from github and return them as pandas dataframe
    def get_elo_ranking(self):
        url = "https://raw.githubusercontent.com/ebijun1007/tennis_elo_scraper/main/latest/atp.csv"
        raw_csv = requests.get(url).content
        df1 = pd.read_csv(io.StringIO(raw_csv.decode('utf-8')))

        url = "https://raw.githubusercontent.com/ebijun1007/tennis_elo_scraper/main/latest/wta.csv"
        raw_csv = requests.get(url).content
        df2 = pd.read_csv(io.StringIO(raw_csv.decode('utf-8')))

        return pd.concat([df1, df2], ignore_index=True)

    def name_order(self, name):
        if(len(ordered_name := name.split(" ")) == 2):
            return ordered_name[1] + " " + ordered_name[0]
        elif(len(ordered_name) == 3):
            return ordered_name[2] + " " + ordered_name[0] + " " + ordered_name[1]
        elif(len(ordered_name) == 4):
            return ordered_name[1] + " " + ordered_name[0]

    def get_surface_elo(self, player, surface):
        df = self.get_elo_ranking()
        try:
            row = df[df['Player'].str.contains(".".join(player.split(' ')))]
            elo = float(row.iloc[0]['Elo'])
            elo_surface = float(row.iloc[0][f'{surface.lower()[0]}Elo'])
            return round((elo + elo_surface) / 2)
        except:
            return "-"

    def get_odds(self, table):
        odds = ["-", "-"]
        for tr in table.css('tr'):
            if 'Pinnacle' in tr.css('td ::text').getall():
                odds = tr.css('div.odds-in::text').getall()
                break
        return odds

    # parse player profile page
    def parse_player_profile(self, url, surface):
        soup = BeautifulSoup(requests.get(url).content, "lxml")
        table = soup.find("table", {"class": "plDetail"})
        name = self.name_order(table.find('h3').text)
        data = table.find_all('div', {"class": "date"})
        country = [row.text for row in data if "Country" in row.text][0].split(": ")[
            1]
        try:
            height, weight = get_integer(
                [row.text for row in data if "Height / Weight" in row.text][0])
        except:
            height, weight = ["-", "-"]
        age = get_integer(
            [row.text for row in data if "Age" in row.text][0])[0]
        try:
            current_rank, highest_rank = get_integer(
                [row.text for row in data if "Current/Highest rank" in row.text][0])
        except:
            current_rank, highest_rank = ["-", "-"]

        wl_table = soup.find("div", {"id": "balMenu-1-data"})
        heads = [x.text for x in wl_table.find('tr').find_all('th')]
        surface_index = heads.index(surface.capitalize())
        year_row = wl_table.find('tbody').find_all('tr')[0]
        year_wl = year_row.find_all('td')[1].text
        year_surface_wl = year_row.find_all('td')[surface_index].text
        career_row = wl_table.find('tfoot').find('tr')
        career_wl = career_row.find_all('td')[1].text
        career_surface_wl = career_row.find_all('td')[surface_index].text

        year_total_win = year_wl.split('/')[0]
        year_total_lose = year_wl.split('/')[1]
        year_surface_win = year_surface_wl.split('/')[0]
        year_surface_lose = year_surface_wl.split('/')[1]
        career_total_win = career_wl.split('/')[0]
        career_total_lose = career_wl.split('/')[1]
        career_surface_win = career_surface_wl.split('/')[0]
        career_surface_lose = career_surface_wl.split('/')[1]

        roi = self.calc_roi(
            soup.find('div', {'id': f'matches-2021-1-data'}))

        return{
            "name": name,
            "country": country,
            "height": height,
            "weight": weight,
            "age": age,
            "current_rank": current_rank,
            "highest_rank": highest_rank,
            "year_total_win": year_total_win,
            "year_total_lose": year_total_lose,
            "year_surface_win": year_surface_win,
            "year_surface_lose": year_surface_lose,
            "career_total_win": career_total_win,
            "career_total_lose": career_total_lose,
            "career_surface_win": career_surface_win,
            "career_surface_lose": career_surface_lose,
            "roi": roi,
        }

    def calc_roi(self, table):
        balance = 1
        for tr in table.find_all('tr'):
            if "Result" in tr.text:
                continue
            win = "notU" in str(tr.find('a'))
            try:
                odds = float(tr.find('td', {"class": "course"}).text)
            except:
                odds = 1.0
            if(win):
                balance += float(odds - 1)
            else:
                balance -= 1
        return round(balance, 2)

    def predict(self, data):
        df = pd.DataFrame.from_dict(data, orient='index').T
        df = df.dropna()

        x = df[EXPLANATORY_VARIABLES]  # 説明変数

        try:
            predict = round(self.prediction_model.predict(
                x.astype(float)).array[0], 2)
            if predict != 0 and predict < 1:
                predict = 1.00
            elif predict > 2:
                predict = 2.00
            return predict
        except Exception as e:
            print(e)
            return 0


def get_integer(string):
    return re.findall(r'\d+', string)
