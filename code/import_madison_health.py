from selenium import webdriver
from bs4 import BeautifulSoup
import re
import pickle
from sys import argv
from unidecode import unidecode

def clean_string(text):
    return unidecode(text.encode('utf8').decode('utf8'))

def search_restaurants(browser, search_term, rest_seen={}, get_inspection=True):
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
    # Loop through each unseen restaurant and get the inspection info
    print 'Number of new restaurants to scrape: %d' % len(rest_dict)
    for page in rest_dict.keys():
        try:
            rest_dict[page]['inspections'] = access_restaurant(browser, page)
        except Exception as e:
            print 'Failed to access inspection: %s (%s), Exception: %s' % (page, rest_dict[page]['name'], e)
            try:
                browser.find_element_by_id('MainContent_lnkBackToSearch').click()
            except:
                print 'On main page'
            
    return rest_dict

def access_restaurant(browser, this_rest):
    # Access restaurant page:
    browser.find_element_by_id(this_rest).click()

    # save results as BeautifulSoup:
    soup = BeautifulSoup(browser.page_source)

    # Scrape inspection info if there are valid results:
    insp_dict = scrape_inspections(soup)
      
    # return to search results
    browser.find_element_by_id('MainContent_lnkBackToSearch').click()
    return insp_dict

def scrape_inspections(soup):
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
    # Loop through each unseen restaurant and get the inspection info
    for page in insp_dict.keys():
        try:
            insp_dict[page]['violations'] = access_inspection(browser, page)
        except Exception as e:
            print 'Failed to access inspection violations: %s, Exception: %s' % (page, e)
            
    return insp_dict
    
def access_inspection(browser, this_insp):
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
