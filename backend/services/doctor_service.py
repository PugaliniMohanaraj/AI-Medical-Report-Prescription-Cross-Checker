"""Match flagged issues to a specialty and search real nearby doctors/clinics."""

from __future__ import annotations

import logging
import math
import re
from typing import Any
from urllib.parse import quote_plus

import httpx

from backend.models.schemas import (
    DoctorRecommendRequest,
    DoctorRecommendResponse,
    DoctorResult,
    FlagInput,
)
from backend.utils.config import Settings, get_settings

logger = logging.getLogger(__name__)

USER_AGENT = "MedCross-YGC/1.0 (medical-report-cross-checker; student-project)"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)

SPECIALTY_RULES: list[tuple[str, str, list[str]]] = [
    (
        "cardiologist",
        "Heart-related labs or diagnoses (blood pressure, cholesterol, cardiac).",
        ["heart", "cardiac", "cardio", "ldl", "hdl", "cholesterol", "hypertension", "blood pressure", "bp ", "triglyceride"],
    ),
    (
        "endocrinologist",
        "Glucose / diabetes markers or diagnoses.",
        ["diabetes", "hba1c", "a1c", "glucose", "insulin", "thyroid", "endocrin"],
    ),
    (
        "nephrologist",
        "Kidney-related labs or diagnoses.",
        ["kidney", "renal", "creatinine", "egfr", "urea", "nephro"],
    ),
    (
        "gastroenterologist",
        "Liver or digestive markers.",
        ["liver", "hepatic", "alt", "ast", "bilirubin", "gastro"],
    ),
    (
        "allergist",
        "Allergy conflict flagged in the prescription check.",
        ["allerg"],
    ),
    (
        "pharmacist",
        "Drug interaction, duplicate prescription, or dosage conflict.",
        ["interaction", "duplicate", "dosage", "drug"],
    ),
]

OSM_SPECIALTY_TAGS: dict[str, list[str]] = {
    "cardiologist": ["cardiology", "cardiologist"],
    "endocrinologist": ["endocrinology", "endocrinologist", "diabetology"],
    "nephrologist": ["nephrology", "nephrologist"],
    "gastroenterologist": ["gastroenterology", "hepatology"],
    "allergist": ["allergology", "allergy", "immunology"],
    "pharmacist": [],
    "general practitioner": ["general", "family", "gp"],
}

PHARMACY_SPECIALTIES = {"pharmacist"}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _blob(flags: list[FlagInput], diagnosis: list[str], primary: str | None, labs: list[str]) -> str:
    parts: list[str] = []
    for flag in flags:
        parts.extend(
            [
                flag.type or "",
                flag.severity or "",
                flag.title or "",
                flag.explanation or "",
                " ".join(flag.related_medicines),
            ]
        )
    parts.extend(diagnosis)
    if primary:
        parts.append(primary)
    parts.extend(labs)
    return " ".join(parts).lower()


def match_specialty(
    flags: list[FlagInput],
    diagnosis: list[str] | None = None,
    primary_diagnosis: str | None = None,
    abnormal_labs: list[str] | None = None,
) -> tuple[str, str]:
    text = _blob(flags, diagnosis or [], primary_diagnosis, abnormal_labs or [])
    high_or_uncertain = any(
        (f.severity or "").lower() == "high" for f in flags
    )
    for specialty, reason, keywords in SPECIALTY_RULES:
        if any(key in text for key in keywords):
            return specialty, reason
    if high_or_uncertain:
        return (
            "general practitioner",
            "High-risk or unclear flag — start with a general practitioner or clinic.",
        )
    return (
        "general practitioner",
        "No specialist keyword matched — a general practitioner can triage next steps.",
    )


def _matches_availability(opening: str | None, availability: str) -> bool:
    if not opening:
        return False
    hours = opening.lower()
    avail = (availability or "anytime").lower().replace(" ", "_")
    if avail in {"anytime", "this_week", "thisweek"}:
        return True
    if avail in {"evenings", "evening"}:
        if "24/7" in hours or "24 hours" in hours:
            return True
        return bool(re.search(r"(1[89]|20|21|22)\s*:", hours))
    if avail in {"weekends", "weekend"}:
        return "sa" in hours or "su" in hours or "sat" in hours or "sun" in hours
    return True


def _display_address(tags: dict[str, Any]) -> str:
    parts = [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:suburb") or tags.get("addr:neighbourhood"),
        tags.get("addr:city") or tags.get("addr:town") or tags.get("addr:village"),
        tags.get("addr:state"),
        tags.get("addr:postcode"),
    ]
    joined = ", ".join(str(p) for p in parts if p)
    return joined or tags.get("addr:full") or "Address not listed in OpenStreetMap"


def _infer_specialty(tags: dict[str, Any], requested: str) -> str:
    healthcare = (tags.get("healthcare:speciality") or tags.get("healthcare:specialty") or "").lower()
    amenity = (tags.get("amenity") or "").lower()
    healthcare_kind = (tags.get("healthcare") or "").lower()
    if amenity == "pharmacy" or healthcare_kind == "pharmacy":
        return "pharmacist"
    if healthcare:
        return healthcare.replace(";", ", ")
    if amenity == "hospital":
        return "hospital / clinic"
    if amenity in {"clinic", "doctors"} or healthcare_kind in {"doctor", "clinic", "centre", "center"}:
        return requested
    return requested


class DoctorService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.google_key = (getattr(self.settings, "google_places_api_key", "") or "").strip()

    async def recommend(self, payload: DoctorRecommendRequest) -> DoctorRecommendResponse:
        specialty, reason = match_specialty(
            payload.flags,
            payload.diagnosis,
            payload.primary_diagnosis,
            payload.abnormal_labs,
        )
        disclaimer = (
            "This is not a diagnosis. Listings come from public map data. "
            "Confirm opening hours and consult a licensed doctor or pharmacist."
        )

        try:
            geo = await self._geocode(payload.location)
        except Exception as exc:
            logger.warning("Geocoding failed: %s", exc)
            return DoctorRecommendResponse(
                recommended_specialty=specialty,
                specialty_reason=reason,
                location_query=payload.location,
                radius_km=payload.radius_km,
                availability=payload.availability,
                source="none",
                no_results=True,
                message=f"Could not find that location. Try a clearer city or area name. ({exc})",
                suggestion="Use a city name such as 'Jaffna' or 'Colombo 07'.",
                disclaimer=disclaimer,
            )

        if geo is None:
            return DoctorRecommendResponse(
                recommended_specialty=specialty,
                specialty_reason=reason,
                location_query=payload.location,
                radius_km=payload.radius_km,
                availability=payload.availability,
                source="nominatim",
                no_results=True,
                message="No matching place found for that location.",
                suggestion="Widen the wording (include city + country) and search again.",
                disclaimer=disclaimer,
            )

        lat, lon, display = geo
        results: list[DoctorResult] = []
        source = "openstreetmap"

        if self.google_key:
            try:
                results = await self._search_google(lat, lon, specialty, payload)
                source = "google_places"
            except Exception as exc:
                logger.warning("Google Places failed, falling back to OSM: %s", exc)

        if not results:
            try:
                results = await self._search_overpass(lat, lon, specialty, payload)
                source = "openstreetmap"
            except Exception as exc:
                logger.warning("Overpass search failed: %s", exc)
                return DoctorRecommendResponse(
                    recommended_specialty=specialty,
                    specialty_reason=reason,
                    location_query=payload.location,
                    location_resolved=display,
                    latitude=lat,
                    longitude=lon,
                    radius_km=payload.radius_km,
                    availability=payload.availability,
                    source=source,
                    no_results=True,
                    message=(
                        "The OpenStreetMap clinic search (Overpass) failed or timed out. "
                        "This is usually a temporary public-API issue, not a problem with your location."
                    ),
                    suggestion="Wait ~30–60s and search again. Optional: set GOOGLE_PLACES_API_KEY for a more stable source.",
                    disclaimer=disclaimer,
                )

        if not results:
            return DoctorRecommendResponse(
                recommended_specialty=specialty,
                specialty_reason=reason,
                location_query=payload.location,
                location_resolved=display,
                latitude=lat,
                longitude=lon,
                radius_km=payload.radius_km,
                availability=payload.availability,
                source=source,
                no_results=True,
                message=(
                    f"No {specialty} listings were found within {payload.radius_km:g} km of {display}."
                ),
                suggestion="Widen the search radius or try a neighbouring city. Do not treat an empty list as a recommendation.",
                disclaimer=disclaimer,
            )

        return DoctorRecommendResponse(
            recommended_specialty=specialty,
            specialty_reason=reason,
            location_query=payload.location,
            location_resolved=display,
            latitude=lat,
            longitude=lon,
            radius_km=payload.radius_km,
            availability=payload.availability,
            source=source,
            results=results,
            count=len(results),
            no_results=False,
            message=f"Found {len(results)} real listing(s) near {display} for {specialty}.",
            disclaimer=disclaimer,
        )

    async def _geocode(self, location: str) -> tuple[float, float, str] | None:
        params = {"q": location, "format": "json", "limit": 1}
        async with httpx.AsyncClient(timeout=20.0, headers={"User-Agent": USER_AGENT}) as client:
            response = await client.get(NOMINATIM_URL, params=params)
            response.raise_for_status()
            data = response.json()
        if not data:
            return None
        first = data[0]
        return float(first["lat"]), float(first["lon"]), str(first.get("display_name") or location)

    async def _search_overpass(
        self,
        lat: float,
        lon: float,
        specialty: str,
        payload: DoctorRecommendRequest,
    ) -> list[DoctorResult]:
        radius_m = int(payload.radius_km * 1000)
        spec_tags = OSM_SPECIALTY_TAGS.get(specialty, [])
        filters: list[str] = []
        if specialty in PHARMACY_SPECIALTIES:
            filters.append(f'nwr["amenity"="pharmacy"](around:{radius_m},{lat},{lon});')
            filters.append(f'nwr["healthcare"="pharmacy"](around:{radius_m},{lat},{lon});')
        else:
            filters.extend(
                [
                    f'nwr["amenity"="doctors"](around:{radius_m},{lat},{lon});',
                    f'nwr["amenity"="clinic"](around:{radius_m},{lat},{lon});',
                    f'nwr["amenity"="hospital"](around:{radius_m},{lat},{lon});',
                    f'nwr["healthcare"="doctor"](around:{radius_m},{lat},{lon});',
                    f'nwr["healthcare"="clinic"](around:{radius_m},{lat},{lon});',
                    f'nwr["healthcare"="hospital"](around:{radius_m},{lat},{lon});',
                ]
            )
            for tag in spec_tags:
                filters.append(
                    f'nwr["healthcare:speciality"~"{tag}",i](around:{radius_m},{lat},{lon});'
                )
        query = f"[out:json][timeout:25];({''.join(filters)});out center tags 40;"

        data: dict[str, Any] | None = None
        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=35.0, headers={"User-Agent": USER_AGENT}) as client:
            for url in OVERPASS_URLS:
                try:
                    response = await client.post(url, data={"data": query})
                    response.raise_for_status()
                    data = response.json()
                    break
                except Exception as exc:
                    last_error = exc
                    continue
        if data is None:
            raise last_error or RuntimeError("Overpass returned no data")

        seen: set[str] = set()
        results: list[DoctorResult] = []
        for element in data.get("elements") or []:
            tags = element.get("tags") or {}
            name = (tags.get("name") or tags.get("operator") or "").strip()
            if not name:
                continue
            elat = element.get("lat") or (element.get("center") or {}).get("lat")
            elon = element.get("lon") or (element.get("center") or {}).get("lon")
            if elat is None or elon is None:
                continue
            key = f"{name}|{round(float(elat), 4)}|{round(float(elon), 4)}"
            if key in seen:
                continue
            seen.add(key)

            listed_specialty = _infer_specialty(tags, specialty)
            if specialty in PHARMACY_SPECIALTIES and listed_specialty != "pharmacist":
                continue
            if specialty not in PHARMACY_SPECIALTIES and listed_specialty == "pharmacist":
                continue

            opening = tags.get("opening_hours")
            phone = tags.get("phone") or tags.get("contact:phone")
            distance = round(haversine_km(lat, lon, float(elat), float(elon)), 2)
            maps_url = f"https://www.openstreetmap.org/?mlat={elat}&mlon={elon}#map=17/{elat}/{elon}"
            results.append(
                DoctorResult(
                    name=name,
                    specialty=listed_specialty,
                    address=_display_address(tags),
                    distance_km=distance,
                    phone=phone,
                    rating=None,
                    opening_hours=opening,
                    maps_url=maps_url,
                    source="openstreetmap",
                    osm_id=f"{element.get('type')}/{element.get('id')}",
                    matches_availability=_matches_availability(opening, payload.availability),
                )
            )

        results.sort(
            key=lambda item: (
                0 if item.matches_availability else 1,
                0 if specialty.split()[0] in (item.specialty or "").lower() else 1,
                item.distance_km if item.distance_km is not None else 999,
            )
        )
        return results[:20]

    async def _search_google(
        self,
        lat: float,
        lon: float,
        specialty: str,
        payload: DoctorRecommendRequest,
    ) -> list[DoctorResult]:
        keyword = specialty if specialty != "pharmacist" else "pharmacy"
        params = {
            "location": f"{lat},{lon}",
            "radius": int(payload.radius_km * 1000),
            "keyword": keyword,
            "key": self.google_key,
        }
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            body = response.json()
        status = body.get("status")
        if status not in {"OK", "ZERO_RESULTS"}:
            raise RuntimeError(body.get("error_message") or status)
        results: list[DoctorResult] = []
        for place in body.get("results") or []:
            loc = (place.get("geometry") or {}).get("location") or {}
            plat, plon = loc.get("lat"), loc.get("lng")
            distance = None
            if plat is not None and plon is not None:
                distance = round(haversine_km(lat, lon, float(plat), float(plon)), 2)
            place_id = place.get("place_id") or ""
            maps_url = (
                f"https://www.google.com/maps/search/?api=1&query={quote_plus(place.get('name') or '')}"
                + (f"&query_place_id={place_id}" if place_id else "")
            )
            opening = None
            if place.get("opening_hours"):
                opening = "Open now" if place["opening_hours"].get("open_now") else "Hours listed"
            results.append(
                DoctorResult(
                    name=place.get("name") or "Unnamed place",
                    specialty=specialty,
                    address=place.get("vicinity") or place.get("formatted_address") or "Address not listed",
                    distance_km=distance,
                    phone=None,
                    rating=place.get("rating"),
                    opening_hours=opening,
                    maps_url=maps_url,
                    source="google_places",
                    matches_availability=_matches_availability(opening, payload.availability),
                )
            )
        results.sort(key=lambda item: item.distance_km if item.distance_km is not None else 999)
        return results[:20]
