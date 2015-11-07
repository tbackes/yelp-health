import requests
import pandas as pd
import phoenix_health as ph
import pickle
from sys import argv

if __name__ == '__main__':
    if len(argv) == 1:
        file_R = '../data/phx/phoenix_restaurants.pkl'
        file_I = '../data/phx/phoenix_inspections.pkl'
        file_V = '../data/phx/phoenix_violations.pkl'
        file_R = '../data/phx/phoenix_R'
        file_I = '../data/phx/phoenix_I'
        file_V = '../data/phx/phoenix_V'
    else:
        file_R = argv[1]
        file_I = argv[2]
        file_V = argv[3]
    
    rest = raw_input("restaurant info (y = scrape & write to file / n = read from file): ")
    if rest == 'y':
        start = raw_input("Start from page (1-2186): ")
        end = raw_input("Stop at page (1-2186 or all): ")
    insp = raw_input("inspection info (y = scrape & write to file / n = read from file): ")
    if insp == 'y':
        start = raw_input("Start from row (1-20316): ")
        end = raw_input("Stop at row (1-20316 or all): ")
    
    
    if rest == 'y' and insp == 'n':
        s = requests.Session()
        if end == 'all':
            end = '2186'
        if start == end:
            R = ph.scrape_restaurant_data([int(start)], s, int(start))
            print '\n\nFinished scraping restaurant data.'
            R.to_pickle('%s_%04d.pkl' % (file_R, int(start)))
            print 'R[%d, %d): %s' % (int(start), int(start), R.shape)
        else: 
            for i in xrange(int(start), int(end), 50):
                j = min(i + 50, int(end)+1)
                R = ph.scrape_restaurant_data(xrange(i, j), s, j-1)
                print '\nFinished scraping restaurant data.'
                R.to_pickle('%s_%04d.pkl' % (file_R, j-1))
                print 'R[%d, %d): %s' % (i, j, R.shape)

    elif rest == 'n' and insp == 'y':
        s = requests.Session()
        if end == 'all':
            end = '20316'
        with open('%s_full.pkl' % file_R) as f_R:
            R = pickle.load(f_R)
        if start == end:
            I, V = ph.scrape_inspection_data(R.iloc[int(start),:], s, int(start))
            print '\n Finished scraping inspection data.'
            I.to_pickle('%s_%05d.pkl' % (file_I, int(start)))
            V.to_pickle('%s_%05d.pkl' % (file_V, int(start)))
            print 'I[%05d]: %s   V[%05d]: %s' % (int(start), I.shape, int(start), V.shape)
        else:
            step_size = 50
            for i in xrange(int(start), int(end)+1, step_size):
                j = min(i + step_size, int(end) + 1)
                I, V = ph.scrape_inspection_data(R.iloc[i:j,:], s, j-1)
                print '\n Finished scraping inspection data.'
                I.to_pickle('%s_%05d.pkl' % (file_I, j-1))
                V.to_pickle('%s_%05d.pkl' % (file_V, j-1))
                print 'I[%05d, %05d): %s   V[%05d, %05d): %s' % (i, j, I.shape, i, j, V.shape)

