# Config

`load_config(defaults, file_values, env)` returns the effective configuration:

1. Start from `defaults`, then apply `file_values`, then the environment `env` (a dict like os.environ).
   Later sources win.
2. Nested dicts are merged key by key, not replaced. Lists and other values are replaced.
3. Only environment variables starting with `APP_` count. `APP_DB__HOST=x` sets `["db"]["host"] = "x"`:
   a double underscore is one level of nesting, names are lowercased.
4. An environment value is converted to the type of the value it overrides when that is an int, float or
   bool (`"true"`/`"false"`, any case); a value that cannot be converted raises ValueError.
5. The inputs are never modified.
