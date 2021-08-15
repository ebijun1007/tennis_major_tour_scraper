from datetime import datetime, timedelta, timezone
from os import path
import shutil  # to save it locally
import requests  # to get image from the web
import scrapy
from bs4 import BeautifulSoup
import pandas as pd
import io
import re
import csv
import random
import json


class ResultsExplorer(scrapy.Spider):
    name = "results"
    home_page = "https://www.tennisexplorer.com/"
    result_urls = {
        "atp": "https://www.tennisexplorer.com/results/?type=atp-single",
        "wta": "https://www.tennisexplorer.com/results/?type=wta-single"
    }
    jst = timezone(timedelta(hours=9), 'JST')
    now = datetime.now(jst) - timedelta(days=2)
    save_image_path = "./tennis_explorer/images/"
    search_results_conditions = f"&year={now.year}&month={now.month:02}&day={now.day:02}"
    MATCH_PREDICTION_JSON = './data/answer_check.json'

    def start_requests(self):
        yield scrapy.Request(url=self.home_page, callback=self.parse_main_tournaments)

    # get main tournament names
    def parse_main_tournaments(self, response):
        atp_competitions = self.get_main_tournaments(response.css(
            'div#idxActTour div.half-l'))
        wta_competitions = self.get_main_tournaments(
            response.css('div#idxActTour div.half-r'))
        self.main_competitions = list(dict.fromkeys(
            atp_competitions + wta_competitions))
        for tour, url in self.result_urls.items():
            yield scrapy.Request(url=url+self.search_results_conditions, callback=self.parse_results, meta={'tour': tour})

    # get only main tournaments from list. exclude lower level tournaments
    def get_main_tournaments(self, table):
        lower_level_tournaments_index = table.css(
            'td::text').getall().index('Lower level tournaments')
        list(filter(lambda name: name != '\xa0', table.css('td a::text').getall()))
        return list(filter(lambda name: name != '\xa0', table.css('td a::text').getall()))[0:lower_level_tournaments_index-1]

    # get results of maintournaments
    def parse_results(self, response):
        crawl_flag = False
        for tr in response.css('table.result tr'):
            if(tr.css('tr::attr(class)').get() == "head flags"):
                crawl_flag = tr.css(
                    'a::text').get() in self.main_competitions
            else:
                if(crawl_flag):
                    detail_page = tr.css(
                        'a[title="Click for match detail"]::attr(href)').get()
                    if(detail_page):
                        yield scrapy.Request(url=response.urljoin(detail_page), callback=self.parse_detail, meta=response.meta)
                else:
                    continue

    # get match details
    def parse_detail(self, response):
        player_profile_urls = response.css('th.plName a::attr(href)').getall()
        match_id = response.url.split('id=')[1]
        title = f'{response.css("#center > div:nth-child(2) > a ::text").get()}{response.xpath("/html/body/div[1]/div[1]/div/div[3]/div[3]/div[1]/text()[2]").get()}'
        game_round = title.split(',')[1].lstrip()
        surface = title.split(',')[2].lstrip()
        title = title.split(',')[0].lstrip()
        H2H = get_integer(response.xpath(
            '//*[@id="center"]/h2[1]//text()').get()) or [0, 0]
        odds = self.get_odds(response.css('div#oddsMenu-1-data table'))
        player1 = self.parse_player_profile(
            response.urljoin(player_profile_urls[0]), surface)
        player2 = self.parse_player_profile(
            response.urljoin(player_profile_urls[1]), surface)
        player1["odds"] = odds[0]
        player1["H2H"] = H2H[0]
        player1["elo"] = self.get_surface_elo(player1["name"], surface)
        player2["odds"] = odds[1]
        player2["H2H"] = H2H[1]
        player2["elo"] = self.get_surface_elo(player2["name"], surface)

        roi = None
        with open(self.MATCH_PREDICTION_JSON, 'r+') as f:
            data = json.load(f)
            winner_name = data.pop(match_id, None)
            if(winner_name):
                f.seek(0)  # rewind
                json.dump(data, f)
                f.truncate()
                if(winner_name == player1["name"]):
                    roi = round(float(player1["odds"]) - 1, 2)
                else:
                    roi = -1

        # shuffle winner
        winner, player1, player2 = self.shuffle_winner(player1, player2)

        # update keys
        player1 = {f'player1_{key}': value
                   for (key, value) in player1.items()}
        player2 = {f'player2_{key}': value
                   for (key, value) in player2.items()}

        match = {
            "match_id": match_id,
            "tour": response.meta["tour"],
            "title": title,
            "surface": surface,
            "round": game_round,
            "winner": winner,
            "prediction_roi": roi
        }
        match.update(player1)
        match.update(player2)

        with open(f'./data/{self.now.strftime("%Y-%m-%d")}.csv', 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=match.keys())
            if csvfile.tell() == 0:
                writer.writeheader()
            writer.writerow(match)

    # get elo rating from github and return them as pandas dataframe
    def get_elo_ranking(self):
        url = "https://raw.githubusercontent.com/ebijun1007/tennis_elo_scraper/main/latest/atp.csv"
        raw_csv = requests.get(url).content
        df1 = pd.read_csv(io.StringIO(raw_csv.decode('utf-8')))

        url = "https://raw.githubusercontent.com/ebijun1007/tennis_elo_scraper/main/latest/wta.csv"
        raw_csv = requests.get(url).content
        df2 = pd.read_csv(io.StringIO(raw_csv.decode('utf-8')))

        return pd.concat([df1, df2], ignore_index=True)

    # calc 50/50 of elo & elo_on_surface
    def get_surface_elo(self, player, surface):
        df = self.get_elo_ranking()
        try:
            row = df[df['Player'].str.contains(".".join(player.split(' ')))]
            elo = float(row.iloc[0]['Elo'])
            elo_surface = float(row.iloc[0][f'{surface.lower()[0]}Elo'])
            return round((elo + elo_surface) / 2)
        except:
            return "-"

    # get odds of pinnacle
    def get_odds(self, table):
        odds = ["-", "-"]
        for tr in table.css('tr'):
            if 'Pinnacle' in tr.css('td ::text').getall():
                odds = tr.css('div.odds-in::text').getall()
                break
        return odds

    def shuffle_winner(self, player1, player2):
        # if random becom True
        if(bool(random.getrandbits(1))):
            return [2, player2, player1]
        else:
            return [1, player1, player2]

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
        current_rank, highest_rank = get_integer(
            [row.text for row in data if "Current/Highest rank" in row.text][0])

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

    def name_order(self, name):
        if(len(ordered_name := name.split(" ")) == 2):
            return ordered_name[1] + " " + ordered_name[0]
        elif(len(ordered_name) == 3):
            return ordered_name[2] + " " + ordered_name[0] + " " + ordered_name[1]
        elif(len(ordered_name) == 4):
            return ordered_name[1] + " " + ordered_name[0]

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


def save_image(filename, image_url):
    save_image_path = "/images/"
    if path.exists(f'{save_image_path}{filename}'):
        return
    # Set up the image URL and filename
    # Open the url image, set stream to True, this will return the stream content.
    r = requests.get(image_url, stream=True)

    # Check if the image was retrieved successfully
    if r.status_code == 200:
        # Set decode_content value to True, otherwise the downloaded image file's size will be zero.
        r.raw.decode_content = True

        # Open a local file with wb ( write binary ) permission.
        with open(f'{save_image_path}{filename}', 'wb') as f:
            shutil.copyfileobj(r.raw, f)
    else:
        print('Image Couldn\'t be retreived')


def get_integer(string):
    return re.findall(r'\d+', string)
