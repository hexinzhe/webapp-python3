from www import config_default

configs = config_default.configs
try:
    from www import config_override
    configs.update(config_override.configs)
except ImportError:
    pass
