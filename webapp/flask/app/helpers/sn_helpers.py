"""Additional helper functions."""
from shapely.geometry import Polygon
import json
import boto3
import pickle
import hashlib
import hmac
import base64
import urllib.parse as urlparse
from PIL import Image
import numpy as np


def check_tile_center_against_bounds(t, bounds):
    """Check if tile is within bounds."""
    SWlat, SWlng, NElat, NElng = bounds
    lat_in = SWlat <= t["lat"] <= NElat or SWlat >= t["lat"] >= NElat
    lon_in = SWlng <= t["lng"] <= NElng or SWlng >= t["lng"] >= NElng
    return True if lat_in and lon_in else False


def get_json_file_from_s3(path):
    """Get a json file from S3."""
    s3client = boto3.client(
        's3'
    )
    bucketname = "solarnet-data"
    file_to_read = path
    fileobj = s3client.get_object(
        Bucket=bucketname,
        Key=file_to_read
    )
    filedata = fileobj['Body'].read()
    contents = filedata.decode('utf-8')
    return json.loads(contents)


def get_image_from_s3(path):
    """Get images from s3."""
    s3client = boto3.client(
        's3'
    )
    bucketname = "solarnet-data"
    file_to_read = path
    fileobj = s3client.get_object(
        Bucket=bucketname,
        Key=file_to_read
    )
    # img = load_img(io.BytesIO(fileobj['Body'].read()))
    img = Image.open(fileobj['Body'])
    return img


def get_image_stream_from_s3(path):
    """Get image stream from s3."""
    s3client = boto3.client(
        's3'
    )
    bucketname = "solarnet-data"
    file_to_read = path
    fileobj = s3client.get_object(
        Bucket=bucketname,
        Key=file_to_read
    )
    # img = load_img(io.BytesIO(fileobj['Body'].read()))
    return fileobj['Body'].read()


def get_state_tiles(place_json, map_object, activate=True):
    """Get tiles based on a geojson file within a region."""
    if activate is True:
        '''
        :type activate: boolean
        :rtype tiles_poly: int
        Function input is a boolean to activate the function. The function will
        read a GeoJSON file with lat/long coordinates for city or state.
        Shapely package is used to create state polygon and outer bounds. All
        the tiles within the square bounds are created using the outer bounds
        and make_tiles function. If the tile intersects the state polygon, append
        to the list of tiles within the state polygon. Return the tiles_poly
        '''

        # maps are downloaded from https://maps.princeton.edu/
        # exported maps must be in GeoJSON format
        # read json file of state lat/long [revise the path to json file]

        # get the coordinates in nested array
        lat_long_coord = place_json['features'][0]['geometry']['coordinates']

        # break down the nested array
        [[unnest_coord]] = lat_long_coord

        # convert nested lists into tuples
        place_coord = [tuple(ele) for ele in unnest_coord]

        # use shapely to get the city/state polygon
        place_poly = Polygon(place_coord)

        print("PLACE POLY", place_poly.bounds)

        # finds the bounds (minx, miny, maxx, maxy) of city/state polygon
        place_bounds_str = str(place_poly.bounds)
        place_bounds_rep = place_bounds_str.replace("(", "")
        place_bounds = place_bounds_rep.replace(")", "")

        # print("PLACE BOUNDS", place_bounds)

        # use make_tiles to get all tiles within state bounds
        tiles_square, nx, ny, meters, h, w = map_object.make_tiles(place_poly.bounds, crop_tiles=False, normal=False)

        # determine if the individual tile is within the state polygon
        # declare tiles_poly
        tiles_poly = []

        for tile in tiles_square:
            # create the coordinates of the tile boundary
            west = (tile['lat'] - (tile['w']/2))
            east = (tile['lat'] + (tile['w']/2))
            north = (tile['lng'] + (tile['h']/2))
            south = (tile['lng'] - (tile['h']/2))
            # create the boundary coordinates of the tile
            check_tile = Polygon([(south, east), (south, west), (north, west), (north, east)])

            # check if the tile intersects with the state_polygon. If true, append tile information to tiles_poly
            if check_tile.intersects(place_poly) is True:
                tiles_poly.append(tile)

    return tiles_poly, place_poly, place_bounds


def save_pickle_file(filename, data):
    """Save to pickle file."""
    dbfile = open(filename, 'ab')
    pickle.dump(data, dbfile)
    dbfile.close()
    return data


def load_pickle_file(filename):
    """Load a pickle file."""
    dbfile = open(filename, 'rb')
    data = pickle.load(dbfile)
    dbfile.close()
    return data


def upload_file(file_name, bucket, content):
    """Upload a file to an S3 bucket.

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """
    # If S3 object_name was not specified, use file_name
    object_name = file_name

    # Upload the file
    s3_client = boto3.resource('s3')
    response = s3_client.Object(bucket, object_name).put(Body=content)
    return response


def chunks(l, n):
    """Iterador para generar batches.

    :Args
        l: list de lineas.
        n: tamaño del iterable.

    :Returns
        Iterador separado por batches.
    """
    for i in range(0, len(l), n):
        yield l[i:i + n]


# This function is obtained from GOOGLE MAP API.
def sign_url(input_url=None, secret=None):
    """Sign a request URL with a URL signing secret.

    :Usage
        from urlsigner import sign_url
        signed_url = sign_url(input_url=my_url, secret=SECRET)
    :Args
        input_url - The URL to sign
        secret    - Your URL signing secret
    :Returns
        The signed request URL
    """
    if not input_url or not secret:
        raise Exception("Both input_url and secret are required")

    url = urlparse.urlparse(input_url)

    # We only need to sign the path+query part of the string
    url_to_sign = url.path + "?" + url.query

    # Decode the private key into its binary format
    # We need to decode the URL-encoded private key
    decoded_key = base64.urlsafe_b64decode(secret)

    # Create a signature using the private key and the URL-encoded
    # string using HMAC SHA1. This signature will be binary.
    signature = hmac.new(decoded_key, str.encode(url_to_sign), hashlib.sha1)

    # Encode the binary signature into base64 for use within a URL
    encoded_signature = base64.urlsafe_b64encode(signature.digest())

    original_url = url.scheme + "://" + url.netloc + url.path + "?" + url.query

    # Return signed URL
    return original_url + "&signature=" + encoded_signature.decode()


def sigmoid(x):
    """Return sigmoid."""
    return 1 / (1 + np.exp(-x))
