from datetime import datetime, timedelta, timezone
import os
import traceback

import scrapy
import pandas as pd
import numpy as np
from scrapy_splash import SplashRequest


class MatchInfo(scrapy.Item):
    id = scrapy.Field()
    timestamp = scrapy.Field()
    category = scrapy.Field()
    title = scrapy.Field()
    surface = scrapy.Field()
    player1_name = scrapy.Field()
    player1_odds = scrapy.Field()
    player2_name = scrapy.Field()
    player2_odds = scrapy.Field()
    score = scrapy.Field()
    winner = scrapy.Field()


class OddsHistoryExplorer(scrapy.Spider):
    name = "odds_history"
    HOME_PAGE = "https://www.oddsportal.com/tennis/results/"
    jst = timezone(timedelta(hours=9), 'JST')
    now = datetime.now(jst) - timedelta(days=1)
    EXCLUDE_WORDS = ["Challenger", "Doubles",
                     "ITF", "Exhibition", "Cup", "Olympic"]
    custom_settings = {
        "SPLASH_URL": os.environ.get("SPLASH_URL"),
        "DOWNLOADER_MIDDLEWARES": {
            'scrapy_splash.SplashCookiesMiddleware': 723,
            'scrapy_splash.SplashMiddleware': 725,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        },
        "SPIDER_MIDDLEWARES": {
            'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,
        },
        "ITEM_PIPELINES": {
            'tennis_explorer.pipelines.OddsPortalPipeline': 300,
        },
        "HTTPCACHE_ENABLED": True,
        "HTTPCACHE_EXPIRATION_SECS": 60 * 60 * 3,
        "HTTPCACHE_DIR": 'httpcache',
        "HTTPCACHE_IGNORE_HTTP_CODES": [],
        "HTTPCACHE_STORAGE": 'scrapy.extensions.httpcache.FilesystemCacheStorage',
    }
    YEAR_PARSE_TARGET = os.environ.get("YEAR_PARSE_TARGET")
    GET_ONLY_LATEST = os.environ.get("GET_ONLY_LATEST")

    def start_requests(self):
        yield scrapy.Request(url=self.HOME_PAGE, callback=self.parse)

    def parse(self, response):
        table = response.css("table.table-main.sport")

        for td in table.css('td'):
            title = td.css("a::text").get()
            if not title:
                continue
            if any([w in title for w in self.EXCLUDE_WORDS]):
                continue
            href = td.css("a::attr('href')").get()
            yield SplashRequest(url=response.urljoin(href), callback=self.parse_detail, meta={'dont_cache': False}, args={
                'wait': 0.1,
            },)

    def parse_detail(self, response):
        pagination = len(response.css("#pagination a"))
        current_year = response.css(
            "#col-content > div.main-menu2.main-menu-gray > ul > li:nth-child(1) > span > strong > a::text").get()
        if self.GET_ONLY_LATEST and current_year != str(self.now.year):
            return

        for i in range(1, pagination - 2):
            yield SplashRequest(url=f"{response.url}/#/page/{i}/", callback=self.parse_match, meta={'dont_cache': False}, args={
                'wait': 0.1,
            },)
        year_list = response.css(
            "#col-content > div.main-menu2.main-menu-gray > ul > li > span > strong > a::attr('href')")

        if not self.GET_ONLY_LATEST:
            for year in year_list:
                yield SplashRequest(url=response.urljoin(year.get()), callback=self.parse_detail, args={
                    'wait': 0.1,
                },)

    def parse_match(self, response):
        h1 = response.css("h1::text").get()
        title = h1.split(" (")[0]
        surface = self.get_surface(h1)
        table = response.css("#tournamentTable > tbody")
        date = None
        for tr in table.css("tr"):
            try:
                item = MatchInfo()
                if new_date := tr.css("span.datet::text").get():
                    if "Today" in new_date:
                        continue
                    date = new_date

                if not date:
                    continue

                if "deactivate" not in tr.get():
                    continue
                category = "WTA" if "WTA" in title else "ATP"
                time = tr.css("td.table-time::text").get()
                timestamp = " ".join([self.convert_date(date), time])
                names = "".join(tr.css("td.name  ::text").getall())
                player1_name = self.name_format(names.split(" - ")[0])
                player2_name = self.name_format(names.split(" - ")[1])
                score = tr.css("td.table-score::text").get()
                odds = tr.css("td.odds-nowrp")
                player1_odds = odds[0].css("a::text").get()
                player2_odds = odds[1].css("a::text").get()
                winner = None
                if "result-ok" in odds[0].get():
                    winner = 1
                if "result-ok" in odds[1].get():
                    winner = 2
                id = "-".join([timestamp.split(" ")[0], player1_name.split(".")[
                    0], player2_name.split(".")[0]])

                item["id"] = id
                item["timestamp"] = timestamp
                item["title"] = title
                item["category"] = category
                item["surface"] = surface
                item["player1_name"] = player1_name
                item["player1_odds"] = round(float(player1_odds), 2)
                item["player2_name"] = player2_name
                item["player2_odds"] = round(float(player2_odds), 2)
                item["score"] = score
                item["winner"] = int(winner)
                yield item

            except Exception:
                print(traceback.format_exc())
                continue

    def convert_date(self, date):
        months = {
            "Jan": "01",
            "Feb": "02",
            "Mar": "03",
            "Apr": "04",
            "May": "05",
            "Jun": "06",
            "Jul": "07",
            "Aug": "08",
            "Sep": "09",
            "Oct": "10",
            "Nov": "11",
            "Dec": "12",
        }
        try:
            d, m, y = date.split(" ")
            m = months[m]
            return "-".join([y, m, d])
        except Exception:
            print(traceback.format_exc())
            print(f"date: {date}")
            return

    def get_surface(self, text):
        if("clay" in text):
            return "clay"
        if("hard" in text):
            return "hard"
        if("grass" in text):
            return "grass"

    def name_format(self, name):
        return name.replace("\xa0", "").rstrip(".").replace(" ", ".")
