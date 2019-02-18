#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Этот файл принадлежит проекту "VNetworkData".
Автор: Волков Семён.
"""
from enum import IntEnum, IntFlag, auto, unique

from PyQt5.QtCore import QObject, Qt, Q_ENUM, Q_FLAG


# TODO: Переименовать Vns в VNetworkData?
# Чтобы QML мог видеть наши перечисления, пришлось обернуть их классом, унаследованным от QObject.
class Vns(QObject):  # VNameSpace.
    """Пространство имен, определяющее перечисления."""

    # TODO: Необходимо запретить создание экземпляров данного класса каким-то более корректным способом!
    def __init__(self):
        raise RuntimeError("Vns is an enum container and can not be constructed.")

    @unique
    class ActionType(IntEnum):
        """Тип действия."""

        LoadingChildren = auto()
        """Загрузка подэлементов."""

        LoadingDetails = auto()
        """Загрузка подробных данных об элементе."""

        # LoadingBinaryFile = auto()
        # """Загрузка бинарных данных файла."""

        # ChangingItem = auto()
        # """Изменение элемента."""
        #
        # RemovingItem = auto()
        # """Удаление элемента."""

        Custom = 1000
        """Пользовательское действие."""

    Q_ENUM(ActionType)

    # @unique
    # class DetailsType(IntEnum):
    #     """Тип подробных данных об элементе."""
    #
    #     # BinaryFile = auto()
    #     # """Бинарные данные файла."""
    #
    #     Custom = 1000
    #     """Пользовательский тип информации об элементе."""
    #
    # Q_ENUM(DetailsType)

    @unique
    class ErrorType(IntEnum):
        """Тип ошибки."""

        NoError = auto()
        """Ошибки нет."""

        NetworkError = auto()
        """Ошибка сети или сервера."""

        # ModelError = auto()
        # """Ошибка модели.""" # TODO == Ошибка программиста?!

        UnknownError = auto()
        """Неизвестная ошибка."""

        CustomError = 1000
        """Первый тип ошибки, который может использоваться для обозначения пользовательских ошибок."""

    Q_ENUM(ErrorType)

    @unique
    class LoadingPolicy(IntFlag):
        """Политика загрузки данных."""

        DoNotLoad = int('0b0000', 2)  # 0
        """Без загрузки."""

        Manually = int('0b0001', 2)  # 1
        """Ручная."""

        Automatically = int('0b0010', 2)  # 2
        """Автоматическая.

        .. note::
           Порядок вызова автоматической загрузки подэлементов в моделях определен в представлениях, например, в
           :class:`PyQt5.QtCore.QAbstractItemView`.
           Представление использует методы модели `hasChildren()`, `canFetchMore()` и `fetchMore()`.
        """

        Combined = Automatically | Manually  # 3
        """Скомбинированная. То есть автоматическая или ручная одновременно."""

    Q_FLAG(LoadingPolicy)

    @unique
    class LoadingState(IntEnum):
        """Состояние загрузки данных."""

        Idle = auto()
        """Состояние покоя."""

        Loading = auto()
        """Загрузка."""

        Error = auto()
        """Ошибка. Загрузка завершилась неудачно."""

        Unknown = auto()
        """Неизвестно. Скорее всего означает, что данные впринципе не загружаемы."""

    Q_ENUM(LoadingState)

    @unique
    class PaginationType(IntEnum):
        """Тип пагинации."""

        Nothing = auto()
        """Без загрузки данных."""

        AllTogether = auto()
        """Загрузка всех данных вместе за один раз."""

        # EndlessAccumulation = auto()
        # """Бесконечная загрузка с накоплением данных."""

        # EndlessReplacement = auto()
        # """Бесконечная загрузка с заменой ранее загруженных данных на новые."""

        PagesAccumulation = auto()
        """Постраничная загрузка с накоплением загруженных страниц."""

        PagesReplacement = auto()
        """Постраничная загрузка с заменой предыдущей (ранее загруженной) страницы на новую."""

        # LimitOffset = auto()
        # """???"""

        # Cursor = auto()
        # """???"""

        Custom = 1000
        """Пользовательская пагинация."""

    Q_ENUM(PaginationType)

    @unique
    class ItemDataRole(IntEnum):
        """Роли элементов моделей."""

        First = Qt.UserRole + 1000
        """Первая зарезервированная роль."""

        ItemDict = auto()
        """Словарь элемента."""

        _ChildrenLoadingInfo = auto()
        """Контейнер со вспомогательной (служебной) информацией о загрузке подэлементов.

        .. warning:: 
            Только для внутреннего использования! 
            Эта роль не должна поддерживаться в методах модели `data()` и `_setData()`.
        """

        ChildrenAreLoadedSeparately = auto()
        """Загружаются ли подэлементы отдельно от родительского элемента. [Reed only]"""

        # TODO: Не хватает роли: HasLoadedChildren - "Имеются ли уже загруженные подэлементы".

        ChildrenLoadingPolicy = auto()
        """Политика загрузки подэлементов."""

        ChildrenLoadingState = auto()
        """Состояние загрузки подэлементов. [Reed only]"""

        ChildrenPagination = auto()
        """Пагинация подэлементов. [Reed only]"""

        _DetailsLoadingInfo = auto()
        """Контейнер со вспомогательной (служебной) информацией о загрузке подробных данных об элементе.

        .. warning:: 
            Только для внутреннего использования! 
            Эта роль не должна поддерживаться в методах модели `data()` и `_setData()`.
        """

        DetailsAreLoadedSeparately = auto()
        """Поддерживается ли загрузка подробных данных об элементе. [Reed only]"""

        DetailsAreLoaded = auto()
        """Загружены ли уже подробные данные об элементе. [Reed only]"""

        DetailsLoadingState = auto()
        """Состояние загрузки подробных данных об элементе. [Reed only]"""

        # Synced = auto()
        # """Синхронизирован ли элемент с сервером. Если нет, то над ним в данный момент производится операция изменения или удаления."""

        Custom = First + 1000
        """Первая роль, которая может использоваться для пользовательских или динамически создаваемых ролей."""

    Q_ENUM(ItemDataRole)
