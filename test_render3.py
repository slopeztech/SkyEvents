import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.local')
django.setup()
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from sky_events.apps.events.models import AstronomicalEvent

evt = AstronomicalEvent.objects.first()
if evt:
    try:
        factory = RequestFactory()
        request = factory.get(f'/events/{evt.code}/')
        request.user = AnonymousUser()
        
        html = render_to_string('pages/events/detail.html', {'event': evt, 'request': request})
        if 'var stations = ' in html:
            start = html.find('var stations = ')
            end = html.find('\n', start)
            line = html[start:end]
            print('Found var stations line:')
            print(line)
        else:
            print('var stations NOT found')
            if '{{ map_stations_json' in html:
                print('Found raw {{ map_stations_json in HTML')
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
else:
    print('No events found')
