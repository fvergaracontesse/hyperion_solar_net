// This example adds a search box to a map, using the Google Place Autocomplete
// feature. People can enter geographical searches. The search box will return a
// pick list containing a mix of places and predicted search terms.
// This example requires the Places library. Include the libraries=places
// parameter when you first load the API. For example:
// <script src="https://maps.googleapis.com/maps/api/js?key=YOUR_API_KEY&libraries=places">

const input = document.getElementById("search");
const nyc = [-74.00820558171071, 40.71083794970947];
const honolulu = [-157.80347409796133, 21.325748892984794];
var map_modified = 0;

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

  currentMap.map.addListener("center_changed", () => {
    map_modified = 1;
  });
  currentMap.map.addListener("zoom_changed", () => {
    map_modified = 1;
  });

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
      zoom: 20,
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

    this.predictions_markers = []
    this.predictions_rectangles = [];
    this.predictions_overlays = [];
    this.markers = [];


    // Listen for the event fired when the user selects a prediction and retrieve
    // more details for that place.
    this.searchBox.addListener("places_changed", () => {
        this.places = this.searchBox.getPlaces();

        if (this.places.length == 0) {
          return;
        }
        map_modified = 1;
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
  removeOverlays(){
      while(this.predictions_markers[0]){
          this.predictions_markers.pop().setMap(null);
      }
      while(this.predictions_rectangles[0]){
          this.predictions_rectangles.pop().setMap(null);
      }
      while(this.predictions_overlays[0]){
          this.predictions_overlays.pop().setMap(null);
      }
  }
}

function removeOverlays() {
    map_modified = 0;
    currentMap.removeOverlays();
}

function getObjects(type) {
  //let center = currentMap.getCenterUrl();
  if (map_modified==1){
      map_modified = 0;
      currentMap.removeOverlays();
  }
  $('#load-spinner').show();
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
        if (type == 'tiles') {
            for (tile of JSON.parse(data)) {
                let bounds = {north: tile["bounds"][2], south: tile["bounds"][0], east: tile["bounds"][3], west: tile["bounds"][1]};
                const rectangle = new google.maps.Rectangle({
                    strokeColor: "#FF0000",
                    strokeOpacity: 0.8,
                    strokeWeight: 2,
                    fillOpacity: 0.0,
                    map: currentMap.map,
                    bounds: bounds
              });
              currentMap.predictions_rectangles.push(rectangle);
              $('#table-results').bootstrapTable('destroy').bootstrapTable({
                columns: [{
                        field: 'id',
                        title: 'id',
                        visible:true
                    },
                    {
                        field: 'lat',
                        title: 'Latitude',
                        visible:true
                    },
                    {
                        field: 'lng',
                        title: 'Longitude',
                        visible:true
                    }],
                data: JSON.parse(data)
            });
              $('.loading-wrap').hide();
            };
            //$("#results").replaceWith("Number of tiles:" + Object.keys(JSON.parse(data)).length);
        }
        if (type == 'classification') {
            for (tile of JSON.parse(data)) {
                let myLatLng = {lat:tile["lat"], lng:tile["lng"]};
                if (tile["prediction"]==1) {
                    let bounds = {north: tile["bounds"][2], south: tile["bounds"][0], east: tile["bounds"][3], west: tile["bounds"][1]};
                    const rectangle = new google.maps.Rectangle({
                        strokeColor: "#FF0000",
                        strokeOpacity: 0.8,
                        strokeWeight: 2,
                        fillColor: "#FF0000",
                        fillOpacity: 0,
                        map: currentMap.map,
                        bounds: bounds
                    });
                    currentMap.predictions_rectangles.push(rectangle)
                    marker = new google.maps.Marker({
                      position: myLatLng,
                      map: currentMap.map
                    });
                    currentMap.predictions_markers.push(marker);
                }
                $('#table-results').bootstrapTable('destroy').bootstrapTable({
                  columns: [{
                          field: 'id',
                          title: 'id',
                          visible:true
                      },
                      {
                          field: 'lat',
                          title: 'Latitude',
                          visible:true
                      },
                      {
                          field: 'lng',
                          title: 'Longitude',
                          visible:true
                      },
                      {
                          field: 'prediction',
                          title: 'Prediction',
                          visible:true
                      }],
                  data: JSON.parse(data)
              });
                $('.loading-wrap').hide();
            };
        };
        if (type == 'segmentation') {
            for (tile of JSON.parse(data)) {
                let imageBounds = {north: tile["bounds"][2], south: tile["bounds"][0], east: tile["bounds"][3], west: tile["bounds"][1]};
                const rectangle = new google.maps.Rectangle({
                  strokeColor: "#00FF00",
                  strokeOpacity: 0.8,
                  strokeWeight: 2,
                  fillOpacity: 0.0,
                  map: currentMap.map,
                  bounds: imageBounds
                });
                currentMap.predictions_rectangles.push(rectangle);
                console.log(tile["url"])
                spOverlay = new google.maps.GroundOverlay(
                   tile["url"],
                   imageBounds
                );
                spOverlay.setMap(currentMap.map);
                spOverlay.setOpacity(0.2);
                currentMap.predictions_overlays.push(spOverlay);
            };
            $('#table-results').bootstrapTable('destroy').bootstrapTable({
              columns: [{
                      field: 'id',
                      title: 'id',
                      visible:true
                  },
                  {
                      field: 'lat',
                      title: 'Latitude',
                      visible:true
                  },
                  {
                      field: 'lng',
                      title: 'Longitude',
                      visible:true
                  },
                  {
                      field: 'panels_area',
                      title: 'Area (sqft)',
                      visible:true
                  },
                  {
                      field: 'panels_count',
                      title: 'Count',
                      visible:true
                  }],
              data: JSON.parse(data)
          });
            $('.loading-wrap').hide();
        };
        $('#load-spinner').hide();
    })

}
