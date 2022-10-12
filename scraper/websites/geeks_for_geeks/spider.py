import re
from asyncio import gather
from bs4 import BeautifulSoup

from scraper.logger import log
from scraper.session import HttpSession, Methods
from scraper.session.response import Response
from scraper.utils.regex import COMPLEXITY_REGEX

from scraper.websites.geeks_for_geeks.extraction_methods import (
    EXTRACTION_METHODS
)
from scraper.websites.geeks_for_geeks.settings import (
    HEADERS, ALGORITHMS_URL
)


def parse_algorithm_schema(algorithm_data: dict):
    pass


def parse_complexity(raw_complexity: str):
    if 'Time' and 'Auxiliary' in raw_complexity:
        time, space = (
            re.search(COMPLEXITY_REGEX, complexity)
            for complexity in raw_complexity.split('Auxiliary')
        )

        # TODO: Validar o match
        complexity = {
            'time': time.group(),
            'space': space.group()
        }
    else:
        complexity = {
            'time': re.search(COMPLEXITY_REGEX, raw_complexity).group()
        }

    return complexity


def filter_algorithms_urls(alorithms_urls: list):
    return list(
        filter(
            lambda href: ('geeksquiz' not in href),
            alorithms_urls
        )
    )


def extract_name(soup):
    name = soup.find(
        'div', {'class': 'article-title'}
    )

    if name:
        return name.findNext().text
    else:
        return ''


def extract_complexity(soup):
    for method in EXTRACTION_METHODS:
        raw_complexity = method(soup)
        if raw_complexity:
            return parse_complexity(raw_complexity)


def extract_algorithm_data(response: Response):
    soup = BeautifulSoup(response.content, 'html.parser')

    return {
        'name': extract_name(soup),
        'complexity': extract_complexity(soup)
    }


def extract_algorithms_urls(response: Response):
    soup = BeautifulSoup(response.content, 'html.parser')
    page_content = soup.find('div', {'class': 'page_content'})

    return list(
        filter(
            None,
            [
                a.attrs.get('href')
                for ol in page_content.find_all('ol')[1:]
                for a in ol.find_all('a')
            ]
        )
    )


async def follow_algorithms(session: HttpSession, algorithms_urls: list):
    return await gather(
        *[
            session.request(
                method=Methods.GET.value,
                url=url,
                callbacks=[extract_algorithm_data]
            )
            for url in algorithms_urls
        ]
    )


async def follow_algorithms_urls(session: HttpSession):
    return await session.request(
        method=Methods.GET.value,
        url=ALGORITHMS_URL,
        callbacks=[
            extract_algorithms_urls,
            filter_algorithms_urls
        ]
    )


async def run():
    session = HttpSession()
    session.default_headers = HEADERS

    log.info('Starting "Geeks for Geeks" algorithms extraction')
    algorithms_urls = await follow_algorithms_urls(session)
    algorithms_data = await follow_algorithms(session, algorithms_urls)
    algorithms_schema = [
        parse_algorithm_schema(algorithm_data)
        for algorithm_data in algorithms_data
    ]

    return algorithms_schema
