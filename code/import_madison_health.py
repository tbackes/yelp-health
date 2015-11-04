import pandas as pd
from selenium import webdriver
from bs4 import BeautifulSoup
import re
import pickle
from sys import argv
from unidecode import unidecode

def clean_string(text):
    return unidecode(text.encode('utf8').decode('utf8'))

def search_restaurants(browser, search_term, rest_seen=set(), get_inspection=True):
    '''
    Grab all restaurant/inspection information for a given search term. Any restaurant's whose id
    is contained in rest_seen will be ignored.

    INPUT:  browser:     Selenium browser
            search_term: string, search term that should be used
            rest_seen:   set, [default = set()] all id's that should be ignored 
                              (used to avoid ids already captured by previous overlapping search(es))
            get_inspection: boolean, [default = True] whether to scrape inspection/violation level information
                            if false, only returns list of restaurants from search results page
    OUTPUT: rest_dict:   dict, all restaurant information (inspections/violations included as nested dict)
                         key = id that can be used to access restaurant's page
                         e.g. {''MainContent_73556-81811':
                                 {
                                    'address': '317 S DIVISION ST\nSTOUGHTON, WI 53589',
                                    'name': 'Reverend Jims Saloon',
                                    'type': 'Primarily Restaurant',
                                    'inspections':
                                    {
                                       'MainContent_2322899': 
                                          {
                                             'date': '11/13/2012',
                                             'result': 'No Reinspection Required',
                                             'type': 'Routine Inspection',
                                             'violations': 
                                             {
                                                '46p - SANITIZER TEST KIT': 
                                                   ['Observation: A test kit for the sanitizer quaternary ammonia is not available or being used.',
                                                    'Corrective action: Provide a test kit or other device for measuring the concentration of sanitizing solutions.',
                                                    'Code reference: WFC 4-302.14',
                                                    'Good Retail Practice',
                                                    'Action taken notes:',
                                                    'Repeat Violation: No',
                                                    'Corrected Onsite: No'],
                                                '49p - PLUMBING GOOD REPAIR ': 
                                                   ['Observation: Repair the water leak in basement that is dripping from a waste pipe.',
                                                    'Corrective action: Repair the plumbing system to conform to the State Uniform Plumbing Code.',
                                                    'Code reference: WFC 5-205.15',
                                                    'Good Retail Practice',
                                                    'Action taken notes:',
                                                    'Repeat Violation: No',
                                                    'Corrected Onsite: No'],
                                                ... # Any additional violations
                                             }
                                          },
                                        ... # Any additional inspections
                                    }
                                 }
                                ... # Any additional restaurants
                              }
    '''
    #navigate to main page
    url = 'https://elam.cityofmadison.com/HealthInspections/Default.aspx?AcceptsCookies=1'
    browser.get(url)
    
    search_content = browser.find_element_by_id('MainContent_txtSearchEstablishment')
    search_content.clear()
    search_content.send_keys(search_term)

    # press search button
    browser.find_element_by_id('MainContent_btnSearch').click()

    # save results as beautiful soup
    soup = BeautifulSoup(browser.page_source)
    
    # scrape restaurant info
    print '\nScraping Restaurant Table: %s' % search_term
    rest_dict = scrape_restaurants(soup, rest_seen)
    
    if get_inspection:
        # get all inspection information for new restaurants:
        print 'Scraping Inspection Data'
        rest_dict = get_inspections(browser, rest_dict)
    
    return rest_dict

def scrape_restaurants(soup, seen):
    '''
    Scrape all information from BeautifulSoup-encoded content of an search-results page.

    INPUT:  soup:      BeautifulSoup, content of page describing all restaurants matching search term
            seen:      set, all restaurant id's that have already been captured by previously used 
                            search terms. These will not be scraped or added to the final output dict.
    OUTPUT: rest_dict: dict, All restaurant information.
    '''
    # Get ESTABLISHMENT table
    t = soup.findAll('table', attrs={'id':'MainContent_tblEstablishment'})[0]
    
    # Save all restaurant-level info from establishment table:
    rest = t.findAll('td')
    rest_dict = {}
    for i in xrange(0, len(rest), 3):
        id_ = clean_string(rest[i].contents[0]['id'])
        # only continue if the id has never been seen before:
        if id_ not in seen:
            name = clean_string(rest[i].contents[0].contents[0])
            address = clean_string(rest[i+1].contents[0])
            type_ = clean_string(rest[i+2].contents[0])
            rest_dict[id_] = {'name':name, 'address':address, 'type':type_}
            
    return rest_dict

def get_inspections(browser, rest_dict):
    '''
    Wrapper that loops through all restaurants and tries to obtain inspection-level information.
    If a restaurant fails to load, prints an error message and then continues with next one.

    INPUT:  browser:   Selenium browser
            rest_dict: dict, all restaurants for a given search term. 
                       key = page id that can be used to access inspection-level 
    OUTPUT: rest_dict: dict, all restaurants for a given search term.
                       each restaurant now owns an inpsection dict populated with inspection-
                       and violation-level info

    NOTE: If an error is caught by the except group, the rest_dict entry for that key is not 
          populated with an insp_dict.
    '''
    # Loop through each unseen restaurant and get the inspection info
    print 'Number of new restaurants to scrape: %d' % len(rest_dict)
    for page in rest_dict.keys():
        try:
            rest_dict[page]['inspections'] = access_restaurant(browser, page)
        except Exception as e:
            print 'Failed to access inspection: %s (%s), Exception: %s' % (page, rest_dict[page]['name'], e)
            # make sure that the browser is returned to the search results page
            try:
                browser.find_element_by_id('MainContent_lnkBackToSearch').click()
            except:
                print 'On main page'
            
    return rest_dict

def access_restaurant(browser, this_rest):
    '''
    Go to page for a given restaurant, download inspection information and save in new dict.

    INPUT:  browser:   Selenium browser
            this_rest: string, id of restaurant link that should be accessed
    OUTPUT: insp_dict: dict, All inspection information. (Violations also included in nested dicts)
    '''
    # Access restaurant page:
    browser.find_element_by_id(this_rest).click()

    # save results as BeautifulSoup:
    soup = BeautifulSoup(browser.page_source)

    # Scrape inspection info if there are valid results:
    insp_dict = scrape_inspections(browser, soup)
      
    # return to search results
    browser.find_element_by_id('MainContent_lnkBackToSearch').click()
    return insp_dict

def scrape_inspections(browser, soup):
    '''
    Scrape all information from BeautifulSoup-encoded content of an inspections page.

    INPUT:  browser:   Selenium browser
            soup:      BeautifulSoup, content of page describing inspections for a restaurant
    OUTPUT: insp_dict_updated: dict, All inspection information. 
                               (Violations also included in nested dicts)
    '''
    if len(soup.findAll('label',attrs={'id':'MainContent_lblNoResults'})) > 0:
        return {}
    else:
        # Get INSPECTION table
        t = soup.findAll('table', attrs={'id':'MainContent_tblInspection'})[0]

        # Save inspection-level information from table:
        insp = t.findAll('td')
        insp_dict = {}
        for i in xrange(0, len(insp), 3):
            id_ = clean_string(insp[i].contents[0]['id'])
            type_ = clean_string(insp[i].contents[0].contents[0])
            date = clean_string(insp[i+1].contents[0])
            result = clean_string(insp[i+2].contents[0])
            insp_dict[id_] = {'type':type_, 'date':date, 'result':result}
        
        # get all violation information for each inspection:
        insp_dict_updated = get_violations(browser, insp_dict)
    
        return insp_dict_updated

def get_violations(browser, insp_dict):
    '''
    Wrapper that loops through all inspections and tries to obtain violation-level information.
    If an inspection fails to load, prints an error message and then continues with next inspection.

    INPUT:  browser:   Selenium browser
            insp_dict: dict, all inspections for a given restaurant. 
                       key = page id that can be used to access violation-level 
    OUTPUT: insp_dict: dict, all inspections for a given restaurant.
                       each inspection now owns a violation dict populated with violation info

    NOTE: If an error is caught by the except group, the insp_dict entry for that key is not 
          populated with a viol_dict.
    '''
    # Loop through each unseen restaurant and get the inspection info
    for page in insp_dict.keys():
        try:
            insp_dict[page]['violations'] = access_inspection(browser, page)
        except Exception as e:
            print 'Failed to access inspection violations: %s, Exception: %s' % (page, e)
            
    return insp_dict
    
def access_inspection(browser, this_insp):
    '''
    Go to page for a given inspection, download violation information and save in new dict.

    INPUT:  browser:   Selenium browser
            this_insp: string, id of inspection link that should be accessed
    OUTPUT: viol_dict: dict, All violation information. Violation comments are saved as list and 
                             still need to be processed and extracted as individual components
    '''
    # Access inspection page:
    browser.find_element_by_id(this_insp).click()

    # Load view with all violations:
    browser.find_element_by_id('MainContent_rblCDC_1').click()
    
    # save results as BeautifulSoup:
    soup = BeautifulSoup(browser.page_source)

    # Scrape violation-level info if there are valid results:
    viol_dict = scrape_violations(soup)
      
    # return to inspection_level page
    browser.find_element_by_id('MainContent_lnkBackToList').click()
    return viol_dict

def scrape_violations(soup):
    '''
    Scrape all information from BeautifulSoup-encoded content of a violations page.

    INPUT:  soup:      BeautifulSoup, content of page describing violations from 1 inspection
    OUTPUT: viol_dict: dict, All violation information. Violation comments are saved as list and 
                             still need to be processed and extracted as individual components
    '''
    if len(soup.findAll('label',attrs={'id':'MainContent_lblNoResults'})) > 0:
        return {}
    else:
        # Get VIOLATION table
        t = soup.findAll('table', attrs={'id':'MainContent_tblViolation'})[0]

        # Save violation-level information from table:
        viol = t.findAll('td', attrs={'class':'ViolationColumn'})
        comments = t.findAll('td', attrs={'class':'FullColumn'})
        viol_dict = {}
        for v, c in zip(viol, comments):
            code = clean_string(v.text)
            verbose = clean_string(v.attrs['title'])
            comments = re.split('<br/>',re.sub('</?b>','',clean_string(c.decode_contents())))
            if code in viol_dict:
                code = code + '_2'
            viol_dict[code] = comments
        
        return viol_dict

def save_to_pickle(data, fname):
    with open(fname, 'wb') as handle:
        pickle.dump(data, handle)


def open_pickle(f_name):
    with open(f_name, 'rb') as f:
        data = pickle.load(f)
    return data

#-------------------------
# Clean up handful of cases with errors:
def fix_restaurant(browser, f_in, f_out, problem_list):
    '''
    Redownloads inspection- and violation-level information for selected restaurants,
    replaces entries in the original dictionary, and writes a new file.

    INPUT: browser:  selenium browser
           f_in:     string, file containing originally downloaded dictionary of restaurants
           f_out:    string, file to write to
           problem_list: list of strings, names of restaurants to re-download

    Writes new file to f_out.

    ex. fix_restaurant(browser, 
                       '../data/mad/mad_health_2.pkl', 
                       '../data/mad/mad_health_2_FINAL.pkl',
                       ['Rodeway Inn & Suites', 'Chang Jiang', "Woodman's Food Market 20",
                        'Walgreens 111', 'A-mart', 'The Spot Restaurant'])

    ex. fix_restaurant(browser,
                       '../data/mad/mad_health_3.pkl',
                       '../data/mad/mad_health_3_FINAL.pkl',
                       ['El Bolillo Bakery', 'Reverend Jims Saloon', 'La Tolteca'])

    ex. fix_restaurant(browser,
                       '../data/mad/mad_health_e.pkl',
                       '../data/mad/mad_health_e_FINAL.pkl',
                       ["Luigi's Diner"])
    '''
    # Read in data
    R_2 = open_pickle(f_in)
    df_2 = pd.DataFrame.from_dict(R_2).T
    
    # These 6 restaurants had the following error message when trying to access the link
    # to their inspection-level information:
    #     Exception: Message: stale element reference: 
    #                element is not attached to the page document
    df_replace = df_2[df_2.name.isin(problem_list)]
    
    # Re-download all data for these files:
    prob_dict = {}
    
    for term in problem_list:
        if term == "Woodman's Food Market 20":
            term = "Woodman's Food Market"
        elif term == "Walgreens 111":
            term = "Walgreens"
            
        restaurants = search_restaurants(browser, term)
        prob_dict.update(restaurants)
        print 'Term: %s    # New Restaurants: %d' % (term, len(restaurants))
        
    df_prob = pd.DataFrame.from_dict(prob_dict).T
    
    # Replace nan's with inspection dictionary that was just downloaded
    R_2_final = R_2.copy()
    for id_ in df_replace.index:
        R_2_final[id_]['inspections'] = df_prob.loc[id_,'inspections']
    
    save_to_pickle(R_2_final, f_out)


if __name__ == '__main__':
    if len(argv) > 1:
        term = argv[1]
        out_file = argv[2]
    
    if len(argv) > 3:
        seen = set(open_pickle(argv[3]))
    else:
        seen = set()
    
    path_to_chromedriver = '/Users/tracy/Desktop/chromedriver' 
    browser = webdriver.Chrome(executable_path = path_to_chromedriver)
    
    R = search_restaurants(browser, term, seen)

    save_to_pickle(R, out_file)
