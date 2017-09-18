angular.module('App')
    .component('homeComp', {
        templateUrl: "static/app/containers/home/home.html",
        controller: HomeCompCtrl,
        controllerAs: 'homeComp'
    });

function HomeCompCtrl($scope, $window, CarList, $sce) {
    var homeComp = this;
    homeComp.cars = "";
    homeComp.colors = ["Avalanche", "Competition Orange", "Deep Impact Blue (Metallic)",  "Shadow Black (Mica)", "Grabber Blue", "Lightning Blue (Metallic)", "Magnetic", "Race Red", "Ruby Red (Metallic)", "Oxford White", "Triple Yellow Tricoat"];
    homeComp.years = ["2016", "2017", "2018"];
    // homeComp.trims = ["Shelby GT350", "Shelby GT350R"];
    homeComp.stripes = ["None","Black W/ White", "White W/ Black", "Blue W/ Black"]
    homeComp.options = ["Electronics Package", "Convenience Package", "None"]
    homeComp.zipcode = "";
    homeComp.radius = "";
    homeComp.minYear = "";
    homeComp.maxYear = "";
    // homeComp.trim = {};
    homeComp.color = {};
    homeComp.stripe = {};
    homeComp.option = {};
    homeComp.processing = false;
    // $scope.$watch('homeComp.cars',function(newVal, oldVal){
    //     console.log("homeComp.cars changed.  It's ", newVal)
    // });
    //get a list of the cars
    homeComp.searchCars = function() {
        homeComp.processing = true;
        var params = {
            zipcode : homeComp.zipcode,
            radius : homeComp.radius,
            minYear : homeComp.minYear,
            maxYear : homeComp.maxYear,
            // trims : homeComp.trim,
            colors : homeComp.color,
            stripe : homeComp.stripe,
            options : homeComp.option,
        }
        CarList.getCars(params).then(function(res) {
            //rank cars by price and distance
            homeComp.cars = rankCars(res);
            homeComp.cars.forEach(function(car) {
                car.pdf = $sce.trustAsResourceUrl("http://www.windowsticker.forddirect.com/windowsticker.pdf?vin=" + car.vin);
                car.showPdf = false;
            });
            homeComp.processing = false
        });
    }
}
//sorting helper
function rankCars(cars) {
    // cars = cars.filter(function(car) {
    //     return car.archived == false;
    // });
    //Add the distance @ $1/mile to the price then sort it.  That would weight the distance more since you'll have pay to travel to the location.
    var carsByPrice = cars.slice(0).sort(function(a, b) {
            if (!a.price){
                a.price = ""
            }
            if (!b.price){
                b.price = ""
            }
            var arr1 = a.price.split("$"),
            arr2 = b.price.split("$");
            var weight1 = a.distance,
            weight2 = b.distance
            if (arr1 == "") {
                arr1 = ["", "999,999"]
            }
            if (arr2 == "") {
                arr2 = ["", "999,999"]
            }
        return parseInt(arr1[1].split(",").join("")) + weight1 > parseInt(arr2[1].split(",").join("")) + weight2 ? 1 : parseInt(arr1[1].split(",").join("")) + weight1 < parseInt(arr2[1].split(",").join("")) + weight2 ? -1 : 0;

    });
    return carsByPrice
}

HomeCompCtrl.$inject = ['$scope', '$window', 'CarList', '$sce'];
