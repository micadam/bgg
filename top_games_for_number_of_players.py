import os
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from time import sleep
from typing import List, Set, Tuple

import requests as r
from bs4 import BeautifulSoup

LIST_TEMPLATE = "https://boardgamegeek.com/browse/boardgame/page/{}"
GAME_API_TEMPLATE = "https://boardgamegeek.com/xmlapi2/thing?id={}&stats=1"
GAME_PAGE_TEMPLATE = "https://boardgamegeek.com/boardgame/{}"


def main():
    """A script for getting the best games for N players,
    according to boardgamegeek

    Params:
        NUM_PLAYERS: the desired number of players,
        NUM_PAGES: the number of BGG pages to fetch (each page is 100 games)
    """
    if len(sys.argv) != 3:
        print(f"Usage: {os.path.basename(__file__)} NUM_PLAYERS NUM_PAGES")
        exit(1)

    num_players, num_pages = map(int, sys.argv[1:])
    print("Rating\tRank\tName\tYear\tWeight\tURL")
    for page in range(1, num_pages + 1):
        games = get_page_of_games(page)
        for game in games:
            best_counts, recommended_counts, weight = \
                get_game_stats(game.bgg_id)
            rating = "BEST" if num_players in best_counts \
                else "RECOMMENDED" if num_players in recommended_counts \
                else None
            if rating:
                print(f"{rating}\t{game.bgg_rank}\t{game.name}"
                      f"\t{game.year}\t{weight:.2f}/5.00"
                      f"\t{GAME_PAGE_TEMPLATE.format(game.bgg_id)}")


def get_game_stats(bgg_id: str) -> Tuple[Set[int], Set[int], float]:
    """Returns the best/recommended player counts for a game,
    as well as its weight (complexity) rating

    Args:
        bgg_id (str): the BoardGameGeek ID of a board game

    Returns:
        Set[int]: best player counts
        Set[int]: recommended player counts
        float: weight
    """
    url = GAME_API_TEMPLATE.format(bgg_id)
    best_counts = set()
    recommended_counts = set()
    nums = None
    while not nums:
        xml = r.get(url).content
        tree = ET.ElementTree(ET.fromstring(xml))
        nums = tree.find(".//*[@name='suggested_numplayers']")
        average_weight_elem = tree.find(".//*averageweight")
        if not nums:
            if tree.find("message").text == "Rate limit exceeded.":
                sleep(1)
            else:
                print("Unexpected exception")
                print(ET.tostring(tree.getroot(),
                                  encoding='utf8', method='xml'))
                exit(1)
    average_weight = float(average_weight_elem.attrib["value"])
    for num_players in nums:
        count_str = num_players.attrib["numplayers"]
        if count_str[-1] == '+':
            count = 1234
        else:
            count = int(count_str)
        votes = {}
        for result in num_players:
            name = result.attrib['value']
            numvotes = int(result.attrib['numvotes'])
            votes[name] = numvotes
        if votes["Best"] == max(votes.values()):
            best_counts.add(count)
        elif votes["Recommended"] == max(votes.values()):
            recommended_counts.add(count)
    return best_counts, recommended_counts, average_weight


def get_page_of_games(num: int) -> List['Game']:
    """Returns the numth page of BGG top games.

    Args:
        num (int): the number of the page

    Returns:
        List[Game]: the resulting list of Games
    """
    html = r.get(LIST_TEMPLATE.format(num)).content
    bs = BeautifulSoup(html, features="lxml")
    # Skip the header row
    table_rows = bs.find("table").findAll("tr")[1:]
    return [Game(row) for row in table_rows]


@dataclass
class Game:
    bgg_rank: str
    name: str
    year: str
    bgg_id: str

    def __init__(self, row):
        self.bgg_rank = row.find("td", {"class": "collection_rank"}) \
            .getText().strip()
        self.name = row.find("a", {"class": "primary"}).getText().strip()
        self.year = row.find("span").getText()[1:-1]
        self.bgg_id = row.find("a", {"class": "primary"})['href'].split("/")[2]


if __name__ == "__main__":
    main()
