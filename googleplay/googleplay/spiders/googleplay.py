# -*- coding: utf-8 -*-

from scrapy.spider import CrawlSpider, Rule
from elasticsearch import Elasticsearch
from scrapy.contrib.linkextractors import LinkExtractor
from ..items import GoogleplayItem
import logging
from datetime import datetime
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
import json


class GoogleSpider(CrawlSpider):
    # Crawling Start
    CrawlSpider.started_on = datetime.now()

    #on instancie l'objet Elasticsearch par défaut
    es = Elasticsearch("127.0.0.1")
    ES_Index = "googleplay"
    ES_Type = "root"

    name = "google"
    allowed_domains = ["play.google.com"]
    start_urls = [
        'https://play.google.com/store',
        'https://play.google.com/store/apps/category/GAME/collection/topselling_free',
        'https://play.google.com/store/apps/details?id=com.viber.voip'
    ]

    rules = [
        Rule(LinkExtractor(allow=("https://play\.google\.com/store/apps/details", )),
             callback='parse_app', follow=True),
    ] # Régle de la spider, le callback ava aller appeler la fonction parse_app

    # Init
    def __init__(self, local = None, *args, **kwargs):
        #run baby, run :)
        super(GoogleSpider, self).__init__(*args, **kwargs)
        # On Spider Closed
        dispatcher.connect(self.spider_closed, signals.spider_closed)

    """
    Ceci est la méthode principale pour parser les objets
    """
    def parse_app(self, response):
        # le dictionnaires des valeures authorisé est défini le fichier items.py
        item = {}
        item['url'] = response.url

        app_id = response.url.split('=')[-1]
        if app_id:
            item['app_id'] = app_id
        else:
            item['app_id'] = ''

        # utilsiation du XPATH pour extraire le données
        rate_count = response.xpath('//span[@class="rating-count"]/text()')
        if rate_count:
            rate_count = rate_count.extract()[0].strip().replace(',', '')
            item['rating_count'] = rate_count

        app_name_div = response.xpath('//div[@class="id-app-title"]/text()')
        if not app_name_div:
            logging.error(msg='not find the app name')
            return
        item['app_name'] = app_name_div.extract()[0].strip()

        mail_a = response.xpath(
            '//div[@class="content contains-text-link"]/a[2]/@href')
        if not mail_a:
            return

        mail_text = mail_a.extract()[0]
        if 'mailto:' in mail_text:
            mail_text = mail_text.replace('mailto:', '')
        item['mail'] = mail_text.strip()

        company_name_span = response.xpath('//span[@itemprop="name"]/text()')
        if not company_name_span:
            return

        company_name = company_name_span.extract()[0].strip()
        item['company_name'] = company_name

        download_count = response.xpath(
            '//div[@itemprop="numDownloads"]/text()')
        if download_count:
            item['download_count'] = download_count.extract()[0].strip()
        else:
            item['download_count'] = '0'

        #On insert la data dans Elasticsearch
        self.insertIntoES(item)
        yield item

    def spider_closed(self, reason):
            """
            Spider closed: specifique method
            :param reason:
            :return:
            """
            # parsing time
            work_time = datetime.now() - CrawlSpider.started_on
    """
    Fonction qui permet d'inserré des documents dans Elasticsearch
    """
    def insertIntoES(self, data):
        print "----------------------------------------------------"
        print "envoi des données dans Elasticsearch"
        print data
        print "----------------------------------------------------"
        self.es.index(index=self.ES_Index, doc_type=self.ES_Type, body=data)
