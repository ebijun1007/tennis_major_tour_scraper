# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


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
