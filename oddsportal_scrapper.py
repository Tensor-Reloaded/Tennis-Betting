import os.path
import sys
import datetime
import os.path
import re
import time

import pandas as pd
import requests
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait # available since 2.4.0
from selenium.webdriver.support import expected_conditions as EC # available since 2.26.0

import argparse

parser = argparse.ArgumentParser(description='OddsPortal scrapping')
parser.add_argument('--T_ID_START', default=0, type=int, help='ID of tournament to start scrapping')
parser.add_argument('--T_ID_END', default=3000, type=int, help='ID of tournament to end scrapping')
parser.add_argument('--save_interval', default=1, type=int, help='number of tournaments to save in one file')
parser.add_argument('--user', default='simi2525', type=str, help='user of odds portal')
parser.add_argument('--password', default='u7YZbkpPsyGg3pE', type=str, help='pass of odds portal')
parser.add_argument('--headless', action='store_false', help='headless')
parser.add_argument('--driver_exec_path', default=r"C:\Users\dell\Downloads\chromedriver_win32\chromedriver.exe", type=str, help='')


args = parser.parse_args()
"""
UPDATE THESE
"""
username = args.user
password = args.password
chrome_executable_path = args.driver_exec_path

base_url = "https://www.oddsportal.com"
start_url = "https://www.oddsportal.com/tennis/results/"
headers = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Mobile Safari/537.36"
}

options = Options()

if args.headless:
    options.add_argument("--headless")  # Runs Chrome in headless mode.
    options.add_argument('--no-sandbox')  # Bypass OS security model
    options.add_argument('--disable-gpu')  # applicable to windows os only
    options.add_argument('start-maximized')  #
    options.add_argument('disable-infobars')
    options.add_argument("--disable-extensions")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.headless = True

def login(username, password, c):
    c.get("https://www.oddsportal.com/login/")
    username_box = c.find_element_by_name("login-username")
    password_box = c.find_element_by_name("login-password")
    username_box.send_keys(username)
    password_box.send_keys(password)
    username_box.send_keys(Keys.ENTER)

def wait_for_element(c,element_selector):
    try:
        element = WebDriverWait(c, 15, poll_frequency=0.1).until(EC.element_located_to_be_selected((By.CSS_SELECTOR, element_selector)))
    finally:
        return


with requests.get(start_url, headers=headers) as r:
    links = re.findall(b'foo="f"\s*href="([^"]+)', r.content)
links = list(map(lambda x: x.decode(), links))

c = Chrome(executable_path=chrome_executable_path, options=options)
save_interval = args.save_interval

T_START_INDEX = min(max(0, args.T_ID_START), len(links))
T_END_INDEX = max(T_START_INDEX, min(len(links), args.T_ID_END))

matches_filename = "data/oddsportal/matches_{}-{}.csv".format(T_START_INDEX, T_END_INDEX)
matches_fd = open(matches_filename, "a+")

df_matches = pd.DataFrame(columns=["match_id", "country", "surface", "match_time", "players", "score", "sets", "odds",
                                   "year", "doubles", "prize_money", "sex",
                                   ])
df_matches.set_index('match_id', inplace=True)

for index, link in enumerate(links[T_START_INDEX:T_END_INDEX]):
    full_link = base_url + link
    link = link.lstrip('/').replace('tennis/', '')
    sep_index = link.find('/')
    if sep_index < 0:
        continue  # not found

    country = link[:sep_index]

    c.get(full_link)
    if "Page not found" in c.title:
        continue
    tournament_name = c.find_element_by_xpath('//h1').get_attribute('textContent')
    surface = re.search('\(\s*([a-z]+)\s*\)', tournament_name)
    sex = "men"
    if "women" in tournament_name.lower() or "wta" in tournament_name.lower():
        sex = "women"
        # We only want ATP
        continue
    elif "mixed" in tournament_name.lower() or "mix" in tournament_name.lower():
        sex = "mixed"
        # We only want ATP
        continue

    doubles = "doubles" in tournament_name.lower()
    if doubles:
        continue

    if surface:
        surface = surface.group(1)
        tournament_name = tournament_name.split(surface)[0].replace("(", "").strip()
    else:
        surface = "*"
        tournament_name = tournament_name.replace("Results & Historical Odds", "").strip()
        print("No surface type found in : ", full_link)

    wait_for_element(c,"#col-content > div.main-menu2.main-menu-gray > ul.main-filter > li > span > strong > a")

    tournmanet_year_links = c.find_element_by_css_selector(
        "#col-content > div.main-menu2.main-menu-gray > ul.main-filter").find_elements_by_css_selector(
        "li > span > strong > a")
    tournmanet_year_links = [e.get_attribute("href") for e in tournmanet_year_links]

    print("Tournament ID", index + T_START_INDEX)
    print("Tournaments remaining", T_END_INDEX - T_START_INDEX - index)

    for year_index, tournmanet_year_link in enumerate(tournmanet_year_links):
        c.get(tournmanet_year_link)

        tournament_year = c.find_element_by_css_selector(
            "#col-content > div.main-menu2.main-menu-gray > ul.main-filter > li > span.active").get_attribute(
            "textContent").strip()

        try:
            prize_money = c.find_element_by_css_selector("#col-content > div.prizemoney").get_attribute(
                "textContent").replace("Prize money: ", "").strip()
        except:
            prize_money = "$0"

        tournament_id = tournament_name + " - " + tournament_year

        table = c.find_element_by_id('tournamentTable')
        table = table.find_element_by_xpath('.//tbody')

        match_links = []
        for child in table.find_elements_by_xpath('.//tr'):
            if child.get_attribute('class') == "dark center":
                pass
            elif "nob-border" in child.get_attribute('class'):
                pass
            elif 'deactivate' in child.get_attribute('class'):
                match_links.append(child.find_element_by_css_selector('td > a').get_attribute("href"))


        print("Tournament year ID", year_index)
        print("Tournament years remaining", len(tournmanet_year_links) - year_index)
        print("Number of matches this year:",len(match_links))

        for match_idx, match_link in enumerate(match_links):
            print("Match ID:", match_idx,", remaining:", len(match_links) - match_idx, end='\r')
            sys.stdout.flush()
            match_time = players = final_score = info_val = ""
            odds = list()

            c.get(match_link)

            wait_for_element(c,"#col-content > h1")

            players = c.find_element_by_css_selector("#col-content > h1").get_attribute("textContent")
            players = re.sub('<[^>]+>', '', players).split('-')
            
            wait_for_element(c,"#col-content > p.date.datet")

            match_time = c.find_element_by_css_selector("#col-content > p.date.datet").get_attribute(
                "textContent")
            match_time = datetime.datetime.strptime(match_time.replace("  ", " ").replace("Today",
                                                                                          datetime.datetime.today().strftime(
                                                                                              '%A')).replace(
                "Yesterday", (datetime.datetime.today() - datetime.timedelta(days=1)).strftime('%A')),
                                                    '%A, %d %b %Y, %H:%M')

            result = c.find_element_by_css_selector("#event-status > p").get_attribute("textContent")
            if "Final result" not in result:
                continue
            result = result.replace("Final result", "").strip()
            result = result.split(" ", 1)
            score = result[0].strip()
            if len(result) == 2:
                sets = result[1][1:-1].split(", ")
            else:
                sets = []
            
            wait_for_element(c,"#bettype-tabs > ul > li.first.active")
            if c.find_element_by_css_selector("#bettype-tabs > ul > li.first.active").get_attribute(
                    "textContent") not in ["Home/Away"]:
                continue
            
            wait_for_element(c,"#odds-data-table > div.table-container > table.table-main.detail-odds.sortable")
            odds_table = c.find_element_by_css_selector("#odds-data-table > div.table-container > table.table-main.detail-odds.sortable")

            try:
                show_more_exists = odds_table.find_element_by_css_selector("tfoot > tr.odd > td > a")
            except:
                show_more_exists = False

            if show_more_exists != False and "Click to show " in show_more_exists.get_attribute(
                    "textContent") and "Click to show 0 more bookmakers!" not in show_more_exists.get_attribute(
                    "textContent"):
                show_more_exists.click()
            
            if "Log in to display the odds!" in odds_table.find_element_by_css_selector("tfoot").get_attribute(
                    "textContent"):
                print("Not loged in")
                login(username, password, c)
                c.get(match_link)
                wait_for_element(c,"#odds-data-table > div.table-container > table.table-main.detail-odds.sortable")
                odds_table = c.find_element_by_css_selector("#odds-data-table > div.table-container > table.table-main.detail-odds.sortable")

            odds_body = odds_table.find_element_by_css_selector("tbody")

            odds = {}
            for odd in odds_body.find_elements_by_css_selector("tr.lo"):
                columns = odd.find_elements_by_css_selector("td")
                if len(columns) < 3:
                    continue
                bookie = columns[0].get_attribute("textContent").strip()
                rates = [columns[1].get_attribute("textContent").strip(),
                         columns[2].get_attribute("textContent").strip()]
                odds[bookie] = rates
            matches_row = [country, surface, str(match_time), players, score, sets, odds, int(tournament_year), doubles, prize_money, sex]
            df_matches.loc[tournament_id + ": " + "-".join(players)] = matches_row
    print("\n")
    if (index + 1) % save_interval == 0 or index + 1 == T_END_INDEX:
        df_matches.to_csv(matches_fd, header=False)
        df_matches = pd.DataFrame(
            columns=["match_id", "country", "surface", "match_time", "players", "score", "sets", "odds",
                                   "year", "doubles", "prize_money", "sex",
                                   ])
        df_matches.set_index('match_id', inplace=True)

        matches_fd.flush()
        os.fsync(matches_fd.fileno())

c.close()
