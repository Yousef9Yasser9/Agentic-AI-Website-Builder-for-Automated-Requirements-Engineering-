import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "page_load: HTTP page load validation")
    config.addinivalue_line("markers", "ui_action: buttons, forms, and navigation")
    config.addinivalue_line("markers", "database: database CRUD and schema checks")
    config.addinivalue_line("markers", "role_based: role dashboards and access control")
