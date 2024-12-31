__version__ = "2.0.1"
__app_name__ = "RogControlCenter"


def is_newer(version):
    def parse_version(version):
        return tuple(map(int, version.split(".")))

    v1 = parse_version(__version__)
    v2 = parse_version(version)

    if v1 < v2:
        return True
    else:
        return False
