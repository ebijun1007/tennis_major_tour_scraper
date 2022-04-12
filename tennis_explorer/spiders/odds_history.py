from datetime import datetime, timedelta, timezone
from os import path
import scrapy
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np


class OddsHistoryExplorer(scrapy.Spider):
    name = "odds_history"
    HOME_PAGE = "https://www.oddsportal.com/tennis/results/"
    jst = timezone(timedelta(hours=9), 'JST')
    now = datetime.now(jst) - timedelta(days=1)
    EXCLUDE_WORDS = ["Challenger", "Doubles", "ITF", "Exhibition", "Cup", "Boys", "Girls"]

    # Tour
    # name, surface, country, year, prize, point

    # Player
    # name, birthday,

    # Match
    # tour_id, timestamp, player1_id, player2_id, player1_odds, player2_odds, winner

    def start_requests(self):
        yield scrapy.Request(url=self.HOME_PAGE, callback=self.parse)


    def parse(self, response):
        table = response.css("table.table-main.sport")
        for td in table.css('td'):
            name = td.css("a::text").get()
            if not name:
                continue
            if any(element in name for element in self.EXCLUDE_WORDS):
                continue
            href = td.css("a::attr('href')").get()
            print(name, response.urljoin(href))

            # yield scrapy.Request(url=response.urljoin(href), callback=self.parse_detail)

    def parse_detail(self, response):
        pass



