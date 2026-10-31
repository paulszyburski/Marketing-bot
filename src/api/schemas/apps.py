from typing import Any

from pydantic import BaseModel


class AppResponse(BaseModel):
    id: str
    appName: str
    appDescription: str | None = None
    appLink: str | None = None
    logo: str | None = None
    advertisingImage: str | None = None
    enabled: bool = True

    @classmethod
    def from_config(cls, app: dict[str, Any]) -> "AppResponse":
        return cls(
            id=app["id"],
            appName=app["appName"],
            appDescription=app.get("appDescription"),
            appLink=app.get("appLink"),
            logo=app.get("logo"),
            advertisingImage=app.get("advertisingImage"),
            enabled=app.get("enabled", True),
        )


class AppEnabledUpdate(BaseModel):
    enabled: bool
