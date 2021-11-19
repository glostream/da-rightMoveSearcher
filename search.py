from bs4 import BeautifulSoup, SoupStrainer
import requests
# from concurrent.futures import ThreadPoolExecutor
import asyncio
from aiohttp import ClientSession
import aiohttp
import re
import json
import os


#-----------------------------------------------------------------------------------------------

# minimum price of property
minPrice = 800000

# Maximum age of the listing. Choose 1, 3, 7, or 14 days
# set to 0 to ignore and show all listings regardless of age
dayAge = 0

# https://en.wikipedia.org/wiki/List_of_postcode_districts_in_the_United_Kingdom
# can search by postcode area, postcode district, postal town, or county 
# NOT case-sensitive for postal towns and counties e.g. 'LonDoN' is fine
locations = ['SE']

# choose either 'true' or 'false'
includeSSTC = 'true'

# list of keyword to search for. NOT case-sensitive
# '&' is treated as logical operator
keywords = ['Arranged as & Flats', 'Arranged as & apartments', 'Arranged as & maisonettes',
'Unbroken Freehold', 'Freehold Investment Containing', 'Self contained Flats', 'self contained residential flats', 'self contained apartments', 'self contained units', 'separate units'
'Multiunit Freehold', 'Block of Flats', 'Block of apartments', 'block of', 'portfolio']

# number of simultaneous searches to do. May crash if too high
batchSize = 10

#-----------------------------------------------------------------------------------------------


def findWholeWord(w):
    return re.compile(r'\b({0})\b'.format(w), flags=re.IGNORECASE).search


def cook(url):
	r = requests.get(url)
	return BeautifulSoup(r.text, 'html.parser')


async def fetchHtml(url: str, session: ClientSession, returnText=True, **kwargs) -> tuple:
	try:
            resp = await session.request(method="GET", url=url, **kwargs)
	except:
		print('request failed: %s' % url)
		if returnText:
			return ''
		else:
			return ('', '')
	if returnText:
		return await resp.text()
	else:
		text = await resp.text()
		url = resp.url
		return (text, url)


async def makeRequests(urls: set, returnText=True, **kwargs) -> None:
	async with ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
		tasks = []
		for url in urls:
			tasks.append(
				fetchHtml(url=url, session=session, returnText=returnText, **kwargs)
			)
		results = await asyncio.gather(*tasks)

	return results


def searchForKey(text, keywords):
	keyFound = False
	for k in keywords:
		andKeys = k.split(' & ')
		if len(andKeys) > 1:
			# boolList = [findWholeWord(ak)(text) for ak in andKeys]
			boolList = [re.search(ak, text, re.IGNORECASE) for ak in andKeys]
			if all(boolList):
				keyFound = True
				print(k)
		else:
			# if findWholeWord(k)(text):
			if re.search(k, text, re.IGNORECASE):
				keyFound = True
				print(k)

	return keyFound


def getPostcodes(postcodeArr, locations):
	postcodes = []
	for loc in locations:
		found = False
		for row in postcodeArr:
			if loc == row[0] or loc.lower() in row[2:]:
				for pc in row[1].split(','): postcodes.append(pc)
				found = True
			elif loc in row[1].split(','):
				postcodes.append(loc)
				found = True
		if not found: print('No match for', loc)

	return postcodes


def formSearchUrl(outcode, dayAge, page, minPrice, includeSSTC):
	if dayAge:
		return 'https://www.rightmove.co.uk/property-for-sale/find.html?locationIdentifier={outcode}&minPrice={minPrice}&sortType=6&index={index}&propertyTypes=&maxDaysSinceAdded={dayAge}&includeSSTC={includeSSTC}&mustHave=&dontShow=&furnishTypes=&keywords='\
		.format(outcode=outcode, dayAge=dayAge, index=(page-1)*24, minPrice=minPrice, includeSSTC=includeSSTC)
	else:
		return 'https://www.rightmove.co.uk/property-for-sale/find.html?locationIdentifier={outcode}&minPrice={minPrice}&sortType=6&index={index}&propertyTypes=&includeSSTC={includeSSTC}&mustHave=&dontShow=&furnishTypes=&keywords='\
		.format(outcode=outcode, index=(page-1)*24, minPrice=minPrice, includeSSTC=includeSSTC)


def scrapePagesForLinks(pages, getPageCounts=False):
	listingLinks = []
	pageCounts = []
	strainer = SoupStrainer('a', attrs={"class": "propertyCard-link"})
	countStrainer = SoupStrainer('span', attrs={"class": "searchHeader-resultCount"})
	for i, page in enumerate(pages):
		listingLinks.append([])
		soup = BeautifulSoup(page, 'lxml', parse_only=strainer)
		cards = soup.findAll("a", {"class": "propertyCard-link"})
		for c in cards[1::2]:
			link = c.get('href')
			if link.strip() == '':
				continue
			listingLinks[i].append('https://www.rightmove.co.uk' + link)
		if getPageCounts == True:
			if len(listingLinks[i]) == 25:
				countSoup = BeautifulSoup(page, 'lxml', parse_only=countStrainer)
				# print(countSoup.text)
				if int(countSoup.text.replace(',', '')) > 1008:
					print('too many results')
				pageCounts.append(int(countSoup.text)//24 + 1)
			else:
				pageCounts.append(1)

	if getPageCounts == True:
		return [listingLinks, pageCounts]
	else: return listingLinks


def main():
	# pool = ThreadPoolExecutor(max_workers=15)
	# propLinks = pool.map(getLinks, [searchResults])
	# postcodeTable = np.genfromtxt('./postcodesEdited.csv', delimiter=';', encoding=None, skip_header=1, dtype=None)

	postcodeTable = []
	with open('./postcodesEdited.csv', 'r') as postcodef:
		postcodef.readline()
		for line in postcodef:
			newLine = []
			for i in line.split(';'):
				newLine.append(i.strip())
			postcodeTable.append(newLine)

	with open('./RightMoveOutcodes.json', 'r') as jsonf:
		outcodeJson = json.load(jsonf)

	oldMatches = []	
	if os.path.isfile('./matches.csv'):
		with open('./matches.csv', 'r') as oldMatchesf:
			for nline in oldMatchesf:
				if nline != '\n':
					s = nline.split('(')[1][:-2].replace('"', '')
					oldMatches.append(s)
		
		if nline != '\n':
			with open('./matches.csv', 'a') as oldMatchesf:
				oldMatchesf.write('\n')

	postcodes = getPostcodes(postcodeTable, locations)
	postcodes = list(dict.fromkeys(postcodes))
	outcodes = [outcodeJson[pc] for pc in postcodes]

	print('Searching %d postcodes:\n' % len(postcodes))
	print(postcodes)
	print()

	allLinks = []
	for iset in range(len(outcodes) // batchSize + 1):
		urls = [formSearchUrl(oc, dayAge, 1, minPrice, includeSSTC) for oc in outcodes[iset*batchSize:(iset+1)*batchSize]]
		# print(urls)
		searchResults = asyncio.run(makeRequests(urls=urls))

		listingLinks, pageCounts = scrapePagesForLinks(searchResults, True)

		for ipc, pc in enumerate(pageCounts):
			if pc == 1:
				print('{}: < 24 listings'.format(postcodes[ipc+iset*batchSize]))
			else: print('{}: ~ {} listings'.format(postcodes[ipc+iset*batchSize], pc*24-12))

		extraPageSearches = []
		for i, count in enumerate(pageCounts):
			extraPageSearches.append([])
			if count > 1:
				for j in range(1, count):
					extraPageSearches[i].append(urls[i].replace('index=0', 'index={}'.format(j*24)))

		print('Getting listing links...\n')

		for i, s in enumerate(extraPageSearches):
			extraPageResults = asyncio.run(makeRequests(urls=s))
			extraPageLinks = scrapePagesForLinks(extraPageResults)
			for l in extraPageLinks:
				for ll in l:
					listingLinks[i].append(ll)


		for i in listingLinks: allLinks.append(i) 


#-------------------------------------------------------------------------------------------------
	
	total = 0
	for i, l in enumerate(allLinks):
		allLinks[i] = list(dict.fromkeys(l))
		total += len(allLinks[i])
	if total == 0:
		print('Search blocked, please try again.')
	else:
		print('found {} listings'.format(total))

	print('\n********************************************************************************')
	print('\nProperty listings gathered, searching for keywords...\n')

	matches = []
	strainer = SoupStrainer('div', attrs={"class": "OD0O7FWw1TjbTD4sdRi1_"})	
	strainer1 = SoupStrainer('div', attrs={"class": "STw8udCxUaBUMfOOZu0iL kJR0bMoi8VLouNkBRKGww"})
	strainer2 = SoupStrainer('p', attrs={"itemprop": "description"})
	strainerFeatures = SoupStrainer('li', attrs={"class": "lIhZ24u1NHMa5Y6gDH90A"})
	strainerPropType = SoupStrainer('div', attrs={"class": "_1fcftXUEbWfJOJzIUeIHKt"})
	
	for i, linkSet in enumerate(allLinks):

		print('{}: {} listings'.format(postcodes[i], len(linkSet)))

		for iset in range(len(linkSet) // batchSize + 1):
			linkBatch = linkSet[iset*batchSize:(iset+1)*batchSize]
			propertyPages = asyncio.run(makeRequests(urls=linkBatch, returnText=False))

			for j, page in enumerate(propertyPages):
				soupDescr = BeautifulSoup(page[0], 'lxml', parse_only=strainer)
				if soupDescr.text.strip() == '':
					soupDescr = BeautifulSoup(page[0], 'lxml', parse_only=strainer2)

				soupFeatures = BeautifulSoup(page[0], 'lxml', parse_only=strainerFeatures)
				propType = BeautifulSoup(page[0], 'lxml', parse_only=strainerPropType)

				description = soupDescr.text + ' ' + str(soupFeatures) + ' ' + str(propType.text)

				if len(description.split('disclaimer')) > 1: description = description.split('disclaimer')[0]
				if len(description.split('Disclaimer')) > 1: description = description.split('Disclaimer')[0]
				if len(description.split('DISCLAIMER')) > 1: description = description.split('DISCLAIMER')[0]

				keyFound = searchForKey(description, keywords)
				if keyFound:
					print(page[1])
					if str(page[1]) not in oldMatches and str(page[1]) not in matches:
						matches.append(str(page[1]))
						with open('matches.csv', 'a') as outf:
							outf.write('=HYPERLINK("%s")\n' % page[1])
		
	print('\nDiscovered {} new matches after searching {} property listings'.format(len(matches), total))


if __name__ == '__main__':
	main()



