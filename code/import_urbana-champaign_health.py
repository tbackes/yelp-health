import pandas as pd
import numpy as np
import requests as requests
from bs4 import BeautifulSoup, UnicodeDammit
import StringIO
import logging
import time
import pickle
from sys import argv

## helper functions:
def setup_logger(logger_name, log_file, level=logging.INFO):
    l = logging.getLogger(logger_name)
    formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(message)s')
    fileHandler = logging.FileHandler(log_file, mode='w')
    fileHandler.setFormatter(formatter)

    l.setLevel(level)
    l.addHandler(fileHandler)

def save_to_pickle(data, fname):
    '''Save a dictionary (or other python data structure) at the given pickle file'''
    with open(fname, 'wb') as handle:
        pickle.dump(data, handle)

## Functions that directly pull results from urbana-champaign website:
def single_query(payload, s=None):
    '''
    Go to link and return response's html content

    INPUT:  paylaod: dict, query terms to append to link
            s:       requests session, (optional)
    OUTPUT: soup:    string, html content from response for this link
    '''
    link = 'http://champaign.il.gegov.com/_templates/90/Food_Establishment_Inspection/_report_full.cfm'
    if s is None:
        response = requests.get(link, params=payload)
    else:
        response = s.get(link, params=payload)
    if len(response.content) < 5000:
        return None
    return response.content

def access_inspection_report(page_no, s=None):
    '''
    Return html content from a given page

    INPUT:  page_no: int, inspectionID to try accessing
            s:       requests session, (optional)
    OUTPUT: content: string, html content of scraped page
    '''
    # convert results page to beautiful soup content:
    payload = {'inspectionID':page_no, 'domainID':90, 'publicSite':'yes'}
    content = single_query(payload, s)
    return content

## wrapper functions that try to access the urbana-champaign website
## they report if the connection failed and can be called again
## the ct argument allows you to specify a pause before trying again 
def get_single_inspection_page(pg, ct, s=None):
    '''
    Scrape information from a given page. If attempt fails, report to logger and wait ct seconds 
    (provides padding before potentially trying again)

    INPUT:  pg: int, inspectionID to try accessing
            ct: int, number of times this page has already been attempted
            s:  requests session, (optional)
    OUTPUT: content: string, html content of scraped page
            e:       string, exception if scraping page failed. None otherwise.
    '''
    logR = logging.getLogger('logR')
    try: 
        #logR.info('Accessing page: %d', pg)
        # Extract html of restaurant inspection report:
        return access_inspection_report(pg, s), None
    except Exception as e:
        logR.warning('[%02d] Failed to load: %d --> exception: %s', ct, pg, e)
        time.sleep(ct)
        return None, str(e)


## Functions that actually loop through a given subset of pages and store all results in a dataframe
def scrape_restaurant_data(pages, s=None, label=None):
    '''
    Scrape restaurant data from given set of pages

    INPUT:  pages: list, inspectionIDs to try accessing
            s:     requests session, (optional)
            label: string, (optional) label to add to log filename
    OUTPUT: R:     dict, all html content for inspections found in this range of pages
    '''
    setup_logger('logR', 'logs/urb/scrape_reports_%06d.log' % label, level=logging.INFO)
    logR = logging.getLogger('logR')
    #logging.basicConfig(filename='logs/scrape_restaurant_%s.log' % label, filemode='w', level=logging.INFO)
    
    ct_max = 10
    ct_error = 0
    R = {}
    if s is None:
        s = requests.Session()
    
    # Loop through each results page:
    for pg in pages:
        ct = 0
        e = ''
        
        # Try up to 10 times to load each page. 
        # Adds a progressively longer wait period (proportional to ct) for each retry
        while (type(e) == str) and (ct < ct_max):
            content, e = get_single_inspection_page(pg, ct, s)
            ct += 1
        if type(e) == str:
            logR.error('Failed to load after %d tries. Error: %s', ct_max, e)
            ct_error += 1
        elif content is not None:
            logR.info('Page is valid: %06d' % pg)
            R['%06d' % pg] = content
    if ct_error > 0:
        logR.error('Failed to load %d pages.', ct_error)
    return R

###############################
# MAIN
###############################
if __name__ == '__main__':
    if len(argv) == 1:
        file_R = '../data/urb/urbchamp_R'
    else:
        file_R = argv[1]

    step_size = 1000
    
    rest = raw_input("scrape restaurant info (y = scrape & write to file / n = read from file): ")
    if rest == 'y':
        start = raw_input("Start from page (1-250000): ")
        end = raw_input("Stop at page (1-250000 or all): ")
    
    if rest == 'y':
        s = requests.Session()
        if end == 'all':
            end = '250000'
        if start == end:
            R = scrape_restaurant_data([int(start)], s, int(start))
            print '\nFinished scraping restaurant data.'
            save_to_pickle(R, '%s_%06d.pkl' % (file_R, int(start)))
            print 'R[%06d, %06dd): %s' % (int(start), int(start), len(R))
        else: 
            for i in xrange(int(start), int(end), step_size):
                j = min(i + step_size, int(end)+1)
                R = scrape_restaurant_data(xrange(i, j), s, j-1)
                print '\nFinished scraping restaurant data.'
                save_to_pickle(R, '%s_%06d.pkl' % (file_R, j-1))
                print 'R[%06d, %06d): %s' % (i, j, len(R))



