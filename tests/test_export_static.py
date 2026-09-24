from undercurrents import export_static


def test_every_parameterised_route_has_an_id_source():
    # A new /api/.../{param} route the front end reads must be enumerable, or the static site
    # would silently miss its files.
    params = {export_static._param(t) for t in export_static._templates()} - {None}
    assert params <= set(export_static.ID_SOURCES)


def test_templates_are_relative_to_the_api_prefix():
    templates = export_static._templates()
    assert "/shows" in templates
    assert "/shows/{setlist_id}" in templates
    assert not any(t.startswith("/api") for t in templates)
