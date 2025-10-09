from typing import Type, Any, Generic, cast, Tuple

from sqladmin import action, ModelView
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.core.type_vars import T
from app.database.crud.mixines import GetBackNextIdMixin
from app.database import db_helper


class CustomModelView(ModelView, Generic[T]):
    repo_type: Type[GetBackNextIdMixin[T]]
    detail_columns_counts: dict[str, dict[str, int]] = {}

    @action(name="back", label="< Назад", add_in_detail=True, add_in_list=False)
    async def back_record(self, request: Request) -> RedirectResponse:
        redirect_url = await self._get_redirect_url(request, is_next=False)
        return RedirectResponse(redirect_url, status_code=303)

    @action(name="next", label="Вперёд >", add_in_detail=True, add_in_list=False)
    async def next_record(self, request: Request) -> RedirectResponse:
        redirect_url = await self._get_redirect_url(request)
        return RedirectResponse(redirect_url, status_code=303)

    async def _get_redirect_url(self, request: Request, is_next: bool = True) -> str:
        referer = request.headers.get("referer", "")
        current_id = request.query_params.get("pks")
        if not current_id:
            return referer
        async for session in db_helper.get_session():
            repo = self.repo_type(session)
            if column := self._get_default_sort()[0]:
                sort_column = column[0]
                current_val = getattr(
                    await repo.get_by_id(int(current_id)), sort_column
                )
            else:
                sort_column = "id"
                current_val = int(current_id)

            url_id = await repo.get_adjacent_id(
                current_val=current_val,
                list_query=cast(ModelView, self).list_query(request),
                sort_column=sort_column,
                is_next=is_next,
            )

            if url_id:
                last_slash_index = referer.rfind("/")
                redirect_url = referer[: last_slash_index + 1] + str(url_id)
                return redirect_url
        return referer

    async def get_count_items(self, request: Request) -> int | None:
        async for session in db_helper.get_session():
            repo = self.repo_type(session)
            user = request.session.get("user")
            conditions = []
            if hasattr(self.model, "user_id") and user and not user.get("is_superuser"):
                conditions.append(getattr(self.model, "user_id") == user.get("id"))
            return await repo.get_count_items(conditions)
        return None

    async def get_item_position(self, request: Request) -> dict[str, int | Any]:
        async for session in db_helper.get_session():
            current_id = request.path_params["pk"]
            repo = self.repo_type(session)

            if column := self._get_default_sort()[0]:
                is_desc = column[1]
                sort_column = column[0]
                current_val = getattr(
                    await repo.get_by_id(int(current_id)),
                    sort_column,
                )
            else:
                sort_column = "id"
                is_desc = False
                current_val = int(current_id)
            if (
                position := await repo.get_async_position(
                    target_val=current_val,
                    column=sort_column,
                    request=request,
                    is_desc=is_desc,
                )
            ) and hasattr(self, "page_size"):
                list_page = (position - 1) // self.page_size + 1
                return {"page": list_page, "item_position": position}
        return {"page": 1, "item_position": 0}

    async def get_page_for_url(self, request: Request) -> str | None:
        item_position = await self.get_item_position(request)
        page = item_position.get("page")
        return f"?page={page}"

    def get_detail_columns_count(self, name: str) -> dict[str, int]:
        return self.detail_columns_counts.get(
            name,
            {"count": 1, "width": 500},
        )

    async def check_restrictions_create(
        self, form_data_dict: dict[str, Any], request: Request | None = None
    ) -> str | None:
        pass

    async def check_restrictions_delete(self, request: Request) -> str | None:
        pass
