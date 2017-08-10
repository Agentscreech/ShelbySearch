import requests

from bs4 import BeautifulSoup


def get_car_details(vin_number, cookies, proxies):
    '''this should grab the deatils from Fords ETIS site
    and then returns and object to query the DB with'''

    url = "https://www.etis.ford.com/vehicleSelection.do"
    #need the cookies to send a post request with vin, so just query the site to grab one
    # try:
    #     set_cookies = requests.get(url)
    # except:
    #     print("initial request failed")
    querystring = {"vin":vin_number, "lookupType":"vin"}

    headers = {
        'host': "www.etis.ford.com",
        'connection': "keep-alive",
        'content-length': "36",
        'pragma': "no-cache",
        'cache-control': "no-cache",
        'origin': "https://www.etis.ford.com",
        'upgrade-insecure-requests': "1",
        'user-agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36",
        'content-type': "application/x-www-form-urlencoded",
        'accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        'dnt': "1",
        'referer': "https://www.etis.ford.com/vehicleRegSelector.do",
        'accept-encoding': "gzip, deflate, br",
        'accept-language': "en-US,en;q=0.8"
        }
    try:
        car_details_html = requests.post(url, headers=headers, data=querystring, cookies=cookies, proxies=proxies)
    except:
        print("ETIS site query failed")
        return "retry"
    car_details_soup = BeautifulSoup(car_details_html.content, "html.parser")
    #title should be Vehical Summary. If it's Vehical Lookup, it was invalid
    status = car_details_soup.find("title").get_text().strip() # shoule be Vehical Summary
    if "Lookup" in status:
        return False
    if "Unavailable" in status:
        #handle Unavailable and don't update the DB for it
        # print(status)
        return "retry"
    print(status)
    primary_features_section = car_details_soup.find(id="pfcSummary")
    primary_features = primary_features_section.find_all(class_="summaryContent")
    options = {}
    options["Build Date"] = primary_features[0].get_text().split("\xa0\xa0")[1]
    options["Color"] = primary_features[-1].get_text().split("\xa0\xa0")[1]

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
        if "Vehicle Cover B" in feature:
            options["Painted Black Roof"] = True
        if "Accent Stripe-" in feature:
            options["Over the Top Racing Stripe"] = feature.split("-")[1]
        if "With Drivers Heated" in feature:
            options["Convenience Package"] = True
        if "With Navigation" in feature:
            options["has nav"] = True

    #check for electronic or convienence Package
    if "has nav" not in options:
        options["Electronics Package"] = False
        options["Convenience Package"] = False
    if "has nav" in options and "Convenience Package" not in options:
        options.pop("has nav", None)
        options["Electronics Package"] = True
        options["Convenience Package"] = False
    if "Convenience Package" in options:
        options.pop("has nav", None)
        options["Electronics Package"] = False
    #add other options as False
    if "Painted Black Roof" not in options:
        options["Painted Black Roof"] = False
    if "Over the Top Racing Stripe" not in options:
        options["Over the Top Racing Stripe"] = False
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



def generate_2017gt350_vins(r=False):
    '''generate all vins 1-9999 and then send to calc_check_digit for final number'''
    if r:
        base_vin = "1FATP8JZ_H552"
    else:
        base_vin = "1FA6P8JZ_H552"
    counter = 1
    all_possible_vins = []
    while counter < 9999:
        vin = base_vin
        missing = len(str(counter))
        while len(vin) < 17-missing:
            vin += "0"
        vin += str(counter)
        if vin[3] == "T":
            total = 374
        else:
            total = 389
        all_possible_vins.append(calc_check_digit(vin, total))
        counter += 1
    return all_possible_vins
