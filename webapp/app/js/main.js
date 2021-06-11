// This example adds a search box to a map, using the Google Place Autocomplete
// feature. People can enter geographical searches. The search box will return a
// pick list containing a mix of places and predicted search terms.
// This example requires the Places library. Include the libraries=places
// parameter when you first load the API. For example:
// <script src="https://maps.googleapis.com/maps/api/js?key=YOUR_API_KEY&libraries=places">

const input = document.getElementById("search");
const nyc = [-74.00820558171071, 40.71083794970947];
const honolulu = [-157.80347409796133, 21.325748892984794]

function setMyLocation() {
  if (location.protocol === 'https:' && navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(showPosition);
  } else {
    googleMap.setCenter(honolulu);
  }
}

function initGoogleMap() {
  googleMap = new GoogleMap();
  setMyLocation();

  // the Google Map is also the default map
  currentMap = googleMap;
}

class SNMap {
  getBounds() {
    throw new Error("not implemented")
  }

  getBoundsUrl() {
    let b = this.getBounds();
    return [b[3], b[0], b[1], b[2]].join(","); // assemble in google format w, s, e, n
  }

  setCenter() {
    throw new Error("not implemented")
  }

  getCenter() {
    let b = this.getBounds();
    return [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2];
  }

  getCenterUrl() {
    let c = this.getCenter();
    return c[0] + "," + c[1];
  }

  getZoom() {
    throw new Error("not implemented")
  }

  setZoom(z) {
    throw new Error("not implemented")
  }
  fitCenter() {
    throw new Error("not implemented")
  }

  search(place) {
    throw new Error("not implemented")
  }

  makeMapRect(o) {
    throw new Error("not implemented")
  }

  updateMapRect(o) {
    throw new Error("not implemented")
  }
}

class GoogleMap extends SNMap {
  constructor() {
    super();
    // make the map
    this.map = new google.maps.Map(document.getElementById("google-map"), {
      zoom: 21,
      mapTypeId: 'satellite',
      fullscreenControl: false,
      streetViewControl: false,
      scaleControl: true,
      maxZoom: 21,
      minZoom: 17,
      tilt: 0,
    });

    this.boundaries = [];
    // Create the search box and link it to the UI element.
    this.searchBox = new google.maps.places.SearchBox(input);

    // Bias the SearchBox results towards current map's viewport.
    this.map.addListener("bounds_changed", () => {
      this.searchBox.setBounds(this.map.getBounds());
    });

    this.markers = []

    // Listen for the event fired when the user selects a prediction and retrieve
    // more details for that place.
    this.searchBox.addListener("places_changed", () => {
        this.places = this.searchBox.getPlaces();

        if (this.places.length == 0) {
          return;
        }
        // Clear out the old markers.
        this.markers.forEach((marker) => {
          marker.setMap(null);
        });
        this.markers = [];
        // For each place, get the icon, name and location.
        this.bounds = new google.maps.LatLngBounds();
        this.places.forEach((place) => {
          if (!place.geometry || !place.geometry.location) {
            console.log("Returned place contains no geometry");
            return;
          }
          const icon = {
            url: place.icon,
            size: new google.maps.Size(71, 71),
            origin: new google.maps.Point(0, 0),
            anchor: new google.maps.Point(17, 34),
            scaledSize: new google.maps.Size(25, 25),
          };
          // Create a marker for each place.
          this.markers.push(
            new google.maps.Marker({
              map: this.map,
              icon,
              title: place.name,
              position: place.geometry.location,
            })
          );

          if (place.geometry.viewport) {
            // Only geocodes have viewport.
            this.bounds.union(place.geometry.viewport);
          } else {
            this.bounds.extend(place.geometry.location);
          }
        });
        this.map.fitBounds(this.bounds);
      });

  }
  setCenter(c) {
    this.map.setCenter({ lat: c[1], lng: c[0] });
    //this.map.setZoom(19);
  }
  getBounds() {
    let bounds = this.map.getBounds();
    let ne = bounds.getNorthEast();
    let sw = bounds.getSouthWest();
    return [sw.lng(), ne.lat(), ne.lng(), sw.lat()];
  }
}

function getObjects(type) {
  //let center = currentMap.getCenterUrl();
  $("#load-spinner").show()
  // now get the boundaries ready to ship
  let bounds = currentMap.getBoundsUrl();

  // first, play the request, but get an estimate of the number of tiles
  const formData = new FormData();
  formData.append('bounds', bounds);
  formData.append('type', type);
  formData.append('height', currentMap.map.getDiv().offsetHeight);
  formData.append('width', currentMap.map.getDiv().offsetWidth);
  formData.append('zoom', currentMap.map.getZoom());
  fetch("/getobjects",  { method: "POST", body: formData, })
    .then(result => result.text())
    .then(data => {
        if (type == 'classification') {
            for (tile of JSON.parse(data)) {
                let myLatLng = {lat:tile["lat"], lng:tile["lng"]};
                if (tile["prediction"][0]==1) {
                    marker = new google.maps.Marker({
                      position: myLatLng,
                      map: currentMap.map
                    });
                }
            };
            $("#results").replaceWith("Classification completed.");
        };
        if (type == 'segmentation') {
            for (tile of JSON.parse(data)) {
                let imageBounds = {north: tile["bounds"][2], south: tile["bounds"][0], east: tile["bounds"][3], west: tile["bounds"][1]};
                console.log(imageBounds);
                spOverlay = new google.maps.GroundOverlay(
                   "http://localhost:5000" + tile["url"],
                   imageBounds
                );
                spOverlay.setMap(currentMap.map)
                spOverlay.setOpacity(0.5)
            };
            $("#results").replaceWith("Segmentation completed.");
        };
        if (type == 'tiles') {
            $("#results").replaceWith(data);
        }
        $("#load-spinner").hide()
    })

}
