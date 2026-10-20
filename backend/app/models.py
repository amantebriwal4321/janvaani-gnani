"""Citizen profile. Synthetic household facts only — never an ID number."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

Gender = Literal["woman", "man", "other"]
Area = Literal["rural", "urban"]
Occupation = Literal[
    "farmer",
    "artisan",
    "street_vendor",
    "labourer",
    "homemaker",
    "student",
    "salaried",
    "other",
]
Ration = Literal["aay", "phh", "nphh", "none"]
Housing = Literal["kutcha", "pucca", "homeless"]
Category = Literal["sc", "st", "obc", "general"]


class Profile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    age: int | None = None
    gender: Gender | None = None
    state: str | None = None
    state_name: str | None = None
    district: str | None = None
    area: Area | None = None
    occupation: Occupation | None = None
    land_acres: float | None = None
    crop: str | None = None
    crop_loss: bool | None = None
    annual_income: int | None = None
    category: Category | None = None
    bpl: bool | None = None
    ration: Ration | None = None
    senior_age: int | None = None
    widow: bool | None = None
    disability: bool | None = None
    pregnant: bool | None = None
    bank_account: bool | None = None
    aadhaar_seeded: bool | None = None
    mobile_linked: bool | None = None
    name_match: bool | None = None
    artisan_trade: str | None = None
    housing: Housing | None = None
    lpg: bool | None = None


BOOL_FIELDS = {
    "crop_loss",
    "bpl",
    "widow",
    "disability",
    "pregnant",
    "bank_account",
    "aadhaar_seeded",
    "mobile_linked",
    "name_match",
    "lpg",
}
INT_FIELDS = {"age", "senior_age", "annual_income"}
FLOAT_FIELDS = {"land_acres"}
ENUM_FIELDS: dict[str, set[str]] = {
    "gender": {"woman", "man", "other"},
    "area": {"rural", "urban"},
    "occupation": {
        "farmer",
        "artisan",
        "street_vendor",
        "labourer",
        "homemaker",
        "student",
        "salaried",
        "other",
    },
    "ration": {"aay", "phh", "nphh", "none"},
    "housing": {"kutcha", "pucca", "homeless"},
    "category": {"sc", "st", "obc", "general"},
}
STRING_FIELDS = {"state", "state_name", "district", "crop", "artisan_trade"}
PROFILE_FIELDS = BOOL_FIELDS | INT_FIELDS | FLOAT_FIELDS | set(ENUM_FIELDS) | STRING_FIELDS
