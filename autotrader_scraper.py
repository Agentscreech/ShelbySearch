import requests

from bs4 import BeautifulSoup



def find_listings(params):
    '''grabs all the listing urls and distance for a given autotrader query'''
    url = "https://www.autotrader.com/cars-for-sale/Ford/Mustang/?zip=" + str(params["zipcode"]) + "&extColorsSimple=" + params["color"] + "&startYear=" + params["minYear"] + "&numRecords=100&endYear=" + params["maxYear"] + "&modelCodeList=MUST&makeCodeList=FORD&sortBy=distanceASC&firstRecord=0&searchRadius=" + str(params["radius"]) + "&trimCodeList=" + params["trim"]
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'}
    print(url)
    urls = []
    distances = []
    try:
        autotrader_results_html = requests.get(url, headers=headers)
    except requests.exceptions.RequestException as e:
        print(e)
    results_soup = BeautifulSoup(autotrader_results_html.content, "html.parser")
    for link in results_soup.find_all("a", attrs={"data-qaid": "lnk-lstgTtlf"}):
        urls.append(link.get('href').split("&")[0])
    for distance in results_soup.find_all(attrs={"data-qaid": "cntnr-dlrlstng-radius"}):
        distances.append(distance.get_text())
    return urls, distances


def get_listing_details(sub_url, distance):
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'}
    url = "https://www.autotrader.com" + sub_url
    # print("trying", url)
    try:
        listing_results_html = requests.get(url, headers=headers)
    except:
        print("listing results request failed")
    listing_soup = BeautifulSoup(listing_results_html.content, "html.parser")
    car = {}
    name = listing_soup.find(attrs={"data-qaid": "cntnr-vehicle-title"})
    price = listing_soup.find(attrs={"data-qaid": "cntnr-pricing-cmp-outer"})
    if price:
        car["price"] = price.get_text()
    vin = listing_soup.find(attrs={"data-qaid": "tbl-value-VIN"})
    dealer = listing_soup.find(attrs={"data-qaid": "dealer_name"})
    address = listing_soup.find(attrs={"itemprop": "address"})
    if address:
        car["address"] = address.get_text()
    phone = listing_soup.find(attrs={"data-qaid": "dlr_phone"})
    if phone:
        car["phone"] = phone.get_text()
    pic = listing_soup.find(class_="media-viewer")
    if pic:
        car["pic"] = pic.find("img").get("src")
    car["name"] = name.get_text()
    car["url"] = url
    car["vin"] = vin.get_text()
    car["dealer"] = dealer.get_text()
    car["distance"] = distance
    # print(car)
    return car
