import pandas as pd
import numpy as np
import requests as requests
from bs4 import BeautifulSoup, UnicodeDammit
import StringIO
import logging
import time

#### U.S.: Pittsburgh, Charlotte, Urbana-Champaign, Phoenix, Las Vegas, Madison

## helper functions:
def setup_logger(logger_name, log_file, level=logging.INFO):
    l = logging.getLogger(logger_name)
    formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(message)s')
    fileHandler = logging.FileHandler(log_file, mode='w')
    fileHandler.setFormatter(formatter)
    #streamHandler = logging.StreamHandler()
    #streamHandler.setFormatter(formatter)

    l.setLevel(level)
    l.addHandler(fileHandler)
    #l.addHandler(streamHandler)  

def single_query(link, payload, s=None):
    '''
    Go to link and return BeautifulSoup content

    INPUT:  link:    string, link extension for subdirectory of maricopa.gov
            paylaod: dict, query terms to append to link
            s:       requests session, (optional)
    OUTPUT: soup:    BeautifulSoup, content at link
    '''
    if s is None:
        response = requests.get('http://www.maricopa.gov'+link, params=payload)
    else:
        response = s.get('http://www.maricopa.gov'+link, params=payload)
    return BeautifulSoup(response.content, from_encoding='UTF-8')

## Functions that directly pull results from PHX website:
def access_results_page(page_no, s=None):
    '''
    Go to results page and scrape restaurant information.

    INPUT:  page_no: int, search results page to scrape
            s:       requests session (optional)
    OUTPUT: permit_links: list, links to each restaurant on this results page
            rows:         list, restaurant-level summary information
                                [permit_id, business name, address, cutting edge participant]
    '''
    # convert results page to beautiful soup content:
    link = '/EnvSvc/OnlineApplication/EnvironmentalHealth/BusinessSearchResults'
    payload = {'page':str(page_no)}
    soup = single_query(link, payload, s)

    # Get list of all rows entries (restaurants) on this page
    t = soup.findAll('div',attrs={'class':'col-xs-12 Row regularText'})

    # Extract table info for each restaurant
    # [permit_id, business name, address, cutting edge participant]
    rows = [[y.text for y in x.findAll('div')] for x in t]
    
    # Extract link to each restaurant's page
    permit_links = [[y['href'] for y in x.findAll('a')][0] for x in t]
    
    return permit_links, rows #permit_ids, names

def access_restaurant_page(restaurant_link, s=None):
    '''
    Go to link and scrape restaurant information.

    INPUT:  restaurant_link:    string, link to restaurant-level page
            s:                  requests session (optional)
    OUTPUT: inspection_links:   list, links to all available inspections
            inspection_summary: list, summary-level information available for each inspection
                                      [Date, purpose, grade, priority violation, cutting edge participant]
    '''
    # convert restaurant page to beautiful soup content:
    soup = single_query(restaurant_link, None, s)
    
    # Get list of all rows entries (inspections) on this page
    t = soup.findAll('div',attrs={'class':'col-xs-12 Row regularText'})
    
    # Extract link to each inspection's detailed report
    inspection_links = [[y['href'] for y in x.findAll('a')][0] for x in t]
    
    # Extract summary details for each report: 
    # [Date, purpose, grade, priority violation, cutting edge participant]
    inspection_summary = [[y.text for y in x.findAll('div')] for x in t]
    
    return inspection_links, inspection_summary

def access_inspection_page(inspection_link, s=None):
    '''
    Go to inspection-link and scrape results

    INPUT:  inspection_link:    string, link to inspection-level page
            s:                  requests session (optional)
    OUTPUT: inspection_summary: list, summary level details for inspection (date, outcome, etc)
                                      [grade, priority violation, cutting edge participant]
            violations:         list, violation-level details
                                      [violation id, violation description, violation comments, correct by]
            comments:           string, high-level comments about inspection
    '''
    # convert inspection page to beautiful soup content:
    soup = single_query(inspection_link, None, s)
    
    # Get list of all rows entries (inspections) on this page
    t = soup.findAll('div',attrs={'class':'col-xs-12 Row regularText'})
    
    rows = [[y.text for y in x.findAll('div')] for x in t]
    
    # Extract inspection summary info
    # [grade, priority violation, cutting edge participant]
    inspection_summary = rows[0]
    
    # Extract violation details: 
    # [violation id, violation description, violation comments, correct by]
    violations = rows[1:] if len(rows) > 1 else []
    
    # Extract inspection comments:
    comments = soup.findAll('p',attrs={'class':'col-xs-12 Row regularText'})[0].text
    
    return inspection_summary, violations, comments

## Helper functions that try to access the PHX website
## they report if the connection failed and can be called again
## the ct argument allows you to specify a pause before trying again 
def get_single_result_page(pg, ct, s=None):
    '''
    Go to results page and scrape restaurant information. If this fails, write exception to log.
    (and sleep ct seconds, to allow time before additional attempts to access this link)

    INPUT:  pg: int, search results page to access
            ct: int, number of times this page has already been tried
            s:  requests session (optional)
    OUTPUT: df: pandas dataframe, restaurant-level information for all restaurants on this page
            e:  exception message (only if there was an error accessing page, otherwise None)
    '''
    logR = logging.getLogger('logR')
    try: 
        logR.info('Accessing page: %d', pg)
        # Extract link to inspections and general restaurant info:
        permit_links, rest_info = access_results_page(pg, s)
        rest_info = np.array(rest_info)
        
        return pd.DataFrame.from_dict({'link': permit_links,
                                       'permit_id': rest_info[:,0], 
                                       'name': rest_info[:,1],
                                       'address': rest_info[:,2],
                                       'cutting_edge': rest_info[:,3]}), None 
    except Exception as e:
        logR.warning('[%02d] Failed to load: %d --> exception: %s', ct, pg, e)
        time.sleep(ct)
        return None, str(e)

def get_single_restaurant(link, ct, s=None):
    '''
    Go to link and scrape restaurant information. If this fails, write exception to log.
    (and sleep ct seconds, to allow time before additional attempts to access this link)

    INPUT:  link:  string, link to restaurant-level page
            ct:    int, number of times this page has already been tried
            s:     requests session (optional)
    OUTPUT: i_links:   list, links to all available inspections
            i_summary: list, summary-level information available for each inspection
            e:         exception message (only if there was an error accessing page, otherwise None)
    '''
    logI = logging.getLogger('logI')
    try: 
        logI.info('Accessing link: %s', link)
        # Extract inspection info:
        i_links, i_summary = access_restaurant_page(link, s)
        i_summary = np.array(i_summary)
        
        return i_links, i_summary, None 
    except Exception as e:
        logI.warning('[%02d] Failed to load: %s --> exception: %s', ct, link, e)
        time.sleep(ct)
        return None, None, str(e)

def get_single_inspection(link, ct, s=None):
    '''
    Go to link and scrape inspection information. If this fails, write exception to log.
    (and sleep ct seconds, to allow time before additional attempts to access this link)

    INPUT:  link:  string, link to inspection-level page
            ct:    int, number of times this page has already been tried
            s:     requests session (optional)
    OUTPUT: inspection_summary: list, summary level details for inspection (date, outcome, etc)
            violations:         list, violation-level details
            comments:           string, high-level comments about inspection
            e:                  exception message (only if there was an error accessing page, otherwise None)
    '''
    logI = logging.getLogger('logI')
    try: 
        logI.debug('           %s', link)
        # Extract inspection info:
        inspection_summary, violations, comments = access_inspection_page(link, s)
        violations = np.array(violations)

        return inspection_summary, violations, comments, None
    except Exception as e:
        logI.warning('[%02d] Failed to load: %s --> exception: %s', ct, link, e)
        time.sleep(ct)
        return None, None, None, str(e)

## Functions that actually loop through a given subset of pages and store all results in a dataframe
def scrape_restaurant_data(pages, s=None, label=None):
    '''
    Given a list of pages, scrape all restaurant-level information from those results pages.

    INPUT: pages:    list, list of pages to scrape
           s:        requests session (optional)
           label:    string, (optional) label to add to log filename
    OUTPUT: R:       pandas dataframe, all restaurant level information scraped from given results pages.
    '''
    setup_logger('logR', 'logs/scrape_restaurant_%s.log' % label, level=logging.INFO)
    logR = logging.getLogger('logR')
    #logging.basicConfig(filename='logs/scrape_restaurant_%s.log' % label, filemode='w', level=logging.INFO)
    
    ct_max = 10
    ct_error = 0
    R = pd.DataFrame(columns=['permit_id', 'link', 'name', 'address', 'cutting_edge'])
    if s is None:
        s = requests.Session()
    
    # Loop through each results page:
    for pg in pages:
        ct = 0
        e = ''
        
        # Try up to 10 times to load each page. 
        # Adds a progressively longer wait period (proportional to ct) for each retry
        while (type(e) == str) and (ct < ct_max):
            R_single, e = get_single_result_page(pg, ct, s)
            ct += 1
        if type(e) == str:
            logR.error('Failed to load after %d tries. Error: %s', ct_max, e)
            ct_error += 1
        else:
            R = pd.concat([R, R_single], ignore_index=True)
    if ct_error > 0:
        logR.error('Failed to load %d pages.', ct_error)
    return R

def scrape_inspection_data(R, s=None, label=None):
    '''
    Given a dataframe of restaurant level information, use the links it contains to scrape 
    all of the inspection- and violation-level information for those restaurants. Return each as
    seperate dataframes.

    INPUT:  R:     pandas dataframe, restaurant level information
            s:     request Session, (optional)
            label: string, (optional) label to add to log filename
    OUTPUT: I:     pandas dataframe, inspection level information
            V:     pandas dataframe, violation level information
    '''
    setup_logger('logI', 'logs/scrape_inspection_%05d.log' % label, level=logging.INFO)
    logI = logging.getLogger('logI')
    #logging.basicConfig(filename='logs/scrape_inspection_%04d.log' % label, filemode='w', level=logging.INFO)
    
    ct_max = 10
    ct_error_link = 0
    ct_error_report = 0
    ct_error_reading = 0
    
    I = pd.DataFrame(columns=['inspec_id', 'permit_id', 'link', 'date', 'grade', 'n_priority', 'cutting_edge', 'comments'])
    V = pd.DataFrame(columns=['inspec_id', 'permit_id', 'code', 'description', 'comments', 'correct_by'])
    if s is None:
        s = requests.Session()
    
    # Loop through each restaurant page:
    for link in R.link:
        i_comments = []

        ct = 0
        e = ''
        
        # Try up to 10 times to load each page.
        # Adds a progressively longer wait period (proportional to ct) for each retry
        while (type(e) == str) and (ct < ct_max):
            i_links, i_summary, e = get_single_restaurant(link, ct, s)
            ct += 1
            
            # [Date, purpose, grade, priority violation, cutting edge participant]
            info = np.array(i_summary)
        if type(e) == str:
            logI.error('Failed to load after %d tries. Error: %s', ct_max, e)
            ct_error_link += 1
        else:
            # Extract id's from url
            split_link = map(lambda x: x.replace('&','=').split('='), i_links)
            inspec_id = [x[3] for x in split_link]
            permit_id = [x[1] for x in split_link]
            
            # Loop through each individual inspection report
            for i in xrange(len(i_links)):
                ct_v = 0
                e = ''
                
                # Try up to 10 times to load each inspection report.
                # Adds a progressively longer wait period (proportional to ct_v) for each retry
                while (type(e) == str) and (ct_v < ct_max):
                    _, violations, comments, e = get_single_inspection(i_links[i], ct_v, s)
                    ct_v += 1
                
                if e == 'list index out of range':
                    logI.warning('Unable to parse after %d tries. Error: %s', ct_max, e)
                    i_comments.append('')
                elif type(e) == str:
                    logI.error('Failed to load after %d tries. Error: %s', ct_max, e)
                    ct_error_report += 1
                else:
                    i_comments.append(comments)
                    
                    # some inspection reports do not include any violations.
                    if violations.size > 0:
                        # Append all violation information to the violation dataframe
                        V = pd.concat([V, pd.DataFrame.from_dict({'inspec_id': inspec_id[i],
                                                                  'permit_id': permit_id[i],
                                                                  'code': violations[:,0],
                                                                  'description': violations[:,1],
                                                                  'comments': violations[:,2],
                                                                  'correct_by': violations[:,3]})])

            # Append all inspection information to the inspection data frame:
            try:
                I = pd.concat([I, pd.DataFrame.from_dict({'link': i_links,
                                                      'inspec_id': inspec_id,
                                                      'permit_id': permit_id,
                                                      'date': i_summary[:,0],
                                                      'purpose': i_summary[:,1],
                                                      'grade': i_summary[:,2],
                                                      'n_priority': i_summary[:,3],
                                                      'cutting_edge': i_summary[:,4],
                                                      'comments': i_comments})], ignore_index=True)
            except Exception as e:
                logI.error('Failed to load row. %s. Exception: %s', link, e)
                ct_error_reading += 1
    if ct_error_link > 0:
        logI.error('Failed to load %d restaurant pages.', ct_error_link)
    if ct_error_report > 0:
        logI.error('Failed to load %d inspection report pages.', ct_error_report)
    if ct_error_reading > 0:
        logI.error('Failed to load %d inspection report pages.', ct_error_reading)
    return I, V

