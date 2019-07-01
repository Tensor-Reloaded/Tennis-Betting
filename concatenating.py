import pandas as pd 

total = pd.DataFrame()
for i in range(2001,2019):
    extension = '.xls' if i < 2013 else '.xlsx'
    current_file = pd.read_excel("data/"+str(i)+extension)
    current_file["Date"] = pd.to_datetime(current_file["Date"])
    total = pd.concat([total,current_file], sort=False)
total.to_csv("data/total_data.csv")

cities = list(total["Location"].unique())
cities_dict = {cities[i].strip():-1 for i in range(len(cities))}

with open("data/city2id.json", 'w') as out:
    out.write(str(cities_dict))