from www import config_default


def merge(defaults, override):
    r = {}
    for k, v in defaults.items():
        if k in override:
            if isinstance(v, dict):
                r[k] = merge(v, override[k])
            else:
                r[k] = override[k]
        else:
            r[k] = v
    return r

configs = config_default.configs
try:
    from www import config_override
    merge(configs, config_override.configs)
except ImportError:
    pass
