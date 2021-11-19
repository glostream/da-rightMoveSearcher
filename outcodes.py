from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import json
# import numpy as np

# postcodes = np.genfromtxt('postcodes.csv', delimiter=',', encoding=None, skip_header=1, dtype=None, usecols=0)

# outjson = {}
# with open('RightMoveOutcodes.json', 'r') as f:
# 	postcodeJson = json.load(f)
# 	for k in postcodeJson:
# 		part1 = postcodeJson[k].split('locationIdentifier=')[1]
# 		code = part1.split('&')[0]
# 		outjson[k] = code


# with open('edited.json', 'w') as outfile:
# 	json.dump(outjson, outfile)


codes = {}
postcodes = []
with open('postcodesEdited.csv', 'r') as f:
	f.readline()
	for line in f:
		cols = line.split(';')
		pcs = cols[1].split(',')
		for pc in pcs:
			postcodes.append(pc.strip())

missing = [p for p in postcodes if p not in postcodeJson.keys()]

print(len(missing))

driver = webdriver.Chrome(executable_path=r'C:\Users\jmbti\Desktop\chromedriver.exe')


driver.get("https://www.rightmove.co.uk/property-for-sale/find.html?locationIdentifier=OUTCODE%5E1858&insId=1&minPrice=800000&numberOfPropertiesPerPage=24&areaSizeUnit=sqft&includeSSTC=true&_includeSSTC=on&googleAnalyticsChannel=buying")



for i, p in enumerate(missing):
	print(len(missing) - i, " remaining...")
	# search_bar = driver.find_element_by_xpath('//*[@id="filters-location"]/div/input')
	search_bar = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="filters-location"]/div/input')))
	search_bar.send_keys(Keys.BACKSPACE)
	search_bar.send_keys(Keys.BACKSPACE)
	search_bar.send_keys(Keys.BACKSPACE)
	search_bar.send_keys(Keys.BACKSPACE)
	search_bar.send_keys(Keys.BACKSPACE)
	search_bar.send_keys(Keys.BACKSPACE)
	search_bar.send_keys(Keys.BACKSPACE)
	search_bar.send_keys(p)
	search_bar.send_keys(Keys.RETURN)
	part1 = driver.current_url.split('locationIdentifier=')[1]
	code = part1.split('&')[0]
	codes[p] = code
	if i % 100 == 0:
		with open('datamissing.json', 'w') as outfile:
			json.dump(codes, outfile)

	driver.get("https://www.rightmove.co.uk/property-for-sale/find.html?locationIdentifier=OUTCODE%5E1858&insId=1&minPrice=800000&numberOfPropertiesPerPage=24&areaSizeUnit=sqft&includeSSTC=true&_includeSSTC=on&googleAnalyticsChannel=buying")
	# time.sleep(1)


with open('datamissing.json', 'w') as outfile:
	json.dump(codes, outfile)

driver.close()