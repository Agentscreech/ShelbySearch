import requests

from bs4 import BeautifulSoup

#<strong data-qaid="cntnr-resultTotal" data-reactid="134">556</strong>


def find_listings(params, urls, distances, firstRecord = 0, results_left = 0):
    '''grabs all the listing urls and distance for a given autotrader query'''
    url = "https://www.autotrader.com/cars-for-sale/Ford/Mustang/?zip=" + str(params["zipcode"]) + "&extColorsSimple=" + params["color"] + "&startYear=" + params["minYear"] + "&numRecords=100&endYear=" + params["maxYear"] + "&modelCodeList=MUST&makeCodeList=FORD&sortBy=distanceASC&firstRecord=" + str(firstRecord) + "&searchRadius=" + str(params["radius"]) + "&trimCodeList=" + params["trim"]
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'}
    print(url)
    try:
        autotrader_results_html = requests.get(url, headers=headers)
    except requests.exceptions.RequestException as e:
        print(e)
    results_soup = BeautifulSoup(autotrader_results_html.content, "html.parser")
    total_results = int(results_soup.find(attrs={"data-qaid": "cntnr-resultTotal"}).get_text())
    urls, distances = find_links(results_soup, urls, distances)
    if total_results > 100 and total_results > results_left:
        results_left += 100
        print(results_left)
        firstRecord += 100
        find_listings(params, urls, distances, firstRecord, results_left)
    return urls, distances

def find_links(soup, urls, distances):
    for link in soup.find_all("a", attrs={"data-qaid": "lnk-lstgTtlf"}):
        urls.append(link.get('href').split("&")[0])
    for distance in soup.find_all(attrs={"data-qaid": "cntnr-dlrlstng-radius"}):
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
    else:
        car["price"] = None
    vin = listing_soup.find(attrs={"data-qaid": "tbl-value-VIN"})
    dealer = listing_soup.find(attrs={"data-qaid": "dealer_name"})
    address = listing_soup.find(attrs={"itemprop": "address"})
    if address:
        car["address"] = address.get_text()
    else:
        car["address"] = None
    phone = listing_soup.find(attrs={"data-qaid": "dlr_phone"})
    if phone:
        car["phone"] = phone.get_text()
    else:
        car["phone"] = None
    pic = listing_soup.find(class_="media-viewer")
    if pic:
        pic_file = pic.find("img").get("src").split("/")
        pic_file[4], pic_file[5] = "640", "480"
        car["pic"] = "/".join(pic_file)
    else:
        car["pic"] = None
    if name:
        car["name"] = name.get_text()
    else:
        car["name"] = "Ford Shelby GT350"
    car["url"] = url
    car["listing"] = url.split("=")[1]
    if vin:
        car["vin"] = vin.get_text()
    else:
        car["vin"] = None
    car["dealer"] = dealer.get_text()
    car["distance"] = distance
    # print(car)
    return car
