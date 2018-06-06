import requests


def reverse_geocode(lat, lon):
    try:
        latlng = str(lon) + ',' + str(lat)
        r = (requests.get('https://geocode-maps.yandex.ru/1.x/?geocode={}&format=json&results=1&kind=house'.format(latlng))
             .json()['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['metaDataProperty']['GeocoderMetaData']
             ['Address']['Components'])
        city = ''
        street = ''
        home = ''
        for c in r:
            if c['kind'] == 'locality':
                city = c['name'].strip()
            if c['kind'] == 'street':
                street = c['name'].replace('улица', '').replace('проспект', '').replace(
                    ' ул', '').replace(' пр-т', '').replace('.', '').strip()
            if c['kind'] == 'house':
                home = c['name'].strip()
        if not all([city, street, home]):
            return None
        return {
            'city': city,
            'street': street,
            'home': home,
        }
    except:
        return None
