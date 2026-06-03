import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.local')
django.setup()
from django.template.loader import render_to_string
from sky_events.apps.events.models import AstronomicalEvent

evt = AstronomicalEvent.objects.first()
if evt:
    from sky_events.apps.events.views import EventDetailView
    view = EventDetailView()
    view.object = evt
    ctx = view.get_context_data()
    
    # Render just the script block to see what it generates
    from django.template import Template, Context
    script_template = Template("""
    var stations = {{ map_stations_json|safe }};
    var lat = {{ map_center_lat }};
    var lng = {{ map_center_lng }};
    var zoom = {{ map_default_zoom }};
    """)
    rendered = script_template.render(Context(ctx))
    print("Rendered script:")
    print(rendered)
else:
    print('No events found')
