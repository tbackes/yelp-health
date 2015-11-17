# yelp-health
Linking Yelp Reviews to Safety Inspection Outcomes

## City-Specific Pages
To see more details on each city that was modeled, browse the following links:
- [Phoenix, AZ](https://github.com/tbackes/yelp-health/blob/master/summary_phoenix.md)

## Datasets
### Yelp Challenge Data
Yelp Challenge Data is available for the following cities:

* Pittsburgh, Charlotte, Urbana-Champaign, Phoenix, Las Vegas and Madison
* http://www.yelp.com/dataset_challenge

### Health Inspection Data
Health Inspection data (scores and reports) have varying availability/accessibility across cities.

* **Pittsburgh**: PDFs of each inspection report are available as early as 2011 (I haven't checked earlier dates yet).
* **Charlotte**: Scores and grades are available as early as 2013. Violation details are available online, but are much trickier to scrape. I'm not sure if I'll have time to scrape the violation details.
* **Urbana-Champaign**: HTML tables of inspection/violation reports are available online. However, I haven't been able to figure out the logic behind url queries to generate these keys... so this city is on hold for now.
* **Phoenix**: Grades and violation details are available as early as 2013. Web-scraping of violation details in progress.
* **Las Vegas**: All data available as downloadable SQL database. Sweet! 
* **Madison**: Data is available online, but html tables are generated by javascripts. Not sure how to scrape, so this city is on hold for now.


## Previous work
* http://engineeringblog.yelp.com/2015/04/data-science-contest-keeping-it-fresh-predict-restaurant-health-scores.html
* http://www.drivendata.org/competitions/5/
* https://gcn.com/articles/2015/03/02/yelp-city-restaurant-inspections.aspx
* http://www.kdnuggets.com/2015/05/drivendata-competition-keeping-boston-fresh.html
* http://people.hbs.edu/mluca/hygiene.pdf
* https://rpubs.com/attarwala/restauranthygiene
* http://www.kval.com/news/health/In-Tracking-Outbreaks-Of-Food-Poisoning-Can-Yelp-Help-335975901.html
* http://www.washingtonpost.com/news/wonkblog/wp/2015/10/27/how-yelp-plans-to-clean-up-one-of-the-restaurant-industrys-most-dangerous-flaws/
* http://www.city-data.com/restaurants-index/Nevada.html
