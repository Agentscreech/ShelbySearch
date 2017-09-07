import os
import time
import random
import copy
from flask import Flask, send_file, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from etis_scraper import *
from autotrader_scraper import *
app = Flask(__name__)
app.config.from_object(os.environ["APP_SETTINGS"])
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
# PROXIES = test_proxies(find_proxies())
from models import Result, Invalid

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/test')
def test():
    check_vin("1FA6P8JZ8H5520775")
    return "done"

@app.route('/api/search', methods=["POST"])
def search_autotrader():
    raw_params = request.get_json()
    print(raw_params)
    filtering_params = copy.deepcopy(raw_params)
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
    print("getting build options")
    filtered_cars = []
    for car in autotrader_cars:
        if car["vin"] is not None:
            build_options = get_car_build_options(car["vin"])
        if build_options:
            for option in build_options:
                car[option] = build_options[option]
            if match_filters(car, filtering_params):
                print("car matched all params")
                filtered_cars.append(car)
        #now filter based on options in params
    return jsonify(filtered_cars),200

def match_filters(car, params):
    print("matching params", params)

    print(car)
    matched = {}
    #filter for color
    if params["colors"]:
        matched["color"] = False
        tripped = 0
        for color in list(params["colors"]):
            if params["colors"][color] is False:
                continue
            if color:
                tripped = 1
                if car["color"]:
                    if car["color"].split(" ")[0] in color:
                        matched['color'] = True
        if tripped == 0:
            matched['color'] = True
    #filter for stripes
    if params["stripe"]:
        matched["stripe"] = False
        tripped = 0
        for stripe in list(params["stripe"]):
            if params["stripe"][stripe] is False:
                continue
            if car["stripe"]:
                tripped = 1
                if car["stripe"].split(' ')[0] == stripe.split(' ')[0]:
                    matched["stripe"] = True
            else:
                if stripe == "None":
                    matched["stripe"] = True
        if tripped == 0:
            matched["stripe"] = True

    #filter for Electronics or Convenience Package
    if params["options"]:
        matched["options"] = False
        for option in list(params["options"]):
            if params["options"][option] is False:
                continue
            if "electronics" in option.lower() and car["electronics"]:
                matched["options"] = True
            elif "convenience" in option.lower() and car["convenience"]:
                matched["options"] = True

    #remove the car if any value in matched is False
    for key in matched:
        # print(key, matched[key])
        if not matched[key]:
            return False
    return True




# @app.route("/add_<year>")

def get_car_build_options(vin):
    '''query db and set results to object to return'''
    if validate_vin(vin):
        if "P8JZ" in vin:
            print("vin is for a GT350")
            db_result = db.session.query(Result).filter_by(vin=vin).first()
            if db_result is None:
                print("car was not in DB, fetching data for vin", vin)
                options = check_vin(vin)
                if options:
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
            print(options)

            return options
        else:
            print("vin is not a GT350")
            return False
    else:
        return False



def format_params(options):
    '''takes the raw input from the request as json and then
    formats it so that we can use it to construct the proper url'''
    options["color"] = []
    options["trim"] = []
    #change each color (2nd word) to array index
    for color in options["colors"]:
        if options["colors"][color]:
            options["color"].append(str(color.split(" ")[1]))

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
    # for trim in options["trims"]:
    #     options["trim"].append(trim)
    #
    # temp = "MUST%7C"
    # if len(options["trim"]) > 1:
    #     temp += "%20".join(options["trim"][0].split(" "))
    #     temp += "%2CMUST%7C"
    #     temp += "%20".join(options["trim"][1].split(" "))
    # else:
    #     temp += "%20".join(options["trim"][0].split(" "))
    options["trim"] = "MUST%7CShelby%20GT350R%2CMUST%7CShelby%20GT350"
    options.pop("trims", None)
    options["radius"] = str(options["radius"])
    options["zipcode"] = str(options["zipcode"])
    print("formatted options", options)
    return options

def get_or_create_car(vin, year, car):
    '''checks to see if the car exists in the db, if not, add it'''
    result = Result(vin, year, car["color"], car["build_date"], car["stripe"], car["electronics"], car["convenience"])
    try:
        db.session.add(result)
        db.session.commit()
    except:
        print("Unable to add item to database.")

def check_vin(vin):
    '''check a single vin because it wasn't in the db'''
    # for proxy in PROXIES:
    #     print("trying proxy", proxy)
    set_cookies = requests.get("http://www.etis.ford.com/vehicleSelection.do")
    # print('status code for cookies', set_cookies.status_code)
    if set_cookies.status_code == 200:
        details = get_car_details(vin, set_cookies.cookies)
        if details == "Server Error":
            return False
    if details == "retry":
        print("Service Unavailable while getting details, retrying")
    if vin[9] == "G":
        year = 2016
    elif vin[9] == "H":
        year = 2017
    elif vin[9] == "J":
        year = 2018
    # elif details is False:
    #     #add the vin to the invalid table
    #     print("invalid, adding to invalid table")
    #     invalid_vin = Invalid(vin)
    #     try:
    #         db.session.add(invalid_vin)
    #         db.session.commit()
    #     except:
    #         print("Unable to add item to database.")
    if details:
        #add the car to the cars table
        print("adding car to cars table")
        get_or_create_car(vin, year, details)

    return details

def validate_vin(field):
    """
    Validate a VIN against the 9th position checksum
    See: http://en.wikipedia.org/wiki/Vehicle_Identification_Number#Check_digit_calculation
    Test VINs:
        1M8GDM9AXKP042788
        11111111111111111
    """
    POSITIONAL_WEIGHTS = [8,7,6,5,4,3,2,10,0,9,8,7,6,5,4,3,2]
    ILLEGAL_ALL = ['I', 'O', 'Q']
    ILLEGAL_TENTH = ['U','Z','0']
    LETTER_KEY = dict(
        A=1,B=2,C=3,D=4,E=5,F=6,G=7,H=8,
        J=1,K=2,L=3,M=4,N=5,    P=7,    R=9,
            S=2,T=3,U=4,V=5,W=6,X=7,Y=8,Z=9,
    )

    if len(field) == 17:
        vin = field.upper()

        for char in ILLEGAL_ALL:
            if char in vin:
                raise ValidationError('Field cannot contain "I", "O", or "Q".')

        if vin[9] in ILLEGAL_TENTH:
            raise ValidationError('Field cannot contain "U", "Z", or "0" in position 10.')

        check_digit = vin[8]

        pos=total=0
        for char in vin:
            value = int(LETTER_KEY[char]) if char in LETTER_KEY else int(char)
            weight = POSITIONAL_WEIGHTS[pos]
            total += (value * weight)
            pos += 1

        calc_check_digit = int(total) % 11

        if calc_check_digit == 10:
            calc_check_digit = 'X'

        if str(check_digit) != str(calc_check_digit):
            return False
    else:
        return False
    return True

if __name__ == "__main__":
    app.run()
