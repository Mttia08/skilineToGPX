from flask import Flask, render_template, jsonify, request, Response

from flask_httpauth import HTTPBasicAuth

from flask_cors import CORS

from werkzeug.security import generate_password_hash, check_password_hash

import requests

import json
import os

import osm2geojson

import networkx as nx

import haversine


from datetime import datetime, timedelta

import zoneinfo





# GitHub-backed persistent storage (configure these in Vercel Environment Variables):
# GITHUB_TOKEN: fine-grained token with Contents: Read and write on this repository
# GITHUB_REPOSITORY: "owner/repository"
# GITHUB_BRANCH: optional, defaults to "main"
GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")


class GitHubStorageError(RuntimeError):
    pass


def _github_headers():
    if not GITHUB_TOKEN or not GITHUB_REPOSITORY:
        raise GitHubStorageError(
            "GitHub storage is not configured. Set GITHUB_TOKEN and GITHUB_REPOSITORY."
        )
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def github_read_bytes(path):
    """Read a repository file's raw bytes through the GitHub Contents API."""
    from urllib.parse import quote
    url = f"{GITHUB_API}/repos/{GITHUB_REPOSITORY}/contents/{quote(path, safe='/')}"
    response = requests.get(
        url, headers={**_github_headers(), "Accept": "application/vnd.github.raw+json"},
        params={"ref": GITHUB_BRANCH}, timeout=20
    )
    if response.status_code == 404:
        raise FileNotFoundError(path)
    if not response.ok:
        raise GitHubStorageError(f"GitHub read failed ({response.status_code}): {response.text[:300]}")
    return response.content


def github_read_json(path):
    return json.loads(github_read_bytes(path).decode("utf-8"))


def github_write_bytes(path, content, message):
    """Create/update a repository file; GitHub requires the current file SHA for updates."""
    import base64
    from urllib.parse import quote
    url = f"{GITHUB_API}/repos/{GITHUB_REPOSITORY}/contents/{quote(path, safe='/')}"
    headers = _github_headers()
    existing = requests.get(
        url, headers=headers, params={"ref": GITHUB_BRANCH}, timeout=20
    )
    if existing.status_code not in (200, 404):
        raise GitHubStorageError(f"GitHub lookup failed ({existing.status_code}): {existing.text[:300]}")
    payload = {
        "message": message,
        "content": base64.b64encode(content).decode("ascii"),
        "branch": GITHUB_BRANCH,
    }
    if existing.status_code == 200:
        payload["sha"] = existing.json()["sha"]
    response = requests.put(url, headers=headers, json=payload, timeout=30)
    if not response.ok:
        raise GitHubStorageError(f"GitHub write failed ({response.status_code}): {response.text[:300]}")
    return response.json()


def github_write_json(path, data, message):
    raw = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    github_write_bytes(path, raw, message)


def load_lift_errors():
    try:
        errors = github_read_json("lift_errors.json")
    except FileNotFoundError:
        errors = {"lifts": {}, "resorts": []}
    errors.setdefault("lifts", {})
    errors.setdefault("resorts", [])
    return errors


def save_lift_errors(errors, message="Update lift error log"):
    github_write_json("lift_errors.json", errors, message)


def valid_resort_id(value):
    # Prevent path traversal and malformed GitHub repository paths.
    return bool(value) and all(part.isalnum() or part in "-_" for part in value)




# GitHub-backed persistent storage (configure these in Vercel Environment Variables):
# GITHUB_TOKEN: fine-grained token with Contents: Read and write on this repository
# GITHUB_REPOSITORY: "owner/repository"
# GITHUB_BRANCH: optional, defaults to "main"
GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")


class GitHubStorageError(RuntimeError):
    pass


def _github_headers():
    if not GITHUB_TOKEN or not GITHUB_REPOSITORY:
        raise GitHubStorageError(
            "GitHub storage is not configured. Set GITHUB_TOKEN and GITHUB_REPOSITORY."
        )
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def github_read_bytes(path):
    """Read a repository file's raw bytes through the GitHub Contents API."""
    from urllib.parse import quote
    url = f"{GITHUB_API}/repos/{GITHUB_REPOSITORY}/contents/{quote(path, safe='/')}"
    response = requests.get(
        url, headers={**_github_headers(), "Accept": "application/vnd.github.raw+json"},
        params={"ref": GITHUB_BRANCH}, timeout=20
    )
    if response.status_code == 404:
        raise FileNotFoundError(path)
    if not response.ok:
        raise GitHubStorageError(f"GitHub read failed ({response.status_code}): {response.text[:300]}")
    return response.content


def github_read_json(path):
    return json.loads(github_read_bytes(path).decode("utf-8"))


def github_write_bytes(path, content, message):
    """Create/update a repository file; GitHub requires the current file SHA for updates."""
    import base64
    from urllib.parse import quote
    url = f"{GITHUB_API}/repos/{GITHUB_REPOSITORY}/contents/{quote(path, safe='/')}"
    headers = _github_headers()
    existing = requests.get(
        url, headers=headers, params={"ref": GITHUB_BRANCH}, timeout=20
    )
    if existing.status_code not in (200, 404):
        raise GitHubStorageError(f"GitHub lookup failed ({existing.status_code}): {existing.text[:300]}")
    payload = {
        "message": message,
        "content": base64.b64encode(content).decode("ascii"),
        "branch": GITHUB_BRANCH,
    }
    if existing.status_code == 200:
        payload["sha"] = existing.json()["sha"]
    response = requests.put(url, headers=headers, json=payload, timeout=30)
    if not response.ok:
        raise GitHubStorageError(f"GitHub write failed ({response.status_code}): {response.text[:300]}")
    return response.json()


def github_write_json(path, data, message):
    raw = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    github_write_bytes(path, raw, message)


def load_lift_errors():
    try:
        errors = github_read_json("lift_errors.json")
    except FileNotFoundError:
        errors = {"lifts": {}, "resorts": []}
    errors.setdefault("lifts", {})
    errors.setdefault("resorts", [])
    return errors


def save_lift_errors(errors, message="Update lift error log"):
    github_write_json("lift_errors.json", errors, message)


def valid_resort_id(value):
    # Prevent path traversal and malformed GitHub repository paths.
    return bool(value) and all(part.isalnum() or part in "-_" for part in value)


app = Flask(__name__)

auth = HTTPBasicAuth()



CORS(app, origins=["https://app.skiline.cc"])



# Set ADMIN_PASSWORD in Vercel; no insecure default password.
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
USERS = {"admin": generate_password_hash(ADMIN_PASSWORD)} if ADMIN_PASSWORD else {}



OVERPASS_URL = "https://overpass-api.de/api/interpreter"



# GPX namespace

GPX_NS = "http://www.topografix.com/GPX/1/1"



@auth.verify_password

def verify_password(username, password):

    if username in USERS and check_password_hash(USERS.get(username), password):

        return username

    return None



@app.route('/')

@auth.login_required

def add_resorts():

    return render_template("index.html")



@app.route("/get_bbox_data", methods=["GET"])

def get_bbox_data():

    required_params = ["south", "west", "north", "east"]



    if not all(param in request.args for param in required_params):

        return jsonify({

            "error": "Missing required bbox parameters",

            "required": required_params

        }), 400



    south = request.args["south"]

    west = request.args["west"]

    north = request.args["north"]

    east = request.args["east"]



    bbox = f"{south},{west},{north},{east}"



    overpass_query = f"""

    [out:json][timeout:25];

    (

      way[aerialway]["aerialway"!="goods"]({bbox});

      node[aerialway]["aerialway"!="goods"]({bbox});

      way["piste:type"="downhill"]({bbox});

      relation["piste:type"="downhill"]({bbox});

    );

    out body;

    >;

    out skel qt;

    """



    try:

        response = requests.post(

            OVERPASS_URL,

            data={"data": overpass_query},

            headers={

                "User-Agent": "SkilineStravaConverter/1.0 (contact: mattia08@bluewin.ch)",

                "Accept": "application/json"

            },

            timeout=35

        )



        response.raise_for_status()



        osm_data = response.json()



        geojson = osm2geojson.json2geojson(osm_data)



        return jsonify(geojson), 200



    except requests.exceptions.RequestException as e:

        app.logger.exception("Overpass request failed")

        return jsonify({

            "error": "Failed to fetch data from Overpass",

            "details": str(e)

        }), 502



    except Exception as e:

        app.logger.exception("GeoJSON conversion failed")

        return jsonify({

            "error": "Failed to convert OSM data to GeoJSON",

            "details": str(e)

        }), 500



def build_graph(json_data):

    G = nx.DiGraph()



    # Adding runs to graph

    for track in json_data["resortRuns"]:

        for i in range(len(track) - 1):

            G.add_edge(tuple(track[i]), tuple(track[i+1]), weight=haversine.haversine(track[i], track[i+1], unit=haversine.Unit.METERS))



    run_coords_list = list(G.nodes)



    sinks = [node for node, out_degree in G.out_degree() if out_degree == 0]

    sources = [node for node, in_degree in G.in_degree() if in_degree == 0]



    lift_starts = []

    lift_ends = []



    # Adding lifts to graph

    for name, track in json_data["resortLifts"].items():

        lift_starts.append(tuple(track[0]))

        lift_ends.append(tuple(track[-1]))

        for i in range(len(track) - 1):

            G.add_edge(tuple(track[i]), tuple(track[i+1]), weight=haversine.haversine(track[i], track[i+1], unit=haversine.Unit.METERS))



    for lift_start in lift_starts:

        closest_coord = min(run_coords_list, key=lambda c: haversine.haversine(lift_start, c, unit=haversine.Unit.METERS))

        if closest_coord != lift_start:

            G.add_edge(closest_coord, lift_start, weight=haversine.haversine(closest_coord, lift_start, unit=haversine.Unit.METERS))



    for lift_end in lift_ends:

        closest_coord = min(run_coords_list, key=lambda c: haversine.haversine(lift_end, c, unit=haversine.Unit.METERS))

        if closest_coord != lift_end:

            G.add_edge(lift_end, closest_coord, weight=haversine.haversine(lift_end, closest_coord, unit=haversine.Unit.METERS))



    for source in sources:

        closest_coord = min(lift_ends, key=lambda c: haversine.haversine(source, c, unit=haversine.Unit.METERS))

        G.add_edge(closest_coord, source, weight=haversine.haversine(closest_coord, source, unit=haversine.Unit.METERS))



    for sink in sinks:

        closest_coord = min(lift_starts, key=lambda c: haversine.haversine(sink, c, unit=haversine.Unit.METERS))

        G.add_edge(sink, closest_coord, weight=haversine.haversine(sink, closest_coord, unit=haversine.Unit.METERS))



    return G



@app.route("/add_new", methods=["POST"])
@auth.login_required
def add_new():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data received"}), 400
    resort_ids = [item.strip() for item in str(data.get("resortId", "")).split(",")]
    if not resort_ids or any(not valid_resort_id(item) for item in resort_ids):
        return jsonify({"status": "error", "message": "Invalid resortId"}), 400
    try:
        build_graph(data)
        for resort_id in resort_ids:
            github_write_json(f"resorts/{resort_id}.json", data, f"Add/update resort {resort_id}")
    except (GitHubStorageError, requests.RequestException) as exc:
        app.logger.exception("GitHub storage operation failed")
        return jsonify({"status": "error", "message": "GitHub storage failed", "details": str(exc)}), 502
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"status": "error", "message": f"Invalid resort data: {exc}"}), 400
    return jsonify({"status": "success", "message": "Successfully processed resort data."}), 200


@app.route("/reprocess", methods=["GET"])
def reprocess():
    resort_id = request.args.get("resortId", "").strip()
    if not resort_id:
        return jsonify({"error": "Missing required resortId parameters", "required": ["resortId"]}), 400
    if not valid_resort_id(resort_id):
        return jsonify({"error": "Invalid resortId"}), 400
    try:
        json_data = github_read_json(f"resorts/{resort_id}.json")
        build_graph(json_data)
    except FileNotFoundError:
        return jsonify({"error": "Resort not found", "resortId": resort_id}), 404
    except (GitHubStorageError, requests.RequestException) as exc:
        app.logger.exception("GitHub storage operation failed")
        return jsonify({"error": "GitHub storage failed", "details": str(exc)}), 502
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"error": f"Invalid resort data: {exc}"}), 400
    return jsonify({"status": "success", "message": "Successfully reprocessed resort data."}), 200


def calculate_gps_track(skiline_data, resort_json, resort_graph):

    def convert_time(date, time, timezone):

        hour, minute = time.split(":")



        completed_time = f"{date[:11]}{hour}:{minute}:00Z"



        naive_dt = datetime.fromisoformat(completed_time.rstrip('Z'))

        local_dt = naive_dt.replace(tzinfo=zoneinfo.ZoneInfo(timezone))

        utc_dt = local_dt.astimezone(zoneinfo.ZoneInfo("UTC"))

        formatted_output = utc_dt.strftime('%Y-%m-%dT%H:%M:%SZ')



        return formatted_output



    def interpolate_times(coordinates, timestamps):

        result = timestamps.copy()



        parsed = [

            datetime.fromisoformat(t.replace("Z", "+00:00")) if t is not None else None

            for t in timestamps

        ]



        known_indices = [

            i for i, t in enumerate(parsed) if t is not None

        ]



        for start, end in zip(known_indices, known_indices[1:]):

            if end == start + 1:

                continue



            distances = [

                haversine.haversine(coordinates[i], coordinates[i + 1])

                for i in range(start, end)

            ]



            total_distance = sum(distances)

            total_time = (parsed[end] - parsed[start]).total_seconds()



            cumulative_distance = 0



            for i in range(start + 1, end):

                cumulative_distance += distances[i - start - 1]



                if total_distance > 0:

                    fraction = cumulative_distance / total_distance

                else:

                    fraction = (i - start) / (end - start)



                interpolated = parsed[start] + timedelta(

                    seconds=total_time * fraction

                )



                result[i] = interpolated.isoformat().replace("+00:00", "Z")



        return result



    def filter_data(graph_data):

        result = []

        pending_departures = []



        for entry in graph_data:

            if "lift" in entry:

                if pending_departures:

                    result.append(pending_departures[-1])

                    pending_departures.clear()



                result.append(entry)



            else:

                pending_departures.append(entry)



        result.extend(pending_departures[-2:])



        return result



    skiing_day = skiline_data["ticketGraph"]["skiingDay"]

    graph_data = skiline_data["ticketGraph"]["graphData"]



    graph_data = filter_data(graph_data)



    date = skiing_day["date"]

    resort_timezone = skiing_day["resortTimeZoneId"]

    resort_id = skiing_day["resortId"]



    gps_track = []

    times = []



    for i, element in enumerate(graph_data):

        if not "lift" in element:

            continue



        tf = False

        next_tf = False



        lift_name = element["lift"].strip()

        if lift_name.endswith("TF"):

            lift_name = lift_name[:-3]

            tf = True



        if lift_name not in resort_json["resortLifts"]:

            lift_errors = load_lift_errors()
            if lift_name not in lift_errors["lifts"].setdefault(resort_id, []):
                lift_errors["lifts"][resort_id].append(lift_name)
                save_lift_errors(lift_errors, f"Log unknown lift for resort {resort_id}")



        lift_time = element["time"]

        run_start_time = graph_data[i+1]["time"]



        current_run = [tuple(coords) for coords in resort_json["resortLifts"][lift_name]]

        if tf:

            current_run.reverse()



        run_start_coords = current_run[-1]



        try:

            run_end_time = graph_data[i+2]["time"]



            if "lift" in graph_data[i+2]:

                next_lift_name = graph_data[i+2]["lift"].strip()

                if lift_name.endswith("TF"):

                    next_lift_name = next_lift_name[:-3]

                    next_tf = True



                if next_lift_name not in resort_json["resortLifts"]:

                    lift_errors = load_lift_errors()
                    if next_lift_name not in lift_errors["lifts"].setdefault(resort_id, []):
                        lift_errors["lifts"][resort_id].append(next_lift_name)
                        save_lift_errors(lift_errors, f"Log unknown lift for resort {resort_id}")



                next_lift_track = resort_json["resortLifts"][next_lift_name]

                if next_tf:

                    next_lift_track.reverse()



                run_end_coords = tuple(next_lift_track[0])



            else:

                run_end_coords = tuple(gps_track[0])



        except KeyError:

            break



        run_start_index = len(current_run) - 1



        try:

            current_run += nx.shortest_path(resort_graph, run_start_coords, run_end_coords, weight="weight")[1:]

        except nx.NetworkXNoPath:

            current_run += [run_end_coords]



        current_times = [None for _ in current_run]

        current_times[0] = convert_time(date, lift_time, resort_timezone)

        current_times[run_start_index] = convert_time(date, run_start_time, resort_timezone)

        current_times[-1] = convert_time(date, run_end_time, resort_timezone)



        if len(gps_track) > 0:

            gps_track += current_run[1:]

            times += current_times[1:]



        else:

            gps_track += current_run

            times += current_times



    interpolated_times = interpolate_times(gps_track, times)



    return [(lat, lon) for lon, lat in gps_track], interpolated_times



def convert_to_gpx(gps_track, times, resort_name):

    gpx = f'''<?xml version="1.0" encoding="UTF-8"?>

<gpx creator="SkilineStravaConverter" version="1.1" xmlns="http://www.topografix.com/GPX/1/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">

 <metadata>

  <time>{times[0]}</time>

 </metadata>

 <trk>

  <name>{resort_name}</name>

  <type>AlpineSki</type>

  <trkseg>

'''



    for (lat, lon), time in zip(gps_track, times):

        gpx += f'''   <trkpt lat="{lat:.7f}" lon="{lon:.7f}">

    <time>{time}</time>

   </trkpt>

'''



    gpx += '''  </trkseg>

 </trk>

</gpx>

'''

    return gpx



@app.route("/create_gpx", methods=["POST", "OPTIONS"])

def create_gpx():

    # Handle the CORS preflight request from the browser

    if request.method == "OPTIONS":

        return Response(status=200)



    data = request.get_json()



    if not data:

        return jsonify({"status": "error", "message": "No data received"}), 400



    resort_id = data["ticketGraph"]["skiingDay"]["resortId"]

    resort_name = data["ticketGraph"]["skiingDay"]["resortName"]



    if not valid_resort_id(str(resort_id)):
        return jsonify({"status": "error", "message": "Invalid resortId"}), 400
    try:
        ski_resort_json = github_read_json(f"resorts/{resort_id}.json")
        ski_resort_graph = build_graph(ski_resort_json)
    except FileNotFoundError:
        try:
            lift_errors = load_lift_errors()
            if resort_id not in lift_errors["resorts"]:
                lift_errors["resorts"].append(resort_id)
                save_lift_errors(lift_errors, f"Log missing resort {resort_id}")
        except (GitHubStorageError, requests.RequestException):
            app.logger.exception("Could not update lift error log")
        return jsonify({"status": "error", "message": f"Unknown resort: {resort_id}"}), 404
    except (GitHubStorageError, requests.RequestException) as exc:
        app.logger.exception("GitHub storage operation failed")
        return jsonify({"status": "error", "message": "GitHub storage failed", "details": str(exc)}), 502

    gps_track, times = calculate_gps_track(data, ski_resort_json, ski_resort_graph)



    # Create GPX

    gpx_string = convert_to_gpx(gps_track, times, resort_name)



    # 3. Return a response

    return Response(

        gpx_string.encode("utf-8"),

        mimetype="application/gpx+xml",

        headers={"Content-Disposition": f"attachment; filename={resort_name}.gpx"}

    )



if __name__ == '__main__':

    app.run(debug=False, use_reloader=False)