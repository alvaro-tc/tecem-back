#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    import sys
    import sys
    try:
        import cgi
    except ImportError:
        print("*************************************************************************")
        print("CRITICAL ERROR: 'cgi' module not found.")
        print(f"You are using Python {sys.version.split()[0]} which has removed this module.")
        print("Django 3.2 requires 'cgi'. You MUST use the virtual environment with Python 3.9.")
        print("Run command:")
        print(".\\venv\\Scripts\\python.exe manage.py runserver 5000")
        print("*************************************************************************")
        sys.exit(1)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
