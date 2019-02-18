#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Этот файл принадлежит проекту "VNetworkData".
Автор: Волков Семён.
"""
import json
import traceback

from typing import Any, Dict, List

from PyQt5.QtCore import QAbstractItemModel, QModelIndex, QObject, Qt, pyqtProperty
from PyQt5.QtGui import QStandardItem, QStandardItemModel

from .action import VNetworkModelAction
from .mixin import VAbstractNetworkDataModelMixin, VChildrenLoadingInfo, VDetailsLoadingInfo
from .namespace import Vns
from .pagination import VAllTogetherPagination


class VAbstractNetworkDataModel(VAbstractNetworkDataModelMixin, QAbstractItemModel):
    """Абстрактная модель, позволяющая загружать свои данные по сети.

    Базовая реализация класса содержит 1 столбец.

    В режиме `release` базовая реализация не отображает никаких данных.
    В режиме `debug` в каждой строке единственного столбца отображается текст "debug: [the item]".

    Все загруженные элементы всегда располагаются в нулевом столбце и содержат свои загруженные данные в словарях,
    хранимых в самих элементах под ролью `Vns.ItemDataRole.ItemDict`.

    Для минимальной реализации reed-only модели классам-наследникам необходимо определить абстрактный метод
    :func:`_requestToLoadingChildren()`.

    Загрузка подэлементов.
    ~~~~~~~~~~~~~~~~~~~~~~

    Базовая реализация загружает только списочную модель, то есть загружает подэлементы только из корня модели
    (который имеет некорректный модельный индекс) и создает только один уровень подэлементов.

    Чтобы создавать большее количество уровней подэлементов в одном действии загрузки подэлементов, наследники класса
    могут переопределить метод :func:`_getListOfDictsForChildren()`.

    Чтобы загружать подэлементы из элементов с корректными индексами в отдельных действиях загрузки подэлементов (также
    отдельно от корня модели), наследники класса могут переопределить метод :func:`_createItem()`, установив в данные
    элементов экземпляры :class:`VChildrenLoadingInfo` для соответствующей роли `Vns.ItemDataRole._ChildrenLoadingInfo`.

    Переопределять можно и сразу оба указанных метода, и только один из них.

    Если вследствие переопределения обоих методов получится так, что на одном уровне будут содержаться подэлементы,
    загруженные из разных элементов-предков, то классам-наследникам также будет необходимо переопределить метод
    :func:`_removeChildren()`.

    Например, если сырые словари подэлементов, получаемые после обработки ответов от сервера, имеют следующий вид:

    .. sourcecode::

        {
            "id": 1,
            "type": "A",
            "childrenWithTypeB": [
                {
                    "id": 2,
                    "type": "B",
                    ...
                },
                ...
            ],
            "hasChildrenWithTypeC": True,
            ...
        }

    и

    .. sourcecode::

        {
            "id": 3,
            "type": "С",
            ...
        }

    и если переопределить указанные методы таким образом:

    .. sourcecode::

        # from typing import List
        # from VNetworkData import VAllTogetherPagination, VChildrenLoadingInfo, Vns

        def _getListOfDictsForChildren(self, rawDict: dict) -> List[dict]:
            if rawDict["type"] == "A":
                return rawDict["childrenWithTypeB"]
            return []

        def _createItem(self, rawDict: dict, columns: int = None) -> QStandardItem:
            item = super()._createItem(rawDict, columns)
            if rawDict["type"] == "A":
                if rawDict["hasChildrenWithTypeC"] == True:
                    info = VChildrenLoadingInfo(Vns.LoadingPolicy.Automatically, VAllTogetherPagination())
                    item.setData(info, Vns.ItemDataRole._ChildrenLoadingInfo)
            return item

        def _removeChildren(self, parent: QModelIndex):
            if not parent.isValid():
                # Удаляем все подэлементы.
                super()._removeChildren(parent)
            parentDict = self.data(parent, Vns.ItemDataRole.ItemDict)
            assert isinstance(parentDict, dict)
            if parentDict["type"] != "A":
                # Удаляем все подэлементы.
                super()._removeChildren(parent)
            firsrRow = 0
            rowCount = self.rowCount(parent)
            for row in range(rowCount - 1, firsrRow - 1, -1):
                index = self.index(row, self.ZERO_COLUMN, parent)
                assert index.isValid()
                itemDict = self.data(index, Vns.ItemDataRole.ItemDict)
                assert isinstance(itemDict, dict)
                if itemDict["type"] == "C":
                    # То есть если элемент с индексом `index` был загружен из элемента с индексом `parent`.
                    ok = self._removeRow(row, parent)
                    assert ok

    а затем выполнить загрузку подэлементов из корня модели, то дерево модели будет выглядеть так:

    .. sourcecode::

        |- {"id": 1, "type": "A", ...}
        |    |- {"id": 2, "type": "B", ...}
        |    |- ...
        |- ...

    Если затем выполнить загрузку подэлементов из элемента `{"id": 1, "type": "A", ...}`, то дерево модели примет вид:

    .. sourcecode::

        |- {"id": 1, "type": "A", ...}
        |    |- {"id": 2, "type": "B", ...}
        |    |- ...
        |    |- {"id": 3, "type": "С", ...}
        |    |- ...
        |- ...

    Загрузка подробных данных об элементах.
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Базовая реализация не загружает подробные данные об элементах.

    Чтобы загружать подробные данные об элементах, наследники класса должны переопределить метод
    :func:`_requestToLoadingDetails()` и установить в данные элементов экземпляры :class:`VDetailsLoadingInfo` для
    соответствующей роли `Vns.ItemDataRole._DetailsLoadingInfo`.
    Для этого наследники класса могут переопределить метод :func:`_createItem()`.
    Например:

    .. sourcecode::

        # from VNetworkData import VAllTogetherPagination, VChildrenLoadingInfo, Vns
        def _createItem(self, rawDict: dict, columns: int = None) -> QStandardItem:
            item = super()._createItem(rawDict, columns)
            if rawDict["hasDetails"] == True:
                info = VDetailsLoadingInfo()
                item.setData(info, Vns.ItemDataRole._DetailsLoadingInfo)
            return item
    """

    # class Columns:
    #     ItemDictColumn = 0  # В этом столбце хранится словарь с данными элемента.
    #     ColumnCount = 1  # Количество столбцов.
    #
    # Q_ENUM(Columns)

    # TODO: Вынести сетевой клиент в наследников?!
    # networkClientChanged = pyqtSignal(VAbstractNetworkClient, arguments=['client'])
    # """Сигнал об изменении сетевого клиента.
    #
    # :param VAbstractNetworkClient client: Новый сетевой клиент.
    # """
    #
    # def getNetworkClient(self) -> VAbstractNetworkClient:
    #     """Возвращает сетевой клиент, обеспечивающий взаимодействие с сервером."""
    #     return self.__networkClient
    #
    # def setNetworkClient(self, client: VAbstractNetworkClient):
    #     """Устанавливает сетевой клиент, обеспечивающий взаимодействие с сервером."""
    #     if self.__networkClient == client:
    #         return
    #     self.__networkClient = client
    #     self.networkClientChanged.emit(client)
    #
    # networkClient = pyqtProperty(type=VAbstractNetworkClient, fget=getNetworkClient, fset=setNetworkClient,
    #         notify=networkClientChanged, doc="Сетевой клиент, обеспечивающий взаимодействие с сервером.")

    ZERO_COLUMN = 0

    def __init__(self, parent: QObject = None):
        super().__init__(parent)

        # TODO: Вынести сетевой клиент в наследников?!
        # self.__networkClient = None

        self.__rootChildrenLoadingInfo = self._createRootChildrenLoadingInfo()
        self.__localDataModel = self._createLocalDataModel()

    def _createRootChildrenLoadingInfo(self) -> VChildrenLoadingInfo:
        """Создает и возвращает контейнер со вспомогательной (служебной) информацией о загрузке подэлементов
        корня модели.

        .. note::
            Метод создан для того, чтобы наследники класса могли переопределить его и использовать собственный
            контейнер со вспомогательной (служебной) информацией о загрузке подэлементов корня модели.
        """
        return VChildrenLoadingInfo(policy=Vns.LoadingPolicy.Manually, pagination=VAllTogetherPagination())

    def _createLocalDataModel(self) -> QStandardItemModel:
        """Создает и возвращает модель, хранящую локальные данные.

        .. note::
            Метод создан для того, чтобы наследники класса могли переопределить его и использовать собственную модель
            для хранения локальных данных.
        """
        rows, columns, parent = 0, 1, self
        return QStandardItemModel(rows, columns, parent)

    def _getLocalDataModel(self) -> QStandardItemModel:
        """Возвращает модель, хранящую локальные данные."""
        return self.__localDataModel

    # TODO: Переименовать геттер, избавиться от свойства.
    _localDataModel = pyqtProperty(type=QStandardItemModel, fget=_getLocalDataModel,
            doc="Модель, хранящая локальные данные. [Reed only]")

    def _mapFromLocal(self, index: QModelIndex) -> QModelIndex:
        """Возвращает индекс из текущей модели для соответствующего индекса `index` из модели с локальными данными."""
        if not index.isValid():
            return QModelIndex()
        assert index.model() is self.__localDataModel
        return self.createIndex(index.row(), index.column(), index.internalId())

    def _mapToLocal(self, index: QModelIndex) -> QModelIndex:
        """Возвращает индекс из модели с локальными данными для соответствующего индекса `index` из текущей модели."""
        if not index.isValid():
            return QModelIndex()
        assert index.model() is self
        return self.__localDataModel.createIndex(index.row(), index.column(), index.internalId())

    # def _mapSelectionFromLocal(self, selection: QItemSelection) -> QItemSelection:
    #     """Возвращает выбор из текущей модели для соответствующего выбора `selection` из модели с локальными данными."""
    #     result = QItemSelection()
    #     for selectionRange in selection:
    #         assert isinstance(selectionRange, QItemSelectionRange)
    #         assert selectionRange.model() is self.__localDataModel
    #         topLeft = QModelIndex(selectionRange.topLeft())
    #         bottomRight = QModelIndex(selectionRange.bottomRight())
    #         result.append(QItemSelectionRange(self._mapFromLocal(topLeft), self._mapFromLocal(bottomRight)))
    #     return result
    #
    # def _mapSelectionToLocal(self, selection: QItemSelection) -> QItemSelection:
    #     """Возвращает выбор из модели с локальными данными для соответствующего выбора `selection` из текущей модели."""
    #     result = QItemSelection()
    #     for selectionRange in selection:
    #         assert isinstance(selectionRange, QItemSelectionRange)
    #         assert selectionRange.model() is self
    #         topLeft = QModelIndex(selectionRange.topLeft())
    #         bottomRight = QModelIndex(selectionRange.bottomRight())
    #         result.append(QItemSelectionRange(self._mapToLocal(topLeft), self._mapToLocal(bottomRight)))
    #     return result

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Переопределяет соответствующий родительский метод."""
        assert parent.model() is self if parent.isValid() else True  # assert self.checkIndex(parent)
        return self.__localDataModel.columnCount(self._mapToLocal(parent))

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Переопределяет соответствующий родительский метод."""
        assert parent.model() is self if parent.isValid() else True  # assert self.checkIndex(parent)
        return self.__localDataModel.rowCount(self._mapToLocal(parent))

    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        """Переопределяет соответствующий родительский метод."""
        assert parent.model() is self if parent.isValid() else True  # assert self.checkIndex(parent, self.DoNotUseParent)
        sourceParent = self._mapToLocal(parent)
        sourceIndex = self.__localDataModel.index(row, column, sourceParent)
        return self._mapFromLocal(sourceIndex)

    def parent(self, index: QModelIndex = None) -> QModelIndex or QObject:
        """Переопределяет соответствующий родительский метод.

        parent(self, index: QModelIndex) -> QModelIndex
        parent(self) -> QObject
        """
        if index is None:
            return super().parent()

        assert index.model() is self if index.isValid() else True  # assert self.checkIndex(parent, self.DoNotUseParent)
        localIndex = self._mapToLocal(index)
        localParent = self.__localDataModel.parent(localIndex)
        return self._mapFromLocal(localParent)

    def sibling(self, row: int, column: int, index: QModelIndex) -> QModelIndex:
        """Переопределяет соответствующий родительский метод."""
        # assert index.model() is self if index.isValid() else True  # assert self.checkIndex(parent)
        return self._mapFromLocal(self.__localDataModel.sibling(row, column, self._mapToLocal(index)))

    # def buddy(self, index: QModelIndex) -> QModelIndex:
    #     """Переопределяет соответствующий родительский метод."""
    #     # assert index.model() is self if index.isValid() else True  # assert self.checkIndex(parent)
    #     return self._mapFromLocal(self.__localDataModel.buddy(self._mapToLocal(index)))
    #
    # # def buddy(self, index: QModelIndex) -> QModelIndex:
    # #     """Переопределяет соответствующий родительский метод.
    # #
    # #     buddy(self, index: QModelIndex) -> QModelIndex
    # #     """
    # #     # return super().buddy(index)
    # #     return self.sibling(index.row(), self.ZERO_COLUMN, index)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        """Переопределяет соответствующий родительский метод."""
        # if role is None:
        #     role = Qt.DisplayRole
        return self.__localDataModel.headerData(section, orientation, role)

    def setHeaderData(self, section: int, orientation: Qt.Orientation, value: Any, role: int = Qt.EditRole) -> bool:
        """Переопределяет соответствующий родительский метод."""
        # if role is None:
        #     role = Qt.EditRole
        return self.__localDataModel.setHeaderData(section, orientation, value, role)

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Переопределяет соответствующий родительский метод.

        flags(self, QModelIndex) -> Qt.ItemFlags
        """
        assert self.checkIndex(index)
        flags = self.__localDataModel.flags(self._mapToLocal(index))
        if flags & Qt.ItemIsEditable:
            flags ^= Qt.ItemIsEditable
        return flags

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        """Переопределяет соответствующий родительский метод.

        data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any
        """
        assert self.checkIndex(index)

        # if role is None:
        #     role = Qt.DisplayRole

        if role == Vns.ItemDataRole.ItemDict:
            assert index.isValid()
            indexWithZeroColumn = self.sibling(index.row(), self.ZERO_COLUMN, index)
            return self.__localDataModel.data(self._mapToLocal(indexWithZeroColumn), role)
        elif role == Vns.ItemDataRole._ChildrenLoadingInfo:
            return None
        elif role == Vns.ItemDataRole.ChildrenAreLoadedSeparately:
            return self.childrenAreLoadedSeparately(index)
        elif role == Vns.ItemDataRole.ChildrenLoadingPolicy:
            return self.childrenLoadingPolicy(index)  # if self.childrenAreLoadedSeparately(index) else None
        elif role == Vns.ItemDataRole.ChildrenLoadingState:
            return self.childrenLoadingState(index)  # if self.childrenAreLoadedSeparately(index) else None
        elif role == Vns.ItemDataRole.ChildrenPagination:
            return self.childrenPagination(index)  # if self.childrenAreLoadedSeparately(index) else None
        elif role == Vns.ItemDataRole._DetailsLoadingInfo:
            return None
        elif role == Vns.ItemDataRole.DetailsAreLoadedSeparately:
            return self.detailsAreLoadedSeparately(index)
        elif role == Vns.ItemDataRole.DetailsAreLoaded:
            return self.hasLoadedDetails(index)  # if self.detailsAreLoadedSeparately(index) else None
        elif role == Vns.ItemDataRole.DetailsLoadingState:
            return self.detailsLoadingState(index)  # if self.detailsAreLoadedSeparately(index) else None

        assert not (Vns.ItemDataRole.First <= role < Vns.ItemDataRole.Custom)

        if __debug__ and role == Qt.DisplayRole and index.isValid() and index.column() == self.ZERO_COLUMN:
            # Этот костыль нужен, чтобы в представлении отображались хоть какие-то данные в режиме отладки.
            return "debug: [the item]"

        return self.__localDataModel.data(self._mapToLocal(index), role)

    def _setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        """Устанавливает локальные данные.

        _setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool
        """
        assert self.checkIndex(index)

        # if role is None:
        #     role = Qt.EditRole

        if role == Vns.ItemDataRole.ItemDict:
            assert index.isValid()
            assert isinstance(value, dict)
            indexWithZeroColumn = self.sibling(index.row(), self.ZERO_COLUMN, index)
            if self.__localDataModel.setData(self._mapToLocal(indexWithZeroColumn), value, role):
                indexWithLastColumn = self.sibling(index.row(), self.columnCount(index.parent()) - 1, index)
                self.dataChanged.emit(indexWithZeroColumn, indexWithLastColumn, [])
                return True
            return False
        elif role == Vns.ItemDataRole._ChildrenLoadingInfo:
            return False
        elif role == Vns.ItemDataRole.ChildrenAreLoadedSeparately:
            return False
        elif role == Vns.ItemDataRole.ChildrenLoadingPolicy:
            assert isinstance(value, Vns.LoadingPolicy)
            # TODO: Для какого индекса надо устанавливать политику: для index или для indexWithZeroColumn?
            if self.setChildrenLoadingPolicy(value, index):
                # TODO: Какие индексы должны быть в сигнале?
                self.dataChanged.emit(index, index, [role])
                return True
            return False
        elif role == Vns.ItemDataRole.ChildrenLoadingState:
            return False
        elif role == Vns.ItemDataRole.ChildrenPagination:
            return False
        elif role == Vns.ItemDataRole._DetailsLoadingInfo:
            return False
        elif role == Vns.ItemDataRole.DetailsAreLoadedSeparately:
            return False
        elif role == Vns.ItemDataRole.DetailsAreLoaded:
            return False
        elif role == Vns.ItemDataRole.DetailsLoadingState:
            return False

        assert not (Vns.ItemDataRole.First <= role < Vns.ItemDataRole.Custom)

        if role == Qt.DisplayRole or role == Qt.EditRole:
            return False

        return self.__localDataModel.setData(self._mapToLocal(index), value, role)

    # def sendData(self, index: QModelIndex, value, role=None) -> VAbstractAsynchronousAction:
    #     """Запускает асинхронное изменение данных по сети в удаленном хранилище.
    #
    #     sendData(self, index: QModelIndex, value: dict) -> VAbstractAsynchronousAction.
    #     sendData(self, index: QModelIndex, value: Any, role: int) -> VAbstractAsynchronousAction.
    #     sendData(self, index: QModelIndex, value: Any, role: str) -> VAbstractAsynchronousAction.
    #     sendData(self, index: QModelIndex, value: Any, role: list[str]) -> VAbstractAsynchronousAction.
    #
    #     В базовой реализации ничего не делает и возвращает действие, которое сразу испустит сигнал завершения с ошибкой.
    #     """
    #     assert isinstance(index, QModelIndex)  # Это только чтобы хоть как-то использовать аргумент.
    #     assert isinstance(value, object)  # Это только чтобы хоть как-то использовать аргумент.
    #     assert isinstance(role, object)  # Это только чтобы хоть как-то использовать аргумент.
    #     return self._createAction()

    # def hasChildren(self, parent: QModelIndex = QModelIndex()) -> bool:
    #     """Переопределяет соответствующий родительский метод."""
    #     if self.childrenAreLoadedSeparately(parent):
    #         return True
    #     return super().hasChildren(parent)
    #
    # def canFetchMore(self, parent: QModelIndex) -> bool:
    #     """Переопределяет соответствующий родительский метод.
    #
    #     Возвращает True - если в данный момент можно запустить АВТОМАТИЧЕСКУЮ загрузку следующей порции подэлементов
    #     из элемента с модельным индексом `parent`, иначе - возвращает False.
    #
    #     .. note::
    #         Данный метод автоматически вызывается в представлениях, например, в :class:`PyQt5.QtCore.QAbstractItemView`.
    #     """
    #     assert isinstance(self, QAbstractItemModel) and isinstance(self, VAbstractNetworkDataModelMixin)
    #     return self._canLoadNextChildren(parent, Vns.LoadingPolicy.Automatically)
    #
    # def fetchMore(self, parent: QModelIndex):
    #     """Переопределяет соответствующий родительский метод.
    #
    #     Запускает АВТОМАТИЧЕСКУЮ асинхронную загрузку следующей порции подэлементов из элемента с модельным индексом
    #     `parent`.
    #
    #     .. warning::
    #         Перед вызовом данного метода необходимо убедиться, что вызов метода :func:`canFetchMore()` возвращает True.
    #
    #     .. note::
    #         Данный метод автоматически вызывается в представлениях, например, в :class:`PyQt5.QtCore.QAbstractItemView`.
    #     """
    #     assert isinstance(self, QAbstractItemModel) and isinstance(self, VAbstractNetworkDataModelMixin)
    #     self.loadNextChildren(parent)

    def _getChildrenLoadingInfo(self, index: QModelIndex = QModelIndex()) -> VChildrenLoadingInfo or None:
        """Переопределяет соответствующий родительский метод.

        Возвращает контейнер со вспомогательной (служебной) информацией о загрузке подэлементов элемента
        с модельным индексом `index`.

        .. note::
            Если загрузка подэлементов не поддерживается из элемента с модельным индексом `index`, возвращает None.

        .. note::
            Базовая реализация гарантированно возвращает экземпляр :class:`VChildrenLoadingInfo` для корня модели,
            то есть для случая с некорректным модельным индексом `index`.

            Результат этого метода для случаев с корректным модельным индексом `index` зависит от того, установлен ли
            экземпляр :class:`VChildrenLoadingInfo` в элемент, соответствующий этому модельному индексу.

            Смотри описание метода :func:`_createItem()`.
        """
        if not index.isValid():
            return self.__rootChildrenLoadingInfo

        indexWithZeroColumn = self.sibling(index.row(), self.ZERO_COLUMN, index)
        return self.__localDataModel.data(self._mapToLocal(indexWithZeroColumn), Vns.ItemDataRole._ChildrenLoadingInfo)

    # def clear(self):
    #     """Сбрасывает модель в незагруженное состояние."""
    #     self.unsubscribeFromChildrenExternalChanges(QModelIndex())
    #     self._removeChildren(QModelIndex())
    #     pagination = self.childrenPagination(QModelIndex())
    #     pagination._resetWhenReloadingData()
    #     pagination.resetLoadingState()
    #     pagination.resetIsInReloading()

    def _removeRow(self, row: int, parent: QModelIndex = QModelIndex()) -> bool:
        """Удаляет строку `row` из элемента с модельным индексом `parent`.
        Возвращает True - если удаление удалось, False - иначе.
        """
        return self._removeRows(row, 1, parent)

    def _removeRows(self, first: int, count: int, parent: QModelIndex = QModelIndex()) -> bool:
        """Удаляет `count` строк, начиная с `first` включительно, из элемента с модельным индексом `parent`.
        Возвращает True - если удаление удалось, False - иначе.
        """
        assert first >= 0
        if first < 0:
            return False
        assert count >= 0
        if count < 0:
            return False
        if count == 0:
            return True
        last = first + count - 1
        localParent = self._mapToLocal(parent)
        assert last < self.__localDataModel.rowCount(localParent)
        self.beginRemoveRows(parent, first, last)
        ok = self.__localDataModel.removeRows(first, count, localParent)
        assert ok
        self.endRemoveRows()
        return True

    def _removeChildren(self, parent: QModelIndex):
        """Переопределяет соответствующий родительский метод.

        Удаляет загруженные подэлементы элемента с модельным индексом `parent`.
        """
        # localParent = self._mapToLocal(parent)
        # count = self.__localDataModel.rowCount(localParent)
        # if not count:
        #     return
        # first = 0
        # last = first + count - 1
        # self.beginRemoveRows(parent, first, last)
        # ok = self.__localDataModel.removeRows(first, count, localParent)
        # assert ok
        # self.endRemoveRows()
        first = 0
        count = self.rowCount(parent)
        ok = self._removeRows(first, count, parent)
        assert ok

    def _appendChildren(self, parent: QModelIndex, action: VNetworkModelAction) -> bool:
        """Переопределяет соответствующий родительский метод.

        Создает элементы, используя данные из действия `action`, и добавляет их в качестве подэлементов
        в элемент с модельным индексом `parent`.

        Возвращает True - если создание и вставка завершились успешно, иначе - возвращает False.
        """
        listOfDicts = self.convertToListOfDicts(action.replyBodyStringData())
        return self._appendChildrenRows(parent, listOfDicts)

    def convertToListOfDicts(self, string: str) -> List[dict]:
        """Преобразует строку `string` в список сырых словарей и возвращает его.

        .. note:: В базовой реализации используется json.
        """
        if not string:
            print("{}: VAbstractNetworkDataModel.convertToListOfDicts(): ERROR! String is empty.".format(type(self)))  # TODO: Исправить вывод ошибки.
            return []

        lst = json.loads(string)
        if isinstance(lst, dict):
            lst = [lst]
        assert isinstance(lst, list)
        return lst

    def _appendChildrenRow(self, parent: QModelIndex, rawDict: dict) -> bool:
        """Создает элемент из сырого словаря `rawDict` и добавляет его в качестве подэлемента в элемент
        с модельным индексом `parent`.

        Возвращает True - если создание и вставка завершились успешно, иначе - возвращает False.
        """
        return self._appendChildrenRows(parent, [rawDict])

    def _appendChildrenRows(self, parent: QModelIndex, listOfDicts: List[dict]) -> bool:
        """Создает элементы из списка сырых словарей `listOfDicts` и добавляет их в качестве подэлементов в элемент
        с модельным индексом `parent`.

        Возвращает True - если создание и вставка завершились успешно, иначе - возвращает False.
        """
        # assert parent.column() == self.ZERO_COLUMN if parent.isValid() else True
        if not parent.isValid():
            parentItem = self.__localDataModel.invisibleRootItem()
        else:
            parentItem = self.__localDataModel.itemFromIndex(self._mapToLocal(parent))

        if parentItem is None:
            return False

        try:
            return self._appendChildrenRowsToItem(parentItem, listOfDicts, True)
        except:
            print(traceback.format_exc())
            return False

    def _appendChildrenRowsToItem(self, item: QStandardItem, listOfDicts: List[dict], emitSignals: bool) -> bool:
        """Создает элементы из списка сырых словарей `listOfDicts` и добавляет их в качестве подэлементов в элемент
        `item`.

        Возвращает True - если создание и вставка завершились успешно, иначе - возвращает False.
        """
        assert item
        columns = item.columnCount()
        if columns < 1:
            columns = 1

        rows = []
        for rawDict in listOfDicts:
            assert isinstance(rawDict, dict)
            childItem = self._createItemsTree(rawDict, columns)
            if childItem:
                rows.append(childItem)
        if rows:
            if emitSignals:
                parent = self._mapFromLocal(self.__localDataModel.indexFromItem(item))
                first = item.rowCount()
                last = first + len(rows) - 1
                self.beginInsertRows(parent, first, last)
            item.appendRows(self._sortChildrenItems(rows))
            if emitSignals:
                self.endInsertRows()
        return True

    def _createItemsTree(self, rawDict: dict, columns: int = None) -> QStandardItem or None:
        """Создает и возвращает дерево из элемента с подэлементами на основе сырого словаря `rawDict`.
        Если элемент создать невозможно - возвращает None.

        :param columns: Рекомендуемое количество столбцов для подэлементов - количество столбцов родительского элемента.
                        Если не задано, то берется количество столбцов корневого элемента (т.е. самой модели).
        """
        item = self._createItem(rawDict, columns)
        if item:
            listOfChildren = self._getListOfDictsForChildren(rawDict)
            if listOfChildren:
                assert isinstance(listOfChildren, list)
                self._appendChildrenRowsToItem(item=item, listOfDicts=listOfChildren, emitSignals=False)
        return item

    def _createItem(self, rawDict: dict, columns: int = None) -> QStandardItem or None:
        """Создает и возвращает элемент на основе сырого словаря `rawDict`.
        Если элемент создать невозможно - возвращает None.

        .. warning::
            Базовая реализация не устанавливает в элемент ни экземпляр :class:`VChildrenLoadingInfo`,
            ни экземпляр :class:`VDetailsLoadingInfo`.

            Наследники класса могут переопределить этот метод и установить в элемент:
              - экземпляр :class:`VChildrenLoadingInfo` - чтобы позволить загружать подэлементы элемента.
              - экземпляр :class:`VDetailsLoadingInfo` - чтобы позволить загружать подробные данные об элементе.
            # TODO: Только при этом еще надо и другие методы переопределить!

        :param columns: Рекомендуемое количество столбцов для подэлементов - количество столбцов родительского элемента.
                        Если не задано, то берется количество столбцов корневого элемента (т.е. самой модели).
        """
        if columns is None:
            columns = self.columnCount()
            if columns < 1:
                columns = 1
        item = QStandardItem()  # self.__localDataModel.itemPrototype()
        item.setData(self._prepareItemDict(rawDict), role=Vns.ItemDataRole.ItemDict)
        item.setColumnCount(columns)
        # item.setFlags(item.flags() ^ Qt.ItemIsEditable)
        return item

    def _prepareItemDict(self, rawDict: dict) -> dict:
        """Осуществляет обработку сырого словаря `rawDict`, содержащего данные элемента
        и возвращает обработанный словарь.

        .. note:: В базовой реализации возвращает оригинальный словарь.
        """
        return rawDict

    def _getListOfDictsForChildren(self, rawDict: dict) -> List[dict]:
        """Возвращает список сырых словарей, содержащих данные подэлементов, из сырого словаря `rawDict`.

        .. note:: В базовой реализации возвращает пустой список.
        """
        assert rawDict  # Это только чтобы хоть как-то использовать аргумент.
        return []

    def _sortChildrenItems(self, listOfItems: List[QStandardItem]) -> List[QStandardItem]:
        """Сортирует список элементов `listOfItems` в том порядке, в каком эти элементы должны быть вставлены в модель,
        возвращает отсортированный список.

        .. note:: В базовой реализации возвращает оригинальный список.
        """
        return listOfItems

    def _getDetailsLoadingInfo(self, index: QModelIndex) -> VDetailsLoadingInfo or None:
        """Переопределяет соответствующий родительский метод.

        Возвращает контейнер со вспомогательной (служебной) информацией о загрузке подробных данных об элементе
        с модельным индексом `index`.

        .. note::
            Если загрузка подробных данных не поддерживается для элемента с модельным индексом `index`, возвращает None.

        .. note::
            Результат этого метода зависит от того, установлен ли экземпляр  :class:`VDetailsLoadingInfo` в элемент
            с модельным индексом `index`.

            Смотри описание метода :func:`_createItem()`.
        """
        indexWithZeroColumn = self.sibling(index.row(), self.ZERO_COLUMN, index)
        return self.__localDataModel.data(self._mapToLocal(indexWithZeroColumn), Vns.ItemDataRole._DetailsLoadingInfo)

    def _updateDetails(self, action: VNetworkModelAction) -> bool:
        """Переопределяет соответствующий родительский метод.

        Обновляет подробные данные об элементе, используя данные из действия `action`.

        Возвращает True - если обновление завершилось успешно, иначе - возвращает False.
        """
        index = action.getIndex()
        if not index.isValid():
            return False
        assert index.column() == self.ZERO_COLUMN
        if index.column() != self.ZERO_COLUMN:
            return False
        itemDict = self.data(index, role=Vns.ItemDataRole.ItemDict)
        assert isinstance(itemDict, dict)
        detailsDict = self._prepareDetailsDict(self.convertToDict(action.replyBodyStringData()))
        itemDict.update(detailsDict)
        return self._setData(index, itemDict, role=Vns.ItemDataRole.ItemDict)

    def convertToDict(self, string: str) -> dict:
        """Преобразует строку `string` в сырой словарь и возвращает его.

        .. note:: В базовой реализации используется json.
        """
        if not string:
            print("{}: VAbstractNetworkDataModel.convertToDict(): ERROR! String is empty.".format(type(self)))  # TODO: Исправить вывод ошибки.
            return {}

        rawDict = json.loads(string)
        assert isinstance(rawDict, dict)
        return rawDict

    def _prepareDetailsDict(self, rawDict: dict) -> dict:
        """Осуществляет обработку сырого словаря `rawDict`, содержащего подробные данные об элементе
        и возвращает обработанный словарь.

        .. note:: В базовой реализации возвращает оригинальный словарь.
        """
        return rawDict

    def _moveRow(self, sourceParent: QModelIndex, sourceRow: int, destinationParent: QModelIndex,
            destinationRow: int) -> bool:
        """Перемещает строку `sourceRow` из элемента с модельным индексом `sourceParent`
        в позицию `destinationRow` в элементе с модельным индексом `destinationParent`
        и возвращает True - если строка была успешно перемещена, False - иначе.
        """
        count = 1
        return self._moveRows(sourceParent, sourceRow, count, destinationParent, destinationRow)

    def _moveRows(self, sourceParent: QModelIndex, sourceRow: int, count: int, destinationParent: QModelIndex,
            destinationRow: int) -> bool:
        """Перемещает `count` строк, начиная с `sourceRow` включительно, из элемента с модельным индексом `sourceParent`
        в позицию `destinationRow` в элементе с модельным индексом `destinationParent`
        и возвращает True - если строка была успешно перемещена, False - иначе.

        .. warning:: Правила для значений аргументов такие же, как и для :func:`beginMoveRows()`.
        """
        assert self.checkIndex(sourceParent)
        assert self.checkIndex(destinationParent)
        assert sourceRow >= 0
        assert count > 0
        assert destinationRow >= 0
        if not self.beginMoveRows(sourceParent, sourceRow, sourceRow + count - 1, destinationParent, destinationRow):
            return False

        sourceParentIndex = self._mapToLocal(sourceParent)
        destinationParentIndex = self._mapToLocal(destinationParent)

        # Извлекаем строки из модели, хранящей локальные данные.
        if sourceParentIndex.isValid():
            sourceParentItem = self.__localDataModel.itemFromIndex(sourceParentIndex)
        else:
            sourceParentItem = self.__localDataModel.invisibleRootItem()
        assert isinstance(sourceParentItem, QStandardItem)
        assert sourceRow + count - 1 < sourceParentItem.rowCount()
        takedRows = []
        for i in range(count):
            takedRowItems = sourceParentItem.takeRow(sourceRow)
            takedRows.append(takedRowItems)

        if destinationParentIndex == sourceParentIndex and destinationRow > sourceRow:
            # Если перемещаем вниз в том же родителе, то после извлечения перемещаемых строк те, что ниже - поднимутся.
            destinationRow -= count

        # Вставляем извлеченные строки в место назначения в модели, хранящей локальные данные.
        if destinationParentIndex.isValid():
            destinationParentItem = self.__localDataModel.itemFromIndex(destinationParentIndex)
        else:
            destinationParentItem = self.__localDataModel.invisibleRootItem()
        assert isinstance(destinationParentItem, QStandardItem)
        assert 0 <= destinationRow <= destinationParentItem.rowCount()
        for takedRowItems in takedRows:
            destinationParentItem.insertRow(destinationRow, takedRowItems)
            destinationRow += 1

        self.endMoveRows()
        return True


class _VAbstractNetworkDataExpandedModel(VAbstractNetworkDataModel):
    """Абстрактная загружаемая по сети модель, автоматически определяющая свои роли."""

    def __init__(self, parent: QObject = None):
        super().__init__(parent)

        self.__nextDynamicRole = Vns.ItemDataRole.Custom  # Следующая за последней используемой динамической ролью.
        self.__dynamicRoleNames = dict()

        # self.modelReset.connect(self._resetDynamicRoleNames)
        # self.modelReset.connect(self._resetDynamicRole)

        # TODO: Надо добавить переиспускание сигнала dataChanged() с пустым списком ролей, если он испустился с ролью Vns.ItemDataRole.ItemDict?!

    def nextDynamicRole(self) -> int:
        """Возвращает целочисленную роль, следующую за последней используемой динамической ролью."""
        return self.__nextDynamicRole

    # def _resetDynamicRole(self):
    #     """Сбрасывает роль, следующую за последней используемой динамической ролью, на значение по-умолчанию."""
    #     self.__nextDynamicRole = Vns.ItemDataRole.Custom

    def dynamicRoleNames(self) -> Dict[int, bytes]:
        """Возвращает словарь с динамическими ролями."""
        return self.__dynamicRoleNames

    # def _resetDynamicRoleNames(self):
    #     """Сбрасывает словарь с динамическими ролями на значение по-умолчанию."""
    #     self.__dynamicRoleNames = dict()

    def roleNames(self) -> Dict[int, bytes]:
        """Переопределяет соответствующий родительский метод."""
        # TODO: Чтоб не было конфликтов со стандартными ролями, нужен OrderedDict с нашими ролями в начале словаря!
        roleNames = super().roleNames()
        assert isinstance(roleNames, dict)
        roleNames.update(self.__dynamicRoleNames)
        return roleNames

    def _createItem(self, rawDict: dict, columns: int = None) -> QStandardItem:
        """Переопределяет соответствующий родительский метод."""
        item = super()._createItem(rawDict, columns)
        itemDict = item.data(Vns.ItemDataRole.ItemDict)
        self._generateDynamicRoleNames(itemDict)
        return item

    def _generateDynamicRoleNames(self, itemDict: Dict[str, Any]):
        """Генерирует динамические роли из ключей словаря `itemDict`."""
        for key in itemDict:
            assert isinstance(key, str)
            roleName = key.encode("utf-8")
            assert isinstance(roleName, bytes)
            if roleName not in self.__dynamicRoleNames.values():
                assert roleName not in super().roleNames().values()  # Не должно совпадать со стандартными названиями ролей.
                assert self.__nextDynamicRole not in self.__dynamicRoleNames.keys()
                self.__dynamicRoleNames[self.__nextDynamicRole] = roleName
                self.__nextDynamicRole += 1

    # def role(self, name: Union[bytes, str], default=None) -> int:
    #     """Возвращает роль с названием `name`. Если такой роли не существует, возвращает `default`."""
    #     if isinstance(name, str):
    #         name = name.encode("utf-8")
    #     assert isinstance(name, bytes)
    #     for key, value in self.roleNames().items():
    #         if value == name:
    #             return key
    #     return default

    # def roleNameBytes(self, role: int, default=None) -> bytes:
    #     """Возвращает название роли `role`. Если такой роли не существует, возвращает `default`."""
    #     return self.roleNames().get(role, default)
    #
    # def roleNameString(self, role: int, default=None) -> str:
    #     """Возвращает название роли `role`. Если такой роли не существует, возвращает `default`."""
    #     roleNameBytes = self.roleNameBytes(role, default)
    #     if roleNameBytes is not default:
    #         return roleNameBytes.decode("utf-8")
    #     return default

    # def _roleNameBytes(self, role: int) -> bytes:
    #     """Возвращает название роли `role`."""
    #     return self.roleNames()[role]
    #
    # def _roleNameString(self, role: int) -> str:
    #     """Возвращает название роли `role`."""
    #     return self._roleNameBytes(role).decode("utf-8")

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        """Переопределяет соответствующий родительский метод.

        data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any
        """
        assert self.checkIndex(index)
        # if role is None:
        #     role = Qt.DisplayRole

        if index.isValid():
            if Vns.ItemDataRole.Custom <= role < self.__nextDynamicRole:
                roleName = self.roleNames()[role].decode("utf-8")
                assert isinstance(roleName, str)
                itemDict = super().data(index, Vns.ItemDataRole.ItemDict)
                assert isinstance(itemDict, dict)
                return itemDict.get(roleName, default=None)
            # elif role == Qt.DisplayRole:
            #     displayRoleName = self.roleNames()[role].decode("utf-8")
            #     assert isinstance(displayRoleName, str)
            #     itemDict = super().data(index, Vns.ItemDataRole.ItemDict)
            #     assert isinstance(itemDict, dict)
            #     displayData = itemDict.get(displayRoleName, default=None)
            #     if displayData is not None:
            #         return displayData

        return super().data(index, role)

    def _setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        """Переопределяет соответствующий родительский метод.

        _setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool

        .. note::
            Для динамических ролей:
            заменяет старое значение с указанной ролью на новое, если для этой роли уже сущесвует значение, или
            создает новое значение с указанной ролью, если для этой роли еще не существует никакого значения.
            При этом всегда возвращает True.
        """
        assert self.checkIndex(index)
        # if role is None:
        #     role = Qt.EditRole

        if index.isValid():
            if Vns.ItemDataRole.Custom <= role < self.__nextDynamicRole:
                roleName = self.roleNames()[role].decode("utf-8")
                assert isinstance(roleName, str)
                itemDict = super().data(index, Vns.ItemDataRole.ItemDict)
                assert isinstance(itemDict, dict)
                itemDict[roleName] = value
                return super()._setData(index, itemDict, Vns.ItemDataRole.ItemDict)

        return super()._setData(index, value, role)
