import django, os, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.local')
django.setup()
from sky_events.apps.events.models import AstronomicalEvent
from sky_events.apps.events.views import EventDetailView

evt = AstronomicalEvent.objects.first()
if evt:
    print(f'Event: {evt.code}')
    view = EventDetailView()
    view.object = evt
    ctx = view.get_context_data()
    if 'map_stations_json' in ctx:
        print(f'map_stations_json type: {type(ctx["map_stations_json"])}')
        print(f'map_stations_json length: {len(ctx["map_stations_json"])}')
        print(f'Content: {ctx["map_stations_json"][:200]}')
    else:
        print('map_stations_json NOT in context!')
        print(f'Available keys: {list(ctx.keys())}')
else:
    print('No events found')
