import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.local')
django.setup()
from django.template.loader import render_to_string
from sky_events.apps.events.models import AstronomicalEvent

evt = AstronomicalEvent.objects.first()
if evt:
    try:
        html = render_to_string('pages/events/detail.html', {'event': evt})
        # Find the var stations line
        if 'var stations = ' in html:
            start = html.find('var stations = ')
            end = html.find(';', start)
            line = html[start:end+1]
            print('Stations line in rendered HTML:')
            print(line[:150])
        else:
            print('var stations not found in rendered HTML')
            if 'map_stations_json' in html:
                print('BUT map_stations_json found in HTML')
            else:
                print('map_stations_json NOT found in HTML either')
    except Exception as e:
        print(f'Error rendering template: {e}')
else:
    print('No events found')
