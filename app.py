import os
import time
import random
from flask import Flask, send_file, render_template, request
from flask_sqlalchemy import SQLAlchemy
from car_scraper import *
app = Flask(__name__)
app.config.from_object(os.environ["APP_SETTINGS"])
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

from models import Result, Invalid

@app.route('/')
def index():
    return render_template("index.html")


@app.route('/api/search', methods=["POST"])
def search_autotrader():
    raw_options = request.get_json()
    print(raw_options)
    formatted_options = set_options(raw_options)
    return "got it"








    return "got it"

@app.route("/add_<year>")
def scrape_year(year):
    print("starting to scrape", int(year))
    vins = generate_2017gt350_vins()
    print("vins generated")
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
        set_cookies = requests.get("https://www.etis.ford.com/vehicleSelection.do", proxies=proxy)
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

def set_options(options):
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

    # change trims to array then replace it with formatted starting
    for trim in options["trims"]:
        options["trim"].append(trim)

    temp = "MUST&7C"
    if len(options["trim"]) > 1:
        temp += "%20".join(options["trim"][0].split(" "))
        temp += "%2CMUST%7C"
        temp += "%20".join(options["trim"][1].split(" "))
    else:
        temp += "%20".join(options["trim"][0].split(" "))
    options["trim"] = temp
    print("formatted options", options)
    return options

def get_or_create_car(vin, year, car):
    '''checks to see if the car exists in the db, if not, add it'''
    result = Result(vin, year, car["Color"], car["Build Date"], car["Over the Top Racing Stripe"], car["Electronics Package"], car["Convenience Package"], car["Painted Black Roof"])
    try:
        db.session.add(result)
        db.session.commit()
    except:
        print("Unable to add item to database.")

def check_vin(vin):
    '''check a single vin because it wasn't in the db'''
    proxy = {'https': 'http://66.70.191.215:1080', 'http':'http://66.70.191.215:1080'}
    set_cookies = requests.get("https://www.etis.ford.com/vehicleSelection.do", proxies=proxy)
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

    return "DONE!!"


if __name__ == "__main__":
    app.run()
