# -*- coding: utf-8 -*-
__author__ = 'Paul'

import re
import lxml.html as html
import urllib2
import urllib

from calibre import as_unicode
from calibre.utils.date import parse_only_date
from calibre.ebooks.metadata import check_isbn
from calibre.ebooks.metadata.book.base import Metadata
from calibre.ebooks.metadata.sources.base import Source


class LibRusEcMetadataSourcePlugin(Source):
    version = (0, 0, 1)
    author = 'Paul Poloskov'
    name = 'lib.rus.ec metadata lookup'
    description = 'Looks up form book information on lib.rus.ec. Focuses of series, genre and tag information. \n' \
                  'Requires `lxml` package.'

    capabilities = frozenset(('identify',))
    supported_platforms = ('windows', 'osx', 'linux')
    touched_fields = frozenset(['title', 'authors', 'identifier:lib.rus.ec', 'tags', 'series', 'series_index', 'languages'])
    cached_cover_url_is_reliable = False

    url_pattern = 'http://lib.rus.ec"'

    @classmethod
    def parse_response(cls, response, log):
        metadata_items = []
        tags = []
        series = u''
        title = u''
        translators = []
        series_index = 0
        authors = []

        resp = urllib2.urlopen(response)
        page = html.parse(resp)
        e = page.getroot().find_class('_ga1_on_').pop()
        e.find("noindex").drop_tree()

        for i in e.xpath('//ol/li/a/text()'):
            tags.append(unicode(i))

        for i in e.xpath(u"//div[@class='_ga1_on_']/br[position()=1]/preceding-sibling::a[contains(@href,'/a/')]/text()"):
            authors.append(unicode(i))

        for i in e.xpath(u"//div[@class='_ga1_on_']/br[position()=1]/preceding-sibling::a[preceding::text()[contains(.,'перевод:')]]/text()"):
            translators.append(unicode(i))

        for i in e.xpath("(//div[@class='_ga1_on_']/div[@id='z0']/following-sibling::text())[1]"):
            title += i

        for i in e.xpath("//div[@class='_ga1_on_']/h8"):
            series = i.text_content()
            series_index = re.findall('\d+', i.tail)[0]

        for i in e.xpath("./a[contains(@href,'/s/')]/text()"):
            tags.append(unicode(i))

        for i in e.xpath("//div[@class='genre']/a/@href"):
            tags.append(unicode(i.split('/')[-1]))

        log.info(u'Found %s/%s: %s' % (series, series_index, title))

        if tags and series in tags:
            tags.remove(series)

        if translators:
            for t in translators:
                if t in authors:
                    authors.remove(t)

        metadata_item = Metadata(title, authors)
        if tags:
            metadata_item.tags = tags
        if series != '':
            metadata_item.series = series
        if series_index is not 0:
            metadata_item.series_index = series_index
        metadata_items.append(metadata_item)

        log.info(series, metadata_item.series)
        if u'Игрушечный дом' == series:
            log.info('1')
        if u'Игрушечный дом' == metadata_item.series:
            log.info('2')
        if series == metadata_item.series:
            log.info('3')

        return metadata_items


    def is_customizable(self):
        return False


    def identify(self, log, result_queue, abort, title=None, authors=None, identifiers=None, timeout=30):
        log.debug(u'lib.rus.ec identification started ...')
        identifiers = identifiers or {}
        search_tokens = []

        print "a", authors
        if title:
            tit = ' '.join(self.get_title_tokens(title))
        if authors:
            aut = ' '.join(self.get_author_tokens(authors, only_first_author=True))

        url = 'http://lib.rus.ec/search/%s' % urllib.quote(tit.encode('utf8'))
        log.info(u'Searching for: %s' % url)
        response = urllib2.urlopen(url)

        res = ''
        if "/b/" in response.geturl():
            res = response.geturl()
        else:
            page = html.parse(response)
            e = page.getroot().get_element_by_id('main')
            e.make_links_absolute('http://lib.rus.ec', resolve_base_href=True)
            for i in e.xpath('//h1/following-sibling::*[text()=" - "]'):
                temp_boo = ''
                br = False
                for ii in i.xpath("./a[contains(@href,'/b/')]"):
                    if tit.lower() == unicode(ii.text_content()).lower():
                        temp_boo = ii.attrib.get('href')
                for ii in i.xpath("./a[contains(@href,'/a/')]/text()"):
                    print temp_boo
                    if temp_boo and aut.lower() == unicode(ii).lower():
                        br = True
                        break
                if br:
                    res = temp_boo
                    break

        #     log.exception('Failed to get data from `%s`: %s' % (url, e.message))
        #     return as_unicode(e)

        if abort.is_set():
            return

        metadata = self.parse_response(res, log=log)

        for result in metadata:
            log.debug(result.series)
            log.debug('We are processing %s' % result)
            self.clean_downloaded_metadata(result)
            # log.debug("processed")
            result_queue.put(result)


if __name__ == '__main__':
    # Tests
    # calibre-customize -b . && calibre-debug -e __init__.py

    from calibre.ebooks.metadata.sources.test import (test_identify_plugin, title_test, authors_test)

    test_identify_plugin(LibRusEcMetadataSourcePlugin.name, [
        (
            {
                'identifiers': {'isbn': '9785932861578'},
                'title': u'Идору',
                'authors': u'Уильям Гибсон'
            },
            [
                title_test(u'Идору', exact=True),
                authors_test([u'Уильям Гибсон'])
            ]
        ),
        # (
        #     {
        #         'title': u'справочник',
        #         'identifiers': {'isbn': '9785932861578'}
        #     },
        #     [
        #         title_test(u'Python. Подробный справочник', exact=True),
        #         authors_test([u'Дэвид Бизли'])
        #     ]
        # ),
        # (
        #     {
        #         'title': u'Opencv Computer Vision',
        #         'authors': u'Howse'
        #     },
        #     [
        #         title_test(u'Opencv Computer Vision with Python', exact=True),
        #         authors_test([u'Joseph Howse'])
        #     ]
        # ),
    ])