import requests
import re
import time
from datetime import datetime
from bs4 import BeautifulSoup

def find_proxies():
    proxies = []
    proxy_html = requests.get("http://us-proxy.org")
    soup = BeautifulSoup(proxy_html.content, "html.parser")
    data = soup.find_all("td")
    ip = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', re.UNICODE)
    for i,row in enumerate(data):
        if row.get_text():
            if ip.match(row.get_text()):
                proxy = {"http":""}
                proxy["http"] = "http://"+row.get_text()+":"+data[i+1].get_text()
                proxies.append(proxy)
    return proxies

def test_proxies(proxies):
    print("testing proxies")
    valid_proxies = []
    response_times = []
    for proxy in proxies:
        try:
            t0 = time.time()
            test_server = requests.get("http://www.etis.ford.com/vehicleSelection.do", proxies=proxy, timeout=5)
            t1 = time.time()
        except requests.exceptions.RequestException as e:
            continue
        if test_server.status_code == 200:
            response_times.append(t1-t0)
            valid_proxies.append(proxy)
            print(proxy, "was valid")
    return [valid_proxies for (response_times,valid_proxies) in sorted(zip(response_times,valid_proxies))]


def get_car_details(vin_number, cookies):
    '''this should grab the deatils from Fords ETIS site
    and then returns and object to query the DB with'''

    url = "http://www.etis.ford.com/vehicleSelection.do"
    #need the cookies to send a post request with vin, so just query the site to grab one
    # try:
    #     set_cookies = requests.get(url)
    # except:
    #     print("initial request failed")
    querystring = {"vin":vin_number, "lookupType":"vin"}

    # headers = {
    #     'host': "www.etis.ford.com",
    #     'connection': "keep-alive",
    #     'content-length': "36",
    #     'pragma': "no-cache",
    #     'cache-control': "no-cache",
    #     'origin': "http://www.etis.ford.com",
    #     'upgrade-insecure-requests': "1",
    #     'user-agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36",
    #     'content-type': "application/x-www-form-urlencoded",
    #     'accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    #     'dnt': "1",
    #     'referer': "http://www.etis.ford.com/vehicleRegSelector.do",
    #     'accept-encoding': "gzip, deflate, br",
    #     'accept-language': "en-US,en;q=0.8"
    #     }
    headers = {
        'user-agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36",
        'Accept':"*/*",
        'Host':"www.etis.ford.com",
        'accept-encoding':"gzip, deflate",
        'content-length':""
    }
    # print(url, headers, querystring, cookies)
    for i in range(2):
        print("attempt", i+1, "of 3")
        try:
            car_details_html = requests.post(url, headers=headers, data=querystring, cookies=cookies, timeout=30)
            print("post status code", car_details_html.status_code)
            car_details_soup = BeautifulSoup(car_details_html.content, "html.parser")
            status = car_details_soup.find("title").get_text().strip() # shoule be Vehical Summary
            # if car_details_html.status_code[0] == 5:
            #     return "Server Error"
            if "Summary" in status:
                #handle Unavailable and don't update the DB for it
                # print(status)
                primary_features_section = car_details_soup.find_all(class_="table__contents")[2]
                break
        except requests.exceptions.RequestException as e:
            print(e)
            print("ETIS site query failed")
            return "Server Error"
        # else:
        #     break
    #title should be Vehical Summary. If it's Vehical Lookup, it was invalid
    # print(status)
    # primary_features_section = car_details_soup.find(id="pfcSummary")
    # primary_col1 = primary_features_section.find_all(class_="summaryPrompt")
    # primary_features = primary_features_section.find_all(class_="summaryContent")
    options = {}
    # for i, col in enumerate(primary_col1):
    #     if col.get_text() == "Build Date:":
    #         options["build_date"] = primary_features[i].get_text().split("\xa0\xa0")[1]
    #     if col.get_text() == "Paint:":
    #         options["color"] = primary_features[i].get_text().split("\xa0\xa0")[1]
    for feature in primary_features_section:
        if not feature.string:
            if "Build" in feature.th.get_text():
                temp = feature.td.get_text(strip=True).split(" ")
                if temp[-1] == "2":
                    options["build_date"] = "PENDING"
                else:
                    del temp[4]
                    date = " ".join(temp)
                    options["build_date"] = datetime.strptime(date,  "%a %b %d %H:%M:%S %Y").strftime("%d.%m.%y")
            if "Paint" in feature.th.get_text():
                options["color"] = feature.td.get_text()

    #now to the minor feature list
    #Vehicle Cover B == painted black roof
    #Accent Stripe-<data I want> = Stripe
    #SVT-R Package = R model
    #With Temp Control Driver Seat = convenience Package
    #With Navigation System && Less Temp Control Driver Seat = Electronics Package
    minor_features_section = car_details_soup.find(id="mfcList")
    minor_features = minor_features_section.find_all("li")
    for feature in minor_features:
        feature = feature.get_text()
        # if "Vehicle Cover B" in feature:
        #     options["painted_roof"] = True
        if "Accent Stripe-" in feature:
            options["stripe"] = feature.split("-")[1]
        if "With Drivers Heated" in feature:
            options["convenience"] = True
        if "With Navigation" in feature:
            options["has nav"] = True


    #check for electronic or convienence Package
    if "has nav" not in options:
        options["electronics"] = False
        options["convenience"] = False
    if "has nav" in options and "convenience" not in options:
        options.pop("has nav", None)
        options["electronics"] = True
        options["convenience"] = False
    if "convenience" in options:
        if options["convenience"]:
            options.pop("has nav", None)
            options["electronics"] = False
    #add other options as False
    # if "painted_roof" not in options:
    #     options["painted_roof"] = False
    if "stripe" not in options:
        options["stripe"] = False
    if "color" not in options:
        options["color"] = False
    # if options["build_date"].split('.')[2] == "0002":
    #     options["build_date"] = "PENDING"
    # print(options)
    return options


def calc_check_digit(vin_to_calc, total):
    '''given a vin number with missing check digt, return vin with calculated check digit'''
    for i, number in enumerate(vin_to_calc):
        if i == 13:
            total += int(number)*5
        if i == 14:
            total += int(number)*4
        if i == 15:
            total += int(number)*3
        if i == 16:
            total += int(number)*2
    check_digit = total % 11
    if check_digit == 10:
        check_digit = "X"
    calculated_vin = vin_to_calc.replace("_", str(check_digit))
    return calculated_vin
