"""Interpret the free-text Location field of the gas log and add geohashes.

Each Location string is matched against PATTERNS (first match wins) and resolved
to a place in PLACES. Coordinates are town or base centres, not individual gas
stations, so the geohash is cut to 5 characters (a cell about 4.9 km x 4.9 km).
The one entry with an exact map pin gets 8 characters (about 38 m x 19 m).

Confidence values:
  exact        coordinates taken from a map link in the entry
  town         the entry names the town or base directly (spelling may be off)
  approximate  the place is my best reading of a vague or garbled entry
  (blank)      no place could be read from the entry
"""
import re

import pandas as pd

# (lat, lon, source). "geonames" = GeoNames cities1000 town centre;
# "manual" = entered by hand because the place isn't in that list.
PLACES = {
    "Springfield, MO": (37.2153, -93.2982, "geonames"),
    "Tulsa, OK": (36.1540, -95.9928, "geonames"),
    "Hinton, OK": (35.4714, -98.3556, "geonames"),
    "Amarillo, TX": (35.2220, -101.8313, "geonames"),
    "Santa Rosa, NM": (34.9387, -104.6825, "geonames"),
    "Milan, NM": (35.1698, -107.8909, "geonames"),
    "Flagstaff, AZ": (35.1981, -111.6513, "geonames"),
    "Cedar City, UT": (37.6775, -113.0619, "geonames"),
    "Chesterfield, MO": (38.6631, -90.5771, "geonames"),
    "Clinton, MO": (38.3686, -93.7783, "geonames"),
    "Burlington, CO": (39.3061, -102.2694, "geonames"),
    "Glenwood Springs, CO": (39.5505, -107.3248, "geonames"),
    "Salina, UT": (38.9577, -111.8599, "geonames"),
    "Springville, UT": (40.1652, -111.6107, "geonames"),
    "Fillmore, UT": (38.9689, -112.3235, "geonames"),
    "Sandy, UT": (40.5916, -111.8841, "geonames"),
    "Ogden, UT": (41.2230, -111.9738, "geonames"),
    "Riverdale, UT": (41.1769, -112.0038, "geonames"),
    "Layton, UT": (41.0602, -111.9711, "geonames"),
    "Clearfield, UT": (41.1108, -112.0260, "geonames"),
    "Laramie, WY": (41.3114, -105.5911, "geonames"),
    "Cheyenne, WY": (41.1400, -104.8203, "geonames"),
    "Sidney, NE": (41.1428, -102.9780, "geonames"),
    "Aurora, NE": (40.8672, -98.0042, "geonames"),
    "Harrisonville, MO": (38.6533, -94.3488, "geonames"),
    "Oklahoma City, OK": (35.4676, -97.5164, "geonames"),
    "Albuquerque, NM": (35.0845, -106.6511, "geonames"),
    "Joseph City, AZ": (34.9559, -110.3340, "geonames"),
    "Kingman, AZ": (35.1894, -114.0530, "geonames"),
    "North Las Vegas, NV": (36.1989, -115.1175, "geonames"),
    "Farmington, UT": (40.9805, -111.8874, "geonames"),
    "Casper, WY": (42.8666, -106.3131, "geonames"),
    "North Platte, NE": (41.1239, -100.7654, "geonames"),
    "Lincoln, NE": (40.8000, -96.6670, "geonames"),
    "Blue Springs, MO": (39.0170, -94.2816, "geonames"),
    "Columbia, MO": (38.9517, -92.3341, "geonames"),
    "Salem, MO": (37.6456, -91.5360, "geonames"),
    "Willow Springs, MO": (36.9923, -91.9699, "geonames"),
    "Green River, WY": (41.5286, -109.4663, "geonames"),
    "Roosevelt, UT": (40.2994, -109.9888, "geonames"),
    "Basalt, CO": (39.3689, -107.0328, "geonames"),
    "Omaha, NE": (41.2586, -95.9378, "geonames"),
    "Uintah, UT": (41.1441, -111.9233, "geonames"),
    "Lehi, UT": (40.3916, -111.8508, "geonames"),
    "Cortez, CO": (37.3489, -108.5859, "geonames"),
    "Gallup, NM": (35.5281, -108.7426, "geonames"),
    "Okemah, OK": (35.4326, -96.3050, "geonames"),
    "Hamilton, AL": (34.1423, -87.9886, "geonames"),
    "Stockbridge, GA": (33.5443, -84.2338, "geonames"),
    "Gainesville, GA": (34.2979, -83.8241, "geonames"),
    "Byron, GA": (32.6538, -83.7596, "geonames"),
    "Forsyth, GA": (33.0343, -83.9382, "geonames"),
    "Warner Robins, GA": (32.6210, -83.5999, "geonames"),
    "Cumming, GA": (34.2073, -84.1402, "geonames"),
    "Locust Grove, GA": (33.3460, -84.1091, "geonames"),
    "Savannah, GA": (32.0835, -81.0998, "geonames"),
    "Biloxi, MS": (30.3960, -88.8853, "geonames"),
    "Nellis AFB, NV": (36.2461, -115.0572, "geonames"),
    # Not in GeoNames cities1000 (small towns and military bases): entered by hand
    "Green River, UT": (38.9953, -110.1618, "manual"),
    "Wamsutter, WY": (41.6719, -107.9784, "manual"),
    "Jamestown, WY": (41.5164, -109.5468, "manual"),
    "Palestine, AR": (34.9690, -90.9026, "manual"),
    "Waco, GA": (33.7023, -85.1855, "manual"),
    "Hill AFB, UT": (41.1240, -111.9730, "manual"),
    "Whiteman AFB, MO": (38.7302, -93.5479, "manual"),
    "Keesler AFB, MS": (30.4103, -88.9240, "manual"),
    "Robins AFB, GA": (32.6400, -83.5918, "manual"),
    "Buckley SFB, CO": (39.7017, -104.7517, "manual"),
    "Fort Riley, KS": (39.0600, -96.7900, "manual"),
    "Fort Leonard Wood, MO": (37.7150, -92.1500, "manual"),
}

# (regex matched case-insensitively against the Location text, place, confidence, note)
# Order matters: the first pattern that matches wins.
PATTERNS = [
    (r"towing|^unknown", None, None, "no place given"),
    (r"^macadoodles$", None, None, "store chain; town not given"),
    (r"^costco$", None, None, "store chain; town not given"),
    (r"^south point mall$", None, None, "no match found"),
    (r"canyon ranch", None, None, "no town by this name on I-15; somewhere between Las Vegas and Springville"),
    (r"loves 581, central utah", None, None, "store number only"),
    (r"\(575\) 472-", "Santa Rosa, NM", "approximate", "read from the phone number's exchange"),
    (r"maverick south oh? hill afb", "Hill AFB, UT", "approximate", "a Maverick just south of the base"),
    (r"maverick on 700", "Clearfield, UT", "approximate", "a road named 700 near Hill AFB"),
    (r"antelope and hill field", "Layton, UT", "town", "Antelope Dr & Hill Field Rd"),
    (r"adam.?s parkway", "Riverdale, UT", "approximate", "Adams Ave Parkway"),
    (r"harrison (blvd|and)", "Ogden, UT", "town", "Harrison Blvd"),
    (r"harmon.?s .*farmington", "Farmington, UT", "town", None),
    (r"ogden", "Ogden, UT", "town", None),
    (r"riverdale", "Riverdale, UT", "town", None),
    (r"unitas", "Uintah, UT", "approximate", "read 'Unitas' as Uintah"),
    (r"maverick lego", "Lehi, UT", "approximate", "read 'Lego' as Lehi"),
    (r"^sandy$", "Sandy, UT", "approximate", "assumed Sandy, UT (living near Hill AFB then)"),
    (r"hill afb", "Hill AFB, UT", "town", None),
    (r"nellis", "Nellis AFB, NV", "town", None),
    (r"north of vegas", "North Las Vegas, NV", "approximate", None),
    (r"whiteman", "Whiteman AFB, MO", "town", None),
    (r"keesler", "Keesler AFB, MS", "town", None),
    (r"warner robbin.?s, afb", "Robins AFB, GA", "town", None),
    (r"warner robins", "Warner Robins, GA", "town", None),
    (r"buckley", "Buckley SFB, CO", "town", None),
    (r"fort riley", "Fort Riley, KS", "town", None),
    (r"fort len", "Fort Leonard Wood, MO", "town", None),
    (r"campbell|springfield|independence|kim and go", "Springfield, MO", "town", None),
    (r"chesterfield", "Chesterfield, MO", "town", None),
    (r"clinton", "Clinton, MO", "town", None),
    (r"tulsa", "Tulsa, OK", "town", None),
    (r"hinton", "Hinton, OK", "town", None),
    (r"oklahoma city", "Oklahoma City, OK", "town", None),
    (r"okemah", "Okemah, OK", "town", None),
    (r"ama?r+illo", "Amarillo, TX", "town", None),
    (r"santa rosa", "Santa Rosa, NM", "town", None),
    (r"milan", "Milan, NM", "town", None),
    (r"albuquerque", "Albuquerque, NM", "town", None),
    (r"gall[ou]p", "Gallup, NM", "town", None),
    (r"flagstaff", "Flagstaff, AZ", "town", None),
    (r"joseph city", "Joseph City, AZ", "town", None),
    (r"kingman", "Kingman, AZ", "town", None),
    (r"cedar city", "Cedar City, UT", "town", None),
    (r"fill?more", "Fillmore, UT", "town", None),
    (r"salina", "Salina, UT", "town", None),
    (r"spring ?(ville|like)", "Springville, UT", "town", None),
    (r"roosevelt", "Roosevelt, UT", "town", None),
    (r"green river,? ut", "Green River, UT", "town", None),
    (r"green river", "Green River, WY", "town", None),
    (r"wamsutter", "Wamsutter, WY", "town", None),
    (r"lar(a|ia|i)mi?e", "Laramie, WY", "town", None),
    (r"cheyan+e", "Cheyenne, WY", "town", None),
    (r"casper", "Casper, WY", "town", None),
    (r"james ?town", "Jamestown, WY", "town", None),
    (r"glenwood", "Glenwood Springs, CO", "town", None),
    (r"basalt", "Basalt, CO", "town", None),
    (r"burlington", "Burlington, CO", "town", None),
    (r"cortez", "Cortez, CO", "town", None),
    (r"s[iy]dney", "Sidney, NE", "town", None),
    (r"aurora", "Aurora, NE", "town", None),
    (r"north platte", "North Platte, NE", "town", "entries tagged WY are North Platte, NE"),
    (r"lincoln", "Lincoln, NE", "town", None),
    (r"omaha", "Omaha, NE", "town", None),
    (r"harrisonville", "Harrisonville, MO", "town", None),
    (r"blue springs", "Blue Springs, MO", "town", None),
    (r"columbia", "Columbia, MO", "town", None),
    (r"salem", "Salem, MO", "town", None),
    (r"willow springs", "Willow Springs, MO", "town", None),
    (r"palestine", "Palestine, AR", "town", None),
    (r"hamilton", "Hamilton, AL", "town", None),
    (r"waco, ga", "Waco, GA", "town", None),
    (r"stockbridge", "Stockbridge, GA", "town", None),
    (r"gainesville", "Gainesville, GA", "town", None),
    (r"byron", "Byron, GA", "town", None),
    (r"forsyth", "Forsyth, GA", "town", None),
    (r"cumming", "Cumming, GA", "town", None),
    (r"locust grove", "Locust Grove, GA", "town", None),
    (r"savannah", "Savannah, GA", "town", None),
    (r"biloxi", "Biloxi, MS", "town", None),
]

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def geohash(lat: float, lon: float, precision: int) -> str:
    """Standard geohash encoding."""
    lat_rng, lon_rng = [-90.0, 90.0], [-180.0, 180.0]
    out, bits, ch, even = [], 0, 0, True
    while len(out) < precision:
        rng, val = (lon_rng, lon) if even else (lat_rng, lat)
        mid = (rng[0] + rng[1]) / 2
        ch <<= 1
        if val >= mid:
            ch |= 1
            rng[0] = mid
        else:
            rng[1] = mid
        even = not even
        bits += 1
        if bits == 5:
            out.append(_BASE32[ch])
            bits, ch = 0, 0
    return "".join(out)


def resolve(text):
    """Return (place, lat, lon, confidence, note) for one Location string."""
    if not isinstance(text, str) or not text.strip():
        return (None, None, None, None, None)
    pin = re.search(r"[?&]ll=(-?\d+\.\d+),(-?\d+\.\d+)", text)
    if pin:
        name = "Amarillo, TX" if "amarillo" in text.lower() else None
        return (name, float(pin[1]), float(pin[2]), "exact", "map pin in the entry")
    for pattern, place, conf, note in PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            if place is None:
                return (None, None, None, None, note)
            lat, lon, _ = PLACES[place]
            return (place, lat, lon, conf, note)
    return (None, None, None, None, "not recognised")


def add_geohash(df: pd.DataFrame, col: str = "Location") -> pd.DataFrame:
    """Add Place, Latitude, Longitude, Geohash, Location Confidence and Location Note."""
    res = pd.DataFrame(
        [resolve(t) for t in df[col]],
        columns=["Place", "Latitude", "Longitude", "Location Confidence", "Location Note"],
        index=df.index,
    )
    res["Geohash"] = [
        geohash(la, lo, 8 if c == "exact" else 5) if pd.notna(c) else None
        for la, lo, c in zip(res.Latitude, res.Longitude, res["Location Confidence"])
    ]
    out = df.copy()
    pos = out.columns.get_loc(col) + 1
    for i, c in enumerate(["Place", "Geohash", "Latitude", "Longitude", "Location Confidence", "Location Note"]):
        out.insert(pos + i, c, res[c])
    return out


if __name__ == "__main__":
    import sys

    from load_gladiator import load_gladiator

    df = add_geohash(load_gladiator(sys.argv[1]))
    pd.set_option("display.width", 250, "display.max_colwidth", 45, "display.max_rows", 200)
    summary = (
        df.assign(Location=df.Location.str.slice(0, 45))
        .groupby(["Location", "Place", "Geohash", "Location Confidence"], dropna=False)
        .size().rename("Stops").reset_index().sort_values("Stops", ascending=False)
    )
    print(summary.to_string(index=False))
    print()
    print(df["Location Confidence"].value_counts(dropna=False))
    if len(sys.argv) > 2:
        df.to_csv(sys.argv[2], index=False)
