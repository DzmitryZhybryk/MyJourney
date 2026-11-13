from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.journeys.application.ports.journey_repository import JourneyFilters
from app.journeys.application.schemas.commands import (
    CreateJourneyCommand,
    EstimateJourneyDistanceCommand,
    GetMovementsMapCommand,
    ListJourneysCommand,
    MoveJourneyCommand,
    UpdateJourneyCommand,
)
from app.journeys.application.services.journey import JourneyService
from app.journeys.presentation.dependencies import journey_service_dependency
from app.journeys.presentation.responses import (
    CREATE_JOURNEY_RESPONSES,
    DELETE_JOURNEY_RESPONSES,
    JOURNEY_DISTANCE_RESPONSES,
    JOURNEY_YEARS_RESPONSES,
    JOURNEYS_FEED_RESPONSES,
    JOURNEYS_GLOBE_RESPONSES,
    JOURNEYS_MAP_RESPONSES,
    MOVE_JOURNEY_RESPONSES,
    MOVEMENTS_MAP_RESPONSES,
    UPDATE_JOURNEY_RESPONSES,
)
from app.journeys.presentation.schemas import (
    CreateJourneyRequest,
    JourneyDistanceRequest,
    JourneyDistanceResponse,
    JourneysFeedRequest,
    JourneysFeedResponse,
    JourneysGlobeResponse,
    JourneysMapResponse,
    JourneyYearsResponse,
    MoveJourneyRequest,
    MoveJourneyResponse,
    MovementsMapFilterRequest,
    MovementsMapResponse,
    UpdateJourneyRequest,
)
from app.shared.infra.jwt.dependency import current_user_id_dependency
from app.shared.pagination import PageQuery

journey_router = APIRouter()


@journey_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    responses=CREATE_JOURNEY_RESPONSES,
)
async def create_journey(
    *,
    body: CreateJourneyRequest,
    user_id: Annotated[UUID, Depends(current_user_id_dependency)],
    journey_service: Annotated[JourneyService, Depends(journey_service_dependency)],
) -> Response:
    command = CreateJourneyCommand(
        origin_city_id=body.origin_city_id,
        destination_city_id=body.destination_city_id,
        transport_type=body.transport_type,
        traveled_year=body.traveled_year,
    )
    await journey_service.create_journey(user_id=user_id, command=command)
    return Response(status_code=status.HTTP_201_CREATED)


@journey_router.put(
    "/{journey_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=UPDATE_JOURNEY_RESPONSES,
)
async def update_journey(
    *,
    journey_id: UUID,
    body: UpdateJourneyRequest,
    user_id: Annotated[UUID, Depends(current_user_id_dependency)],
    journey_service: Annotated[JourneyService, Depends(journey_service_dependency)],
) -> Response:
    command = UpdateJourneyCommand(
        origin_city_id=body.origin_city_id,
        destination_city_id=body.destination_city_id,
        transport_type=body.transport_type,
        traveled_year=body.traveled_year,
    )
    await journey_service.update_journey(user_id=user_id, journey_id=journey_id, command=command)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@journey_router.delete(
    "/{journey_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=DELETE_JOURNEY_RESPONSES,
)
async def delete_journey(
    *,
    journey_id: UUID,
    user_id: Annotated[UUID, Depends(current_user_id_dependency)],
    journey_service: Annotated[JourneyService, Depends(journey_service_dependency)],
) -> Response:
    await journey_service.delete_journey(user_id=user_id, journey_id=journey_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@journey_router.post(
    "/{journey_id}/move/",
    response_model=MoveJourneyResponse,
    responses=MOVE_JOURNEY_RESPONSES,
)
async def move_journey(
    *,
    journey_id: UUID,
    body: MoveJourneyRequest,
    user_id: Annotated[UUID, Depends(current_user_id_dependency)],
    journey_service: Annotated[JourneyService, Depends(journey_service_dependency)],
) -> MoveJourneyResponse:
    command = MoveJourneyCommand(neighbor_journey_id=body.neighbor_journey_id, placement=body.placement)
    result = await journey_service.move_journey(user_id=user_id, journey_id=journey_id, command=command)
    return MoveJourneyResponse.model_validate(result, from_attributes=True)


@journey_router.get(
    "/distance/",
    response_model=JourneyDistanceResponse,
    responses=JOURNEY_DISTANCE_RESPONSES,
    dependencies=[Depends(current_user_id_dependency)],
)
async def estimate_journey_distance(
    *,
    query: Annotated[JourneyDistanceRequest, Query()],
    journey_service: Annotated[JourneyService, Depends(journey_service_dependency)],
) -> JourneyDistanceResponse:
    command = EstimateJourneyDistanceCommand(
        origin_city_id=query.origin_city_id,
        destination_city_id=query.destination_city_id,
    )
    result = await journey_service.estimate_journey_distance(command=command)
    return JourneyDistanceResponse.model_validate(result, from_attributes=True)


@journey_router.get(
    "/",
    response_model=JourneysFeedResponse,
    responses=JOURNEYS_FEED_RESPONSES,
)
async def list_journeys(
    *,
    query: Annotated[JourneysFeedRequest, Query()],
    user_id: Annotated[UUID, Depends(current_user_id_dependency)],
    journey_service: Annotated[JourneyService, Depends(journey_service_dependency)],
) -> JourneysFeedResponse:
    command = ListJourneysCommand(
        page=PageQuery(cursor=query.cursor, limit=query.limit),
        filters=JourneyFilters(
            year_from=query.year_from,
            year_to=query.year_to,
            transport_types=query.transport_type,
        ),
    )
    result = await journey_service.list_journeys(user_id=user_id, command=command)
    return JourneysFeedResponse.model_validate(result, from_attributes=True)


@journey_router.get(
    "/years/",
    response_model=JourneyYearsResponse,
    responses=JOURNEY_YEARS_RESPONSES,
)
async def get_journey_years(
    *,
    user_id: Annotated[UUID, Depends(current_user_id_dependency)],
    journey_service: Annotated[JourneyService, Depends(journey_service_dependency)],
) -> JourneyYearsResponse:
    result = await journey_service.get_journey_years(user_id=user_id)
    return JourneyYearsResponse.model_validate(result, from_attributes=True)


@journey_router.get(
    "/map/",
    response_model=JourneysMapResponse,
    responses=JOURNEYS_MAP_RESPONSES,
)
async def get_journeys_map(
    *,
    user_id: Annotated[UUID, Depends(current_user_id_dependency)],
    journey_service: Annotated[JourneyService, Depends(journey_service_dependency)],
) -> JourneysMapResponse:
    result = await journey_service.get_journeys_map(user_id=user_id)
    return JourneysMapResponse.model_validate(result, from_attributes=True)


@journey_router.get(
    "/globe/",
    response_model=JourneysGlobeResponse,
    responses=JOURNEYS_GLOBE_RESPONSES,
)
async def get_journeys_globe(
    *,
    user_id: Annotated[UUID, Depends(current_user_id_dependency)],
    journey_service: Annotated[JourneyService, Depends(journey_service_dependency)],
) -> JourneysGlobeResponse:
    result = await journey_service.get_journeys_globe(user_id=user_id)
    return JourneysGlobeResponse.model_validate(result, from_attributes=True)


@journey_router.get(
    "/movements/",
    response_model=MovementsMapResponse,
    responses=MOVEMENTS_MAP_RESPONSES,
)
async def get_movements_map(
    *,
    filters: Annotated[MovementsMapFilterRequest, Query()],
    user_id: Annotated[UUID, Depends(current_user_id_dependency)],
    journey_service: Annotated[JourneyService, Depends(journey_service_dependency)],
) -> MovementsMapResponse:
    command = GetMovementsMapCommand(transport_types=filters.transport_type)
    result = await journey_service.get_movements_map(user_id=user_id, command=command)
    return MovementsMapResponse.model_validate(result, from_attributes=True)
