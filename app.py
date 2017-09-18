import os
import time
import random
import copy
import requests
from sqlalchemy import or_
from flask import Flask, send_file, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from etis_scraper import *
from autotrader_scraper import *
app = Flask(__name__)
app.config.from_object(os.environ["APP_SETTINGS"])
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
# PROXIES = test_proxies(find_proxies())
from models import Result, Invalid, Autotrader

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/test')
def test():
    check_vin("1FA6P8JZ8H5520775")
    return "done"

@app.route('/api/search', methods=["POST"])
def search_cars():
    #take params and make it into a valid DB query.
    raw_params = request.get_json()
    #{'zipcode': 98036, 'radius': 500, 'minYear': '2017', 'maxYear': '2017', 'colors': {'Lightning Blue': True, 'Grabber Blue': True}, 'stripe': {'Black W/ White': True, 'None': True}, 'options': {}}
    # make a zipcode api req to get the valid zips in radius of input zips
    print(raw_params)
    formatted_params = db_query_format(raw_params)

    valid_zips = requests.get('https://www.zipcodeapi.com/rest/'+os.environ["ZIPCODE_API"]+'/radius.json/'+str(raw_params["zipcode"])+'/'+str(raw_params["radius"])+"/mile?minimal").json()
    zips = valid_zips["zip_codes"]
    # select * from cars inner join search_results on cars.vin = search_results.vin where params
    #DBSession().query(MyTable).filter(or_(*[MyTable.my_column.like(name) for name in foo]))

    db_result = db.session.query(Result,Autotrader).join(Autotrader, Result.vin == Autotrader.vin).\
        filter(Autotrader.zipcode.in_(zips)).\
        filter(Result.year >= raw_params['minYear']).\
        filter(Result.year <= raw_params['maxYear'])
    for filter_ in formatted_params:
        if filter_ == "color":
            db_result = db_result.filter(or_(*[Result.color == name for name in formatted_params[filter_]]))
        if filter_ == "stripe":
            db_result = db_result.filter(or_(*[Result.stripe.like(name +"%") for name in formatted_params[filter_]]))
        # if filter_ == "option":
    filtered_result = db_result.all()
    returned_zips = [str(raw_params["zipcode"])]
    for result in filtered_result:
        if result.Autotrader.zipcode not in returned_zips:
            returned_zips.append(result.Autotrader.zipcode)
    print(returned_zips)
    distance_query = ",".join(item for item in returned_zips)
    distances = requests.get('https://www.zipcodeapi.com/rest/'+os.environ["ZIPCODE_API"]+'/match-close.json/'+distance_query+'/'+str(raw_params['radius'])+'/mile').json()
    cars_matched = []
    valid_distances = {}
    valid_distances[str(raw_params["zipcode"])] = "0"
    for distance in distances:
        print(distance)
        if distance["zip_code1"] == str(raw_params["zipcode"]):
            valid_distances[distance["zip_code2"]] = distance["distance"]
        if distance["zip_code2"] == str(raw_params["zipcode"]):
            valid_distances[distance["zip_code1"]] = distance["distance"]
    print(valid_distances)

    for car in filtered_result:
        new_car = {}
        new_car["name"] = car.Autotrader.name
        new_car["url"] = car.Autotrader.url
        new_car["vin"] = car.Autotrader.vin
        new_car["dealer"] = car.Autotrader.dealer
        new_car["zipcode"] = car.Autotrader.zipcode
        new_car["address"] = car.Autotrader.address
        new_car["phone"] = car.Autotrader.phone
        new_car["price"] = car.Autotrader.price
        new_car["pic"] = car.Autotrader.pic
        new_car["year"] = car.Result.year
        new_car["color"] = car.Result.color
        new_car["stripe"] = car.Result.stripe
        new_car["electronics"] = car.Result.electronics
        new_car["convenience"] = car.Result.convenience
        new_car["build_date"] = car.Result.build_date
        if car.Autotrader.zipcode in valid_distances:
            new_car["distance"] = int(valid_distances[car.Autotrader.zipcode])
        else:
            print(car.Autotrader.zipcode, "not in valid_distances")
            new_car["distance"] = 0
        cars_matched.append(new_car)
    return jsonify(cars_matched), 200


def db_query_format(params):
    formatted = {}
    for param in params:
        if param == "colors":
            formatted["color"] = []
            for color in params[param]:
                if params[param][color]:
                    formatted["color"].append(color)
        if param == "stripe":
            formatted["stripe"] = []
            for stripe in params[param]:
                if params[param][stripe]:
                    if stripe == "None":
                        stripe = "false"
                    formatted["stripe"].append(stripe)
        if param == "options":
            formatted["option"] = []
            for option in params[param]:
                if params[param][option]:
                    formatted["option"].append(option)
    for item in list(formatted):
        if not formatted[item]:
            formatted.pop(item, None)


    return formatted

def search_autotrader():
    raw_params = request.get_json()
    # print(raw_params)
    filtering_params = copy.deepcopy(raw_params)
    formatted_params = format_params(raw_params)
    urls = []
    # distances = []
    #send these options to a function that scrapes autotrader with these params
    #TODO: Should check the DB and the scraper would just be constantly running
    urls = find_listings(formatted_params, urls)
    print("found",len(urls),"cars")
    # new_car = get_listing_details(urls[0], distances[0])
    # now send each url and distance to listing details scrape_year
    autotrader_cars = []
    for i, url in enumerate(urls):
        #search localdb for the car, if not there, then scrape it
        # print(url.split("=")[1])
        db_result = db.session.query(Autotrader).filter_by(listing=url.split("=")[1]).first()
        if db_result is None:
            print("Car not seen before, scraping car", i+1)
            #maybe send this to the redis worker?
            new_car = get_listing_details(urls[i])
            autotrader_cars.append(new_car)
            #write the car to the DB
            if "P8JZ" in new_car["vin"]:
                add_to_autotrader_db(new_car)
        else:
            #TODO: should check to see if the url is still a valid listing
            new_car = {}
            new_car["name"] = db_result.name
            new_car["url"] = db_result.url
            new_car["vin"] = db_result.vin
            new_car["dealer"] = db_result.dealer
            new_car["zipcode"] = db_result.zipcode
            new_car["address"] = db_result.address
            new_car["phone"] = db_result.phone
            new_car["price"] = db_result.price
            new_car["pic"] = db_result.pic
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
    print("sending matching cars")
    return jsonify(filtered_cars),200

def match_filters(car, params):
    # print("matching params", params)

    # print(car)
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
            # print("vin is for a GT350")
            db_result = db.session.query(Result).filter_by(vin=vin).first()
            if db_result is None:
                print("car was not in DB, fetching data for vin", vin)
                # #temp bypass
                # return False
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
            # print(options)

            return options
        else:
            print("vin is not a GT350")
            # car_to_delete = db.session.query(Autotrader).filter_by(vin=vin).first()
            # db.session.delete(car_to_delete)
            # db.session.commit()
            return False
    else:
        return False

def add_to_autotrader_db(car):
    #def __init__(self, price, name, url, vin, dealer, address, phone, listing):
    result = Autotrader(car['pic'], car["price"], car["name"], car["url"], car["vin"], car["dealer"], car["address"], car["phone"], car["listing"], car["zipcode"])
    try:
        db.session.add(result)
        db.session.commit()
    except:
        print("Unable to add item to database.")

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
