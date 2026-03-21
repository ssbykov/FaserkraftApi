from app.admin.custom_model_view import CustomModelView
from app.database.crud.size_type import SizeTypeRepository
from app.database.models import SizeType


class SizeTypeAdmin(
    CustomModelView[SizeType],
    model=SizeType,
):
    repo_type = SizeTypeRepository
    name_plural = "Типоразмеры"
    name = "Типоразмер"
    category = "Раздел процессов"

    column_list = ("name", "packaging_count")

    column_details_list = ("name", "packaging_count")

    column_labels = {
        "name": "Название",
        "packaging_count": "Количество в упаковке",
    }

    form_create_rules = [
        "name",
        "packaging_count",
    ]
    form_edit_rules = form_create_rules.copy()

    can_edit = True
    can_delete = True
    can_export = False
