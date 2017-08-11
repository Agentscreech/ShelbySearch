import os
import time
import random
from flask import Flask, send_file, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from car_scraper import *
from autotrader_scraper import *
app = Flask(__name__)
app.config.from_object(os.environ["APP_SETTINGS"])
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

from models import Result, Invalid

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/test')
# def test():
#     us_proxies = find_proxies()
#     proxies = test_proxies(us_proxies[:75]))
#     # proxies = [{'http': 'http://35.196.19.142:80'}, {'http': 'http://104.196.226.56:80'}, {'http': 'http://34.225.178.44:8080'}, {'http': 'http://64.77.242.74:3128'}, {'http': 'http://52.11.203.152:8083'}, {'http': 'http://52.24.78.66:80'}, {'http': 'http://198.110.57.6:8080'}, {'http': 'http://192.95.18.162:8080'}, {'http': 'http://47.91.229.46:8080'}, {'http': 'http://69.7.46.63:80'}, {'http': 'http://70.32.89.160:3128'}, {'http': 'http://47.74.134.234:80'}]
#     # proxy = random.choice(proxies)
#     for proxy in proxies:
#         print("trying with proxy", proxy)
#         good_proxy = proxy
#         try:
#             set_cookies = requests.get("http://www.etis.ford.com/", proxies=proxy, timeout=5)
#             if set_cookies.status_code == 200:
#                 break
#         except requests.exceptions.RequestException as e:
#             print(e)
#         else:
#             break
#     print("status code when getting cookie", set_cookies.status_code)
#     time_of_cookie = time.time()
#     for entry in db.session.query(Result).filter(Result.convenience==False).all():
#         now = time.time()
#         test = int(entry.vin[-4:])
#         print(test)
#         if test < 5272:
#             continue
#         if entry.electronics:
#             continue
#         print("checking", entry.vin, entry.electronics)
#         if now-time_of_cookie > 600:
#             print("getting new cookie")
#             for proxy in proxies:
#                 good_proxy = proxy
#                 try:
#                     set_cookies = requests.get("http://www.etis.ford.com/", proxies=proxy, timeout=5)
#                     if set_cookies.status_code == 200:
#                         break
#                 except requests.exceptions.RequestException as e:
#                     print(e)
#                 else:
#                     break
#             time_of_cookie = time.time()
#         #randomize proxy before sending
#         details = get_car_details(entry.vin, set_cookies.cookies, good_proxy)
#         if details == "retry":
#             print("getting details didn't work")
#             # test()
#         else:
#             #add the car to the cars table
#             if details["electronics"]:
#                 print("updating car")
#                 entry.electronics = True
#                 db.session.commit()
#
#
#
#     return "test complete"

@app.route('/api/search', methods=["POST"])
def search_autotrader():
    raw_params = request.get_json()
    print(raw_params)
    formatted_params = format_params(raw_params)
    #send these options to a function that scrapes autotrader with these params
    urls, distances = find_listings(formatted_params)
    print("found",len(urls),"cars")
    # new_car = get_listing_details(urls[0], distances[0])
    # now send each url and distance to listing details scrape_year
    autotrader_cars = []
    for i, _ in enumerate(urls):
        print("scraping car", i+1)
        #maybe send this to the redis worker?
        new_car = get_listing_details(urls[i], distances[i])
        autotrader_cars.append(new_car)
    #now that we have the vin for each car, check the DB for options
    #if it's not in the DB, serach and add it
    for car in autotrader_cars:
        print("car before db", car)
        build_options = get_car_build_options(car["vin"])
        for option in build_options:
            car[option] = build_options[option]
        print("car after db", car)
    return jsonify(autotrader_cars),200


    return "got it "


def get_car_build_options(vin):
    '''query db and set results to object to return'''
    db_result = db.session.query(Result).filter_by(vin=vin).first()
    if db_result is None:
        print("car was not in DB, fetching data for vin", vin)
        options = check_vin(vin)
        if options["stripe"] == "false":
            options["stripe"] = False
    else:
        # print(db_result.color, db_result.build_date,db_result.stripe,db_result.electronics,db_result.convenience,db_result.painted_roof)
        options = {}
        options["color"] = db_result.color
        options["build_date"] = db_result.build_date
        if db_result.stripe == "false":
            options["stripe"] = False
        else:
            options["stripe"] = db_result.stripe
        options["electronics"] = db_result.electronics
        options["convenience"] = db_result.convenience
        options["painted_roof"] = db_result.painted_roof
    print(options)

    return options

@app.route("/add_<year>")
# def scrape_year(year):
#     print("starting to scrape")
#     vins = generate_2017gt350_vins()
#     print("vins generated")
#     proxies = [
#         {'https': 'http://66.70.191.215:1080', 'http':'http://66.70.191.215:1080'},
#         # {'https': 'http://104.41.154.213:8118', 'http': 'http://104.41.154.213:8118'},
#         # {'https': 'http://54.204.31.39:4000', 'http': 'http://54.204.31.39:4000'},
#         # {'https': 'http://45.32.161.20:1080', 'http': 'http://45.32.161.20:1080'},
#         # {'https': 'http://162.243.55.213:8118', 'http': 'http://162.243.55.213:8118'},
#         # {'https': 'http://209.212.248.53:80', 'http': 'http://209.212.248.53:80'},
#         # {'https': 'http://209.212.253.18:1080', 'http': 'http://209.212.253.18:1080'},
#         # {'https': 'http://103.11.67.192:3128', 'http': 'http://103.11.67.192:3128'},
#         # {'https': 'http://191.96.227.75:62222', 'http': 'http://191.96.227.75:62222'}
#     ]
#     proxy = random.choice(proxies)
#     print("trying with proxy", proxy)
#     try:
#         set_cookies = requests.get("https://www.etis.ford.com/vehicleSelection.do", proxies=proxy)
#     except:
#         return "cookie request error"
#     time_of_cookie = time.time()
#     print("got", len(vins), "vins")
#     for vin in vins:
#         print("checking", vin)
#         is_invalid = db.session.query(Invalid).filter_by(vin=vin).first()
#         db_check = db.session.query(Result).filter_by(vin=vin).first()
#         now = time.time()
#         if now-time_of_cookie > 600:
#             print("getting new cookie")
#             set_cookies = requests.get("https://www.etis.ford.com/vehicleSelection.do", proxies=proxy)
#             time_of_cookie = time.time()
#         if db_check is None and is_invalid is None:
#             #randomize proxy before sending
#             proxy = random.choice(proxies)
#             details = get_car_details(vin, set_cookies.cookies, proxy)
#             if details == "retry":
#                 print("Service Unavailable while getting details")
#             elif details is False:
#                 #add the vin to the invalid table
#                 print("invalid, adding to invalid table")
#                 invalid_vin = Invalid(vin)
#                 try:
#                     db.session.add(invalid_vin)
#                     db.session.commit()
#                 except:
#                     print("Unable to add item to database.")
#             else:
#                 #add the car to the cars table
#                 print("adding car to cars table")
#                 get_or_create_car(vin, year, details)
#     return "DONE!, CHECK THE DB"


def scrape_vin(vin):
    print("starting to scrape")

    proxies = [
        {'https': 'http://66.70.191.215:1080', 'http':'http://66.70.191.215:1080'},
        # {'https': 'http://104.41.154.213:8118', 'http': 'http://104.41.154.213:8118'},
        # {'https': 'http://54.204.31.39:4000', 'http': 'http://54.204.31.39:4000'},
        # {'https': 'http://45.32.161.20:1080', 'http': 'http://45.32.161.20:1080'},
        # {'https': 'http://162.243.55.213:8118', 'http': 'http://162.243.55.213:8118'},
        # {'https': 'http://209.212.248.53:80', 'http': 'http://209.212.248.53:80'},
        # {'https': 'http://209.212.253.18:1080', 'http': 'http://209.212.253.18:1080'},
        # {'https': 'http://103.11.67.192:3128', 'http': 'http://103.11.67.192:3128'},
        # {'https': 'http://191.96.227.75:62222', 'http': 'http://191.96.227.75:62222'}
    ]
    proxy = random.choice(proxies)
    print("trying with proxy", proxy)
    try:
        set_cookies = requests.get("http://www.etis.ford.com/vehicleSelection.do", proxies=proxy)
    except:
        return "cookie request error"
    time_of_cookie = time.time()
    print("got", len(vins), "vins")
    for vin in vins:
        print("checking", vin)
        is_invalid = db.session.query(Invalid).filter_by(vin=vin).first()
        db_check = db.session.query(Result).filter_by(vin=vin).first()
        now = time.time()
        if now-time_of_cookie > 600:
            print("getting new cookie")
            set_cookies = requests.get("https://www.etis.ford.com/vehicleSelection.do", proxies=proxy)
            time_of_cookie = time.time()
        if db_check is None and is_invalid is None:
            #randomize proxy before sending
            proxy = random.choice(proxies)
            details = get_car_details(vin, set_cookies.cookies, proxy)
            if details == "retry":
                print("Service Unavailable while getting details")
            elif details is False:
                #add the vin to the invalid table
                print("invalid, adding to invalid table")
                invalid_vin = Invalid(vin)
                try:
                    db.session.add(invalid_vin)
                    db.session.commit()
                except:
                    print("Unable to add item to database.")
            else:
                #add the car to the cars table
                print("adding car to cars table")
                get_or_create_car(vin, year, details)
    return "DONE!, CHECK THE DB"


def format_params(options):
    '''takes the raw input from the request as json and then
    formats it so that we can use it to construct the proper url'''
    options["color"] = []
    options["trim"] = []
    #change each color to array index
    for color in options["colors"]:
        if options["colors"][color]:
            options["color"].append(str(color))

    if len(options["color"]) is not 0:
        if len(options["color"]) > 1:
            #replace the array with the properly formatted query string
            temp = options["color"][0].upper()
            for i, color in enumerate(options["color"]):
                temp += "%2C"
                temp += options["color"][i].upper()
            options["color"] = temp
        else:
            options["color"] = options["color"][0].upper()
    if len(options["color"]) is 0:
        options["color"] = ""
    options.pop("colors", None)
    # change trims to array then replace it with formatted starting
    for trim in options["trims"]:
        options["trim"].append(trim)

    temp = "MUST%7C"
    if len(options["trim"]) > 1:
        temp += "%20".join(options["trim"][0].split(" "))
        temp += "%2CMUST%7C"
        temp += "%20".join(options["trim"][1].split(" "))
    else:
        temp += "%20".join(options["trim"][0].split(" "))
    options["trim"] = temp
    options.pop("trims", None)
    options["radius"] = str(options["radius"])
    options["zipcode"] = str(options["zipcode"])
    print("formatted options", options)
    return options

def get_or_create_car(vin, year, car):
    '''checks to see if the car exists in the db, if not, add it'''
    result = Result(vin, year, car["color"], car["build_date"], car["stripe"], car["electronics"], car["convenience"], car["painted_roof"])
    try:
        db.session.add(result)
        db.session.commit()
    except:
        print("Unable to add item to database.")

def check_vin(vin):
    '''check a single vin because it wasn't in the db'''
    proxy = {'http':'http://35.189.9.152:80'}
    set_cookies = requests.get("http://www.etis.ford.com/vehicleSelection.do", proxies=proxy)
    # print(set_cookies.headers)
    details = get_car_details(vin, set_cookies.cookies, proxy)
    if vin[9] == "G":
        year = 2016
    elif vin[9] == "H":
        year = 2017
    elif vin[9] == "J":
        year = 2018
    if details == "retry":
        print("Service Unavailable while getting details, retrying")
        check_vin(vin)
    elif details is False:
        #add the vin to the invalid table
        print("invalid, adding to invalid table")
        invalid_vin = Invalid(vin)
        try:
            db.session.add(invalid_vin)
            db.session.commit()
        except:
            print("Unable to add item to database.")
    else:
        #add the car to the cars table
        print("adding car to cars table")
        get_or_create_car(vin, year, details)

    return details


if __name__ == "__main__":
    app.run()
