import re
from pydantic import BaseModel, ConfigDict


def to_camel(string: str) -> str:
    """snake_case -> camelCase"""
    if not string:
        return string
    # preserve leading underscores
    prefix_match = re.match(r"^(_+)", string)
    prefix = prefix_match.group(1) if prefix_match else ""
    core = string[len(prefix) :]
    parts = core.split("_")
    if not parts:
        return prefix
    first = parts[0].lower()
    rest = "".join(p.capitalize() if p else "" for p in parts[1:])
    return prefix + first + rest


def to_snake(string: str) -> str:
    """camelCase/PascalCase -> snake_case"""
    if not string:
        return string
    # preserve leading underscores
    prefix_match = re.match(r"^(_+)", string)
    prefix = prefix_match.group(1) if prefix_match else ""
    core = string[len(prefix) :]
    # normalize hyphens and then split camel/Pascal boundaries
    s = core.replace("-", "_")
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", s)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    return prefix + s.lower()


class CamelModel(BaseModel):
    # Inbound + schema: alias_generator defines how field aliases (camelCase) are produced.
    # Inbound: populate_by_name=True lets clients send either snake_case or camelCase.
    # (Outbound shape is enforced below in model_dump / model_dump_json.)
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        str_strip_whitespace=False,
    )

    # Outbound: ensure dict serialization always uses camelCase unless explicitly overridden.
    def model_dump(self, *args, **kwargs):
        kwargs.setdefault("by_alias", True)
        return super().model_dump(*args, **kwargs)

    # Outbound: ensure JSON string serialization also always uses camelCase.
    def model_dump_json(self, *args, **kwargs):
        kwargs.setdefault("by_alias", True)
        return super().model_dump_json(*args, **kwargs)

