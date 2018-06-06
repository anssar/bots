import googlemaps

gmaps = googlemaps.Client(key='AIzaSyAV5UX8H9JeV_itj7W-Ep5sRhkUDBaebqE')


def longest(a):
    max_len = -1
    ret = None
    for i in a:
        if '.' in i:
            continue
        if len(i) > max_len:
            max_len = len(i)
            ret = i
    return ret


def reverse_geocode(lat, lon):
    home = None
    street = None
    city = None
    rv = gmaps.reverse_geocode((lat, lon), language='Ru')
    for i in rv:
        for j in i['address_components']:
            if 'street_number' in j['types']:
                home = j['short_name']
            if 'route' in j['types']:
                street = longest(j['short_name'].split(' '))
            if 'locality' in j['types']:
                city = longest(j['short_name'].split(' '))
    if not all([city, street, home]):
        return None
    return {
        'city': city,
        'street': street,
        'home': home,
    }
