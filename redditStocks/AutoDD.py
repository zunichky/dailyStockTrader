#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" AutoDD: Automatically does the so called Due Diligence for you. """

#AutoDD - Automatically does the "due diligence" for you.
#Copyright (C) 2020  Fufu Fang, Steven Zhu

#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <https://www.gnu.org/licenses/>.

__author__ = "Fufu Fang kaito1410 Napo2k"
__copyright__ = "The GNU General Public License v3.0"

# Native Python imports
import os
import math
import sys
import re
import argparse
import logging

from collections import Counter
from datetime import datetime, timedelta

# Pip modules imports
from psaw import PushshiftAPI
from yahooquery import Ticker
from tabulate import tabulate

# dictionary of possible subreddits to search in with their respective column name
subreddit_dict = {'pennystocks' : 'pnystks',
                  'RobinHoodPennyStocks' : 'RHPnnyStck',
                  'Daytrading' : 'daytrade',
                  'StockMarket' : 'stkmrkt',
                  'stocks' : 'stocks',
                  'investing' : 'invstng',
                  'wallstreetbets' : 'WSB'}

# dictionary of ticker financial information to get from yahoo
financial_measures = {'currentPrice' : 'Price', 'recommendationKey': 'recommadtn'}

# dictionary of ticker summary information to get from yahoo
summary_measures = {'exchange': 'exchange', 'previousClose' : 'prvCls', 'open': 'open', 'volume': 'volume', 'averageVolume': 'avgvolume', 'averageVolume10days': 'avgvlmn10'}

# dictionairy of ticker key stats summary
key_stats_measures = {'floatShares': 'Float'}

# note: the following scoring system is tuned to calculate a "popularity" score
# feel free to make adjustments to suit your needs

# x base point of for a ticker that appears on a subreddit title or text body that fits the search criteria
base_points = 4

# x bonus points for each flair matching 'DD' or 'Catalyst' of for a ticker that appears on the subreddit
bonus_points = 2

# every x upvotes on the thread counts for 1 point (rounded down)
upvote_factor = 2

# rocket emoji
rocket = '🚀'

def get_submission(n, sub):

    """
    Returns a list of results for submission in past:
    1st list: current result from n hours ago until now
    2nd list: prev result from 2n hours ago until n hours ago
    m. for each subreddit in subreddit_dict, create a new results list from 2n hours ago until now
     """

    val = subreddit_dict.pop(sub, None)
    if val is None:
        print('invalid subreddit: ' + sub)
        quit()

    api = PushshiftAPI()

    mid_interval = datetime.today() - timedelta(hours=n)
    timestamp_mid = int(mid_interval.timestamp())
    timestamp_start = int((mid_interval - timedelta(hours=n)).timestamp())
    timestamp_end = int(datetime.today().timestamp())

    results = []
    # results from the last n hours
    results.append(api.search_submissions(after=timestamp_mid,
                                 before=timestamp_end,
                                 subreddit=sub,
                                 filter=['title', 'link_flair_text', 'selftext', 'score']))

    # results from the last 2n hours until n hours ago
    results.append(api.search_submissions(after=timestamp_start,
                                 before=timestamp_mid,
                                 subreddit=sub,
                                 filter=['title', 'link_flair_text', 'selftext', 'score']))

    # results for the other subreddits
    for key in subreddit_dict:
        results.append(api.search_submissions(after=timestamp_start,
                                    before=timestamp_end,
                                    subreddit=key,
                                    filter=['title', 'link_flair_text', 'selftext', 'score']))

    return results


def get_freq_list(gen):
    """
    Return the frequency list for the past n days

    :param int gen: The generator for subreddit submission
    :returns:
        - all_tbl - frequency table for all stock mentions
        - title_tbl - frequency table for stock mentions in titles
        - selftext_tbl - frequency table for all stock metninos in selftext
    """

    # Python regex pattern for stocks codes
    pattern = "[A-Z]{3,5}"

    # Dictionary containing the summaries
    all_dict = {}

    # Dictionary containing the rocket count
    rocket_dict = {}

    # looping over each thread
    for i in gen:

        # every ticker in the title will earn this base points
        increment = base_points

        # flair is worth bonus points
        if hasattr(i, 'link_flair_text'):
            if 'DD' in i.link_flair_text:
                increment += bonus_points
            elif 'Catalyst' in i.link_flair_text:
                increment += bonus_points
            elif 'technical analysis' in i.link_flair_text:
                increment += bonus_points

        # every 2 upvotes are worth 1 extra point
        if hasattr(i, 'score') and upvote_factor > 0:
            increment += math.ceil(i.score/upvote_factor)

        # search the title for the ticker/tickers
        if hasattr(i, 'title'):
            title = ' ' + i.title + ' '
            title_extracted = set(re.findall(pattern, title))

        # search the text body for the ticker/tickers
        if hasattr(i, 'selftext'):
            selftext = ' ' + i.selftext + ' '
            selftext_extracted = set(re.findall(pattern, selftext))

        rocket_tickers = selftext_extracted.union(title_extracted)

        for j in rocket_tickers:

            count_rocket = title.count(rocket) + selftext.count(rocket)
            if j in rocket_dict:
                rocket_dict[j] += count_rocket
            else:
                rocket_dict[j] = count_rocket

        # title_extracted is a set, duplicate tickers from the same title counted once only
        for k in title_extracted:

            if k in all_dict:
                all_dict[k] += increment
            else:
                all_dict[k] = increment

        # avoid counting additional point for the tickers found in the text body
        # only search the text body if ticker was not found in the title
        if len(title_extracted) > 0:
                continue

        for m in selftext_extracted:

            if m in all_dict:
                all_dict[m] += increment
            else:
                all_dict[m] = increment

    return all_dict.items(), rocket_dict

# this functions is similar to the above, but it's run on the
# results from other subreddits rather than r/pennystocks
# since there is no flair, rockets, and we have a list of tickers
# we are looking for already
def get_freq_dict(gen):
    """
    Return the frequency list for the past n days

    :param int gen: The generator for subreddit submission
    :returns:
        - all_tbl - frequency table for all stock mentions
        - title_tbl - frequency table for stock mentions in titles
        - selftext_tbl - frequency table for all stock metninos in selftext
    """

    # Python regex pattern for stocks codes
    pattern = "[A-Z]{3,5}"

    # Dictionary containing the summaries
    all_dict = {}

    # looping over each thread
    for i in gen:

        # every ticker in the title will earn this base points
        increment = base_points

        # every 2 upvotes are worth 1 extra point
        if hasattr(i, 'score') and upvote_factor > 0:
            increment += math.ceil(i.score/upvote_factor)

        # search the title for the ticker/tickers
        if hasattr(i, 'title'):
            title = ' ' + i.title + ' '
            title_extracted = set(re.findall(pattern, title))

            # title_extracted is a set, duplicate tickers from the same title counted once only
            for k in title_extracted:

                if k in all_dict:
                    all_dict[k] += increment
                else:
                    all_dict[k] = increment


        # avoid counting additional point for the ticker found in the text body
        if len(title_extracted) > 0:
            continue

        # search the text body for the ticker/tickers
        if hasattr(i, 'selftext'):
            selftext = ' ' + i.selftext + ' '
            selftext_extracted = set(re.findall(pattern, selftext))

            for m in selftext_extracted:

                if m in all_dict:
                    all_dict[m] += increment
                else:
                    all_dict[m] = increment

    return all_dict

def filter_tbl(tbl, min_val):
    """
    Filter a frequency table

    :param list tbl: the table to be filtered
    :param int min: the number of days in the past
    :returns: the filtered table
    """
    BANNED_WORDS = [
        'THE', 'FUCK', 'ING', 'CEO', 'USD', 'WSB', 'FDA', 'NEWS', 'FOR', 'YOU', 'AMTES', 'WILL', 'CDT', 'SUPPO', 'MERGE',
        'BUY', 'HIGH', 'ADS', 'FOMO', 'THIS', 'OTC', 'ELI', 'IMO', 'TLDR', 'SHIT', 'ETF', 'BOOM', 'THANK', 'MAYBE', 'AKA',
        'CBS', 'SEC', 'NOW', 'OVER', 'ROPE', 'MOON', 'SSR', 'HOLD', 'SELL', 'COVID', 'GROUP', 'MONDA', 'PPP', 'REIT', 'HOT', 'USA'
    ]

    tbl = [row for row in tbl if row[1][0] >= min_val or row[1][1] >= min_val]
    tbl = [row for row in tbl if row[0] not in BANNED_WORDS]
    return tbl


def combine_tbl(tbl_current, tbl_prev):
    """
    Combine two frequency table, one from the current time interval, and one from the past time interval
    :returns: the combined table
    """
    dict_result = {}

    for key, value in tbl_current:
        dict_result[key] = [value, value, 0, value]

    for key, value in tbl_prev:
        if key in dict_result.keys():
            dict_result[key][0] = dict_result[key][0] + value
            dict_result[key][2] = value
            dict_result[key][3] = dict_result[key][3] - value
        else:
            dict_result[key] = [value, 0, value, -value]

    return dict_result.items()


def additional_filter(results_tbl, filter_collection):

    filter_dict = get_freq_dict(filter_collection)

    for k, v in results_tbl:
        if k in filter_dict.keys():
            v.append(filter_dict[k])
        else:
            v.append(0)

    return results_tbl

def append_rocket_tbl(results_tbl, rockets_1, rockets_2):

    rockets = Counter(rockets_1) + Counter(rockets_2)

    for k, v in results_tbl:
        if k in rockets.keys():
            v.append(rockets[k])
        else:
            v.append(0)

    return results_tbl


def get_list_val(lst, index):
        try:
            return lst[index]
        except IndexError:
            return 0


def print_tbl(tbl, filename, allsub, yahoo):

    header = ["Code", "Total", "Recent", "Prev", "Change", "Rockets"]

    if allsub:
        header = header + list(subreddit_dict.values())

    if yahoo:
        header = header + list(summary_measures.values())
        header = header + list(financial_measures.values())
        header = header + list(key_stats_measures.values())

    tbl = [[k] + v for k, v in tbl]

    now = datetime.now()
    # dd/mm/YY H:M:S
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

    #print("date and time now = ", dt_string)
    #print(tabulate(tbl, headers=header))

    # save the file to the same dir as the AutoDD.py script
    completeName = os.path.join(sys.path[0], filename)

    #setup config file string
    configString = ""
    if yahoo:
        configString = '['
        count = 0
        for x in tbl:
            if (x[1] > 15 ):
                if (x[6] != "PNK" and x[6] != "YHD" ):
                    count = count + 1
                    configString += '"' + x[0] + '",'
                    if (count >= 20):
                        break
        #remove last comma
        configString = configString[:-1]
        configString += ']'


    # write to file
    with open(completeName, "a") as myfile:
        myfile.write("date and time now = ")
        myfile.write(dt_string)
        myfile.write('\n')
        myfile.write(tabulate(tbl, headers=header))
        myfile.write('\n\n')
        myfile.write('stocksToWatch=' + configString)

    #logs to console
    print("Wrote to file successfully: ")
    print(completeName)

def get_nested(data, *args):
    if args and data:
        element  = args[0]
        if element:
            if type(data) == str:
                return 0
            value = data.get(element)
            return value if len(args) == 1 else get_nested(value, *args[1:])


def getTickerInfo(results_tbl):

    filtered_tbl = []

    for entry in results_tbl:
        ticker = Ticker(entry[0])
        if ticker is not None:
            valid = False
            for measure in summary_measures.keys():
                if (measure == 'exchange'):
                    result = get_nested(ticker.price, entry[0], measure)
                else:
                    result = get_nested(ticker.summary_detail, entry[0], measure)
                if result is not None:
                    entry[1].append(result)
                    if result != 0:
                        valid = True
                else:
                    entry[1].append(0)

            for measure in financial_measures.keys():
                result = get_nested(ticker.financial_data, entry[0], measure)
                if result is not None:
                    entry[1].append(result)
                    if result != 0:
                        valid = True
                else:
                    entry[1].append(0)
            
            x = ticker.price
##adding key stats module
            for measure in key_stats_measures.keys():
                result = get_nested(ticker.key_stats, entry[0], measure)
                if result is not None:
                    entry[1].append(result)
                    if result != 0:
                        valid = True
                else:
                    entry[1].append(0)

            if valid:
                filtered_tbl.append(entry)

    return filtered_tbl
