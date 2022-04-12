from datetime import datetime, timedelta, timezone
from os import path
import scrapy
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np


class OddsHistoryExplorer(scrapy.Spider):
    name = "odds_history"
    home_page = "https://www.oddsportal.com/tennis/results/"
    jst = timezone(timedelta(hours=9), 'JST')
    now = datetime.now(jst) - timedelta(days=1)
    EXCLUDE_WORDS = ["Challenger", "Doubles", "ITF", "Exhibition"]

    # Tour
    # name, surface, country, year, prize, point

    # Player
    # name, birthday,

    # Match
    # tour_id, timestamp, player1_id, player2_id, player1_odds, player2_odds, winner

    def parse(self, response):
        table = response.css("table.table-main.sport")
        for td in table.css('td'):
            name = td.css("a::text").get()
            href = td.css("a::attr('href')").get()
            print(name, href)

            # yield scrapy.Request(url=response.urljoin(href), callback=self.parse_detail)

    def parse_detail(self, response):
        pass



