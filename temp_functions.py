'''place to hold all the functions made to test the scraping'''



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
