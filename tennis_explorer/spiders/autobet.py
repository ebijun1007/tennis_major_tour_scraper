from datetime import datetime, timedelta, timezone
import os
import traceback

import scrapy
import pandas as pd
import numpy as np
from scrapy_splash import SplashRequest


class BetInfo(scrapy.Item):
    surface = scrapy.Field()
    player1_name = scrapy.Field()
    player2_name = scrapy.Field()


class AutobetExplorer(scrapy.Spider):
    name = "autobet"
    HOME_PAGE = "https://www.oddsportal.com/matches/tennis/"
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
            'tennis_explorer.pipelines.AutobetPipeline': 300,
        },
    }
    YEAR_PARSE_TARGET = os.environ.get("YEAR_PARSE_TARGET")
    GET_ONLY_LATEST = os.environ.get("GET_ONLY_LATEST")

    def start_requests(self):
        yield SplashRequest(url=self.HOME_PAGE, callback=self.parse, meta={'dont_cache': True}, args={
            'wait': 1,
        },)

    def parse(self, response):
        table = response.css("table.table-main")
        title = ""
        surface = ""

        for tr in table.css("tr"):
            title = tr.css("th > a:nth-child(3)::text").get() or title
            if not title:
                continue
            if any([w in title for w in self.EXCLUDE_WORDS]):
                continue

            try:
                if "deactivate" in tr.get():
                    continue
                surface = self.get_surface(title) or surface
                item = BetInfo()
                names = tr.css("td.name a:nth-child(2)::text").get()
                if not names:
                    continue
                player1_name = self.name_format(names.split(" - ")[0])
                player2_name = self.name_format(names.split(" - ")[1])

                item["surface"] = surface
                item["player1_name"] = player1_name
                item["player2_name"] = player2_name
                yield item

            except Exception:
                print(traceback.format_exc())
                continue

    def get_surface(self, text):
        if not text:
            return False
        if("clay" in text):
            return "clay"
        if("hard" in text):
            return "hard"
        if("grass" in text):
            return "grass"

    def name_format(self, name):
        return name.replace("\xa0", "")


def to_html(p, t):
    with open(p, mode='w') as f:
        f.write(t)
