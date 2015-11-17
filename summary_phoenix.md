# Phoenix, AZ

## Data

### Inspections:

Health Inspection data was gathered from the Maricopa County's Environmental Services portal. (http://www.maricopa.gov/EnvSvc/OnlineApplication/EnvironmentalHealth/FoodInspections)

Inspection dates ranged from: 10/23/2012 to 10/14/2015

The main information collected for each inspection include:
- `Date`
- `Purpose`
- `Grade`
- `# Violations - Priority`
	* A provision that contributes directly to the elimination, prevention, or reduction to an acceptable level, of hazards associated with foodborne illness or injury. There are no other provisions that more directly control the hazard in question.
- `# Violations - Priority Foundation`
	* A provision whose application supports, facilitates or enables one or more priority items.
- `# Violations - Core`
	* A provision that relates to general sanitation, operational controls, facilities or structures, equipment design, or general maintenance, and which is not designated as a Priority Item or Priority Foundation Item.
	* For more information, see: http://www.maricopa.gov/EnvSvc/EnvHealth/Violations.aspx

### Merge with Yelp Data:
After merging with the yelp business database:
- 4090 Restaurants
- 23,487 Inspection Instances
	* An inspection instance was defined as the period ending on the date of inspection and starting on the day after the previous inspection. If no previous inspection is available, the inspection period starts 6 months prior to the date of inspection.
	* For now, only ***routine*** inspections were used to create inspection instances.
	* Inspection instances span the period from: 04/24/2012 to 10/14/2015

## Target Generation:

The target (i.e. dependent variable) is based on `# Violations - Priority`.
- For classification modeling, thresholds from t = 1 to 6 were evaluated to create a binary target.
- For regression modeling, the total number of violations was used as the target.

## Classification Modeling:
These are the initial untuned models that were tested using model classes from `sklearn`:
```
model_rfc = RandomForestClassifier(oob_score=True, 
                                   random_state = 981, 
                                   class_weight='balanced')
model_log = LogisticRegression()
model_svc = LinearSVC(C=0.19, random_state = 981, class_weight='balanced')
```

With only basic features ``, we saw the following results:

|              | FN   | FP   | TN   | TP   | accuracy | f1       | mse       | precision | recall   | model                  |
|--------------|------|------|------|------|----------|----------|-----------|-----------|----------|----------------------- |
| sum_priority |      |      |      |      |          |          |           |           |          |                        |
| 1            | 2457 | 1817 | 3675 | 1446 | 0.545077 | 0.403572 | 0.454923  | 0.443150  | 0.370484 | RandomForestClassifier |
| 2            | 1253 | 608  | 7417 | 117  | 0.801916 | 0.111695 | 0.198084  | 0.161379  | 0.085401 | RandomForestClassifier |
| 3            | 430  | 120  | 8835 | 10   | 0.941458 | 0.035088 | 0.058542  | 0.076923  | 0.022727 | RandomForestClassifier |
| 4            | 124  | 29   | 9239 | 3    | 0.983715 | 0.037736 | 0.016285  | 0.093750  | 0.023622 | RandomForestClassifier |
| 5            | 35   | 12   | 9348 | 0    | 0.994997 | 0.000000 | 0.005003  | 0.000000  | 0.000000 | RandomForestClassifier |
| 6            | 10   | 4    | 9381 | 0    | 0.998510 | 0.000000 | 0.001490  | 0.000000  | 0.000000 | RandomForestClassifier |
| 1            | 3822 | 88   | 5404 | 81   | 0.583821 | 0.039784 | 0.416179  | 0.479290  | 0.020753 | LogisticRegression     |
| 2            | 1370 | 0    | 8025 | 0    | 0.854178 | 0.000000 | 0.145822  | 0.000000  | 0.000000 | LogisticRegression     |
| 3            | 440  | 0    | 8955 | 0    | 0.953167 | 0.000000 | 0.046833  | 0.000000  | 0.000000 | LogisticRegression     |
| 4            | 127  | 0    | 9268 | 0    | 0.986482 | 0.000000 | 0.013518  | 0.000000  | 0.000000 | LogisticRegression     |
| 5            | 35   | 0    | 9360 | 0    | 0.996275 | 0.000000 | 0.003725  | 0.000000  | 0.000000 | LogisticRegression     |
| 6            | 10   | 0    | 9385 | 0    | 0.998936 | 0.000000 | 0.001064  | 0.000000  | 0.000000 | LogisticRegression     |
| 1            | 3903 | 0    | 5492 | 0    | 0.584566 | 0.000000 | 0.415434  | 0.000000  | 0.000000 | LinearSVC              |
| 2            | 1370 | 0    | 8025 | 0    | 0.854178 | 0.000000 | 0.145822  | 0.000000  | 0.000000 | LinearSVC              |
| 3            | 440  | 0    | 8955 | 0    | 0.953167 | 0.000000 | 0.046833  | 0.000000  | 0.000000 | LinearSVC              |
| 4            | 127  | 0    | 9268 | 0    | 0.986482 | 0.000000 | 0.013518  | 0.000000  | 0.000000 | LinearSVC              |
| 5            | 35   | 0    | 9360 | 0    | 0.996275 | 0.000000 | 0.003725  | 0.000000  | 0.000000 | LinearSVC              |
| 6            | 10   | 0    | 9385 | 0    | 0.998936 | 0.000000 | 0.001064  | 0.000000  | 0.000000 | LinearSVC              |

