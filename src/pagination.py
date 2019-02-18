#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Этот файл принадлежит проекту "VNetworkData".
Автор: Волков Семён.
"""
from enum import IntEnum, unique

from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot, Q_ENUM
from PyQt5.QtNetwork import QNetworkReply

from .action import VNetworkAction
from .namespace import Vns


# TODO: Пока так помечаем то, что должно быть помечено через макрос Q_INVOKABLE.
vFromQmlInvokable = pyqtSlot


# TODO: Пагинация не нуждается в наследовании от QObject, ей не нужны сигналы и свойства?!
class VAbstractPagination(QObject):
    """Абстрактная пагинация - хранит мета-информацию о загруженных данных."""

    # @vFromQmlInvokable(result=int)
    def getType(self) -> int:
        """Возвращает тип пагинации.

        .. warning::
            Это абстрактный метод, который должны переопределить наследники класса.

        .. note::
            Стандартные типы смотри в :class:`Vns.PaginationType`.
        """
        raise NotImplementedError()

    # @vFromQmlInvokable(result=bool)
    def hasLoadedData(self) -> bool:
        """Возвращает True - если имеются уже загруженные данные, False - иначе.

        .. warning::
            Это абстрактный метод, который должны переопределить наследники класса.
        """
        raise NotImplementedError()

    # @vFromQmlInvokable(result=bool)
    def mustRemoveLoadedDataWhenLoadingNewData(self) -> bool:
        # TODO: Переименовать Remove на Replace?
        """Возвращает True - если уже загруженные данные должны быть удалены при загрузке новых, иначе - False.

        .. warning::
            Это абстрактный метод, который должны переопределить наследники класса.
        """
        raise NotImplementedError()

    # @vFromQmlInvokable(result=bool)
    def canLoadNextData(self) -> bool:
        """Возвращает True - если можно загрузить следующую порцию данных, False - иначе.

        .. warning::
            Это абстрактный метод, который должны переопределить наследники класса.
        """
        raise NotImplementedError()

    def _requestToLoadingNextDataPart(self):
        """Запрашивает загрузку следующей порции данных.

        .. warning::
            Перед вызовом данного метода необходимо убедиться, что вызов метода :func:`canLoadNextData()`
            возвращает True.

        .. warning::
            Это абстрактный метод, который должны переопределить наследники класса.
        """
        raise NotImplementedError()

    # @vFromQmlInvokable(result=bool)
    def canLoadPreviousData(self) -> bool:
        """Возвращает True - если можно загрузить предыдущую порцию данных, False - иначе.

        .. warning::
            Это абстрактный метод, который должны переопределить наследники класса.
        """
        raise NotImplementedError()

    def _requestToLoadingPreviousDataPart(self):
        """Запрашивает загрузку предыдущей порции данных.

        .. warning::
            Перед вызовом данного метода необходимо убедиться, что вызов метода :func:`canLoadPreviousData()`
            возвращает True.

        .. warning::
            Это абстрактный метод, который должны переопределить наследники класса.
        """
        raise NotImplementedError()

    # @vFromQmlInvokable(result=bool)
    def canReloadData(self) -> bool:
        """Возвращает True - если можно загрузить данные, когда они еще не загружены, или перезагрузить их,
        когда они уже загружены, иначе - возвращает False.

        .. warning::
            Это абстрактный метод, который должны переопределить наследники класса.
        """
        raise NotImplementedError()

    def _requestToReloadingData(self):
        """Запрашивает загрузку данных, если они еще не загружены, или их перезагрузку, если они уже загружены.

        .. warning::
            Перед вызовом данного метода необходимо убедиться, что вызов метода :func:`canReloadData()` возвращает True.

        .. warning::
            Это абстрактный метод, который должны переопределить наследники класса.
        """
        raise NotImplementedError()

    def _resetWhenReloadingData(self):
        """Сбрасывает мета-данные пагинации об уже загруженных данных во время перезагрузки.

        .. warning::
            Это абстрактный метод, который должны переопределить наследники класса.
        """
        raise NotImplementedError()

    def _updateAfterLoadingData(self, action: VNetworkAction) -> bool:
        """Обновляет пагинацию после загрузки данных, используя данные из действия `action`.
        Возвращает True - если пагинация была обновлена успешно, False - иначе.

        .. warning::
            Это абстрактный метод, который должны переопределить наследники класса.
        """
        raise NotImplementedError()

    def _resetAll(self):
        """Сбрасывает пагинацию целиком в начальное состояние.

        .. warning::
            Это абстрактный метод, который должны переопределить наследники класса.
        """
        raise NotImplementedError()


class VNothingPagination(VAbstractPagination):
    """Пагинация, не позволяющая загружать никаких данных."""

    @vFromQmlInvokable(result=int)
    def getType(self) -> int:
        """Переопределяет соответствующий родительский метод."""
        return Vns.PaginationType.Nothing

    @vFromQmlInvokable(result=bool)
    def hasLoadedData(self) -> bool:
        """Переопределяет соответствующий родительский метод."""
        return False

    @vFromQmlInvokable(result=bool)
    def mustRemoveLoadedDataWhenLoadingNewData(self) -> bool:
        """Переопределяет соответствующий родительский метод."""
        return False

    @vFromQmlInvokable(result=bool)
    def canLoadNextData(self) -> bool:
        """Переопределяет соответствующий родительский метод."""
        return False

    def _requestToLoadingNextDataPart(self):
        """Переопределяет соответствующий родительский метод."""
        pass

    @vFromQmlInvokable(result=bool)
    def canLoadPreviousData(self) -> bool:
        """Переопределяет соответствующий родительский метод."""
        return False

    def _requestToLoadingPreviousDataPart(self):
        """Переопределяет соответствующий родительский метод."""
        pass

    @vFromQmlInvokable(result=bool)
    def canReloadData(self) -> bool:
        """Переопределяет соответствующий родительский метод."""
        return False

    def _requestToReloadingData(self):
        """Переопределяет соответствующий родительский метод."""
        pass

    def _resetWhenReloadingData(self):
        """Переопределяет соответствующий родительский метод."""
        pass

    def _updateAfterLoadingData(self, action: VNetworkAction) -> bool:
        """Переопределяет соответствующий родительский метод."""
        assert action.replyErrorType() == QNetworkReply.NoError
        assert action.getType() == Vns.ActionType.LoadingChildren
        return True

    def _resetAll(self):
        """Переопределяет соответствующий родительский метод."""
        pass


class VAllTogetherPagination(VAbstractPagination):
    """Пагинация для загрузки всех данных вместе за один раз."""

    # _loadedChanged = pyqtSignal(bool, arguments=['loaded'])
    # """Сигнал об изменении состояния загруженности данных.
    #
    # :param bool loaded: Новое значение состояния загруженности данных: True - если данные загружены, False - иначе.
    # """

    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        self.__loaded = False

    # def _getLoaded(self) -> bool:
    #     """Возвращает состояние загруженности данных: True - если данные загружены, False - иначе."""
    #     return self.__loaded

    def _setLoaded(self, value: bool = True):
        """Устанавливает состояние загруженности данных: True - если данные загружены, False - иначе."""
        if value != self.__loaded:
            self.__loaded = value
            # self._loadedChanged.emit(value)

    def _resetLoaded(self):
        """Сбрасывает состояние загруженности данных на значение по-умолчанию."""
        self._setLoaded(False)

    # loaded = pyqtProperty(type=bool, fget=_getLoaded, fset=_setLoaded, freset=_resetLoaded, notify=_loadedChanged,
    #         doc="Состояние загруженности данных: True - если данные загружены, False - иначе.")

    @vFromQmlInvokable(result=int)
    def getType(self) -> int:
        """Переопределяет соответствующий родительский метод."""
        return Vns.PaginationType.AllTogether

    @vFromQmlInvokable(result=bool)
    def hasLoadedData(self) -> bool:
        """Переопределяет соответствующий родительский метод."""
        return self.__loaded

    @vFromQmlInvokable(result=bool)
    def mustRemoveLoadedDataWhenLoadingNewData(self) -> bool:
        """Переопределяет соответствующий родительский метод."""
        return False

    @vFromQmlInvokable(result=bool)
    def canLoadNextData(self) -> bool:
        """Переопределяет соответствующий родительский метод."""
        return not self.__loaded

    def _requestToLoadingNextDataPart(self):
        """Переопределяет соответствующий родительский метод."""
        pass

    @vFromQmlInvokable(result=bool)
    def canLoadPreviousData(self) -> bool:
        """Переопределяет соответствующий родительский метод."""
        return not self.__loaded

    def _requestToLoadingPreviousDataPart(self):
        """Переопределяет соответствующий родительский метод."""
        pass

    @vFromQmlInvokable(result=bool)
    def canReloadData(self) -> bool:
        """Переопределяет соответствующий родительский метод."""
        return True

    def _requestToReloadingData(self):
        """Переопределяет соответствующий родительский метод."""
        pass

    def _resetWhenReloadingData(self):
        """Переопределяет соответствующий родительский метод."""
        self._resetLoaded()

    def _updateAfterLoadingData(self, action: VNetworkAction) -> bool:
        """Переопределяет соответствующий родительский метод."""
        assert action.replyErrorType() == QNetworkReply.NoError
        assert action.getType() == Vns.ActionType.LoadingChildren
        self._setLoaded(True)
        return True

    def _resetAll(self):
        """Переопределяет соответствующий родительский метод."""
        self._resetLoaded()


class VPagesAccumulationPagination(VAbstractPagination):
    """Пагинация для постраничной загрузки с накоплением страниц."""

    @unique
    class Direction(IntEnum):
        """Направление последовательности загрузки страниц."""

        FromFirstToLast = 0
        """От первой к последней."""

        FromLastToFirst = 1
        """От последней к первой."""

    Q_ENUM(Direction)

    DEFAULT_DIRECTION = Direction.FromFirstToLast
    """Направление последовательности загрузки страниц по-умолчанию."""

    DEFAULT_FIRST_PAGE = 1
    """Номер первой страницы по-умолчанию."""

    DEFAULT_UNKNOWN_LAST_PAGE = -1
    """Номер последней страницы по-умолчанию, пока неизвестен ее реальный номер. # Первая с конца."""

    DEFAULT_CURRENT_PAGE_HEADER = "X-Pagination-Current-Page"
    """Название заголовка с текущей страницой по-умолчанию."""

    DEFAULT_UNKNOWN_PAGE_COUNT = 1
    """Количество страниц по-умолчанию, пока не известно их реальное количество."""

    DEFAULT_PAGE_COUNT_HEADER = "X-Pagination-Page-Count"
    """Название заголовка с количеством страниц по-умолчанию."""

    DEFAULT_PER_PAGE = 25
    """Количество записей на одной странице по-умолчанию."""

    @property
    def DEFAULT_UNKNOWN_CURRENT_PAGE(self) -> int:
        """Номер текущей страницы по-умолчанию, пока не известен ее реальный номер. [Reed only]"""
        return self.DEFAULT_FIRST_PAGE - 1

    directionChanged = pyqtSignal(Direction, arguments=['direction'])
    """Сигнал об изменении направления последовательности загрузки страниц.

    :param Direction direction: Новое направление последовательности загрузки страниц.
    """

    currentPageChanged = pyqtSignal(int, arguments=['currentPage'])
    """Сигнал об изменении номера текущей страницы.

    :param int currentPage: Новый номер текущей страницы.
    """

    currentPageHeaderChanged = pyqtSignal(str, arguments=['currentPageHeader'])
    """Сигнал об изменении заголовка с номером текущей страницы.

    :param str currentPageHeader: Новый заголовок с номером текущей страницы.
    """

    pageCountChanged = pyqtSignal(int, arguments=['pageCount'])
    """Сигнал об изменении количества страниц.

    :param int pageCount: Новое количество страниц.
    """

    pageCountHeaderChanged = pyqtSignal(str, arguments=['pageCountHeader'])
    """Сигнал об изменении заголовка с количеством страниц.

    :param str pageCountHeader: Новый заголовок с количеством страниц.
    """

    perPageChanged = pyqtSignal(int, arguments=['perPage'])
    """Сигнал об изменении количества записей на одной странице.

    :param int perPage: Новое количество записей на одной странице.
    """

    requiredPageChanged = pyqtSignal(int, arguments=['requiredPage'])
    """Сигнал об изменении номера требуемой страницы.

    :param int requiredPage: Новый номер требуемой страницы.
    """

    def __init__(self, parent: QObject = None):
        super().__init__(parent)

        self.__direction = self.DEFAULT_DIRECTION
        if self.__direction == self.Direction.FromFirstToLast:
            self.__requiredPage = self.DEFAULT_FIRST_PAGE
        else:
            assert self.__direction == self.Direction.FromLastToFirst
            self.__requiredPage = self.DEFAULT_UNKNOWN_LAST_PAGE
        self.__currentPage = self.DEFAULT_UNKNOWN_CURRENT_PAGE
        self.__currentPageHeader = self.DEFAULT_CURRENT_PAGE_HEADER
        self.__pageCount = self.DEFAULT_UNKNOWN_PAGE_COUNT
        self.__pageCountHeader = self.DEFAULT_PAGE_COUNT_HEADER
        self.__perPage = self.DEFAULT_PER_PAGE

    def getDirection(self) -> Direction:
        """Возвращает направление последовательности загрузки страниц."""
        return self.__direction

    def setDirection(self, value: Direction):
        """Устанавливает направление последовательности загрузки страниц."""
        # assert not self.hasLoadedData()  # Направление можно настраивать только до начала загрузки!
        if value != self.__direction:
            self.__direction = value
            self.directionChanged.emit(value)

    def resetDirection(self):
        """Сбрасывает направление последовательности загрузки страниц на значение по-умолчанию."""
        self.setDirection(self.DEFAULT_DIRECTION)

    direction = pyqtProperty(type=Direction, fget=getDirection, fset=setDirection, freset=resetDirection,
            notify=directionChanged, doc="Направление последовательности загрузки страниц.")

    def getCurrentPage(self) -> int:
        """Возвращает номер текущей страницы."""
        return self.__currentPage

    def _setCurrentPage(self, value: int):
        """Устанавливает номер текущей страницы."""
        if value != self.__currentPage:
            self.__currentPage = value
            self.currentPageChanged.emit(value)

    def _resetCurrentPage(self):
        """Сбрасывает номер текущей страницы на значение по-умолчанию."""
        self._setCurrentPage(self.DEFAULT_UNKNOWN_CURRENT_PAGE)

    currentPage = pyqtProperty(type=int, fget=getCurrentPage,  # fset=_setCurrentPage, freset=_resetCurrentPage,
            notify=currentPageChanged, doc="Номер текущей страницы.")

    def getCurrentPageHeader(self) -> str:
        """Возвращает заголовок с номером текущей страницы."""
        return self.__currentPageHeader

    def setCurrentPageHeader(self, header: str):
        """Устанавливает заголовок с номером текущей страницы."""
        if header != self.__currentPageHeader:
            self.__currentPageHeader = header
            self.currentPageHeaderChanged.emit(header)

    def resetCurrentPageHeader(self):
        """Сбрасывает заголовок с номером текущей страницы на значение по-умолчанию."""
        self.setCurrentPageHeader(self.DEFAULT_CURRENT_PAGE_HEADER)

    currentPageHeader = pyqtProperty(type=str, fget=getCurrentPageHeader, fset=setCurrentPageHeader,
            freset=resetCurrentPageHeader, notify=currentPageHeaderChanged, doc="Заголовок с номером текущей страницы.")

    def getPageCount(self) -> int:
        """Возвращает количество страниц."""
        return self.__pageCount

    def _setPageCount(self, pageCount: int):
        """Устанавливает количество страниц."""
        assert pageCount >= 0  # TODO: или assert pageCount > 0?
        if pageCount != self.__pageCount:
            self.__pageCount = pageCount
            self.pageCountChanged.emit(pageCount)

    def _resetPageCount(self):
        """Сбрасывает количество страниц на значение по-умолчанию."""
        self._setPageCount(self.DEFAULT_UNKNOWN_PAGE_COUNT)

    pageCount = pyqtProperty(type=int, fget=getPageCount,  # fset=_setPageCount, freset=_resetPageCount,
            notify=pageCountChanged, doc="Количество страниц.")

    def getPageCountHeader(self) -> str:
        """Возвращает заголовок с количеством страниц."""
        return self.__pageCountHeader

    def setPageCountHeader(self, header: str):
        """Устанавливает заголовок с количеством страниц."""
        if header != self.__pageCountHeader:
            self.__pageCountHeader = header
            self.pageCountHeaderChanged.emit(header)

    def resetPageCountHeader(self):
        """Сбрасывает заголовок с количеством страниц на значение по-умолчанию."""
        self.setPageCountHeader(self.DEFAULT_PAGE_COUNT_HEADER)

    pageCountHeader = pyqtProperty(type=str, fget=getPageCountHeader, fset=setPageCountHeader,
            freset=resetPageCountHeader, notify=pageCountHeaderChanged, doc="Заголовок с количеством страниц.")

    def getPerPage(self) -> int:
        """Возвращает количество элементов на странице."""
        return self.__perPage

    def setPerPage(self, perPage: int):
        """Устанавливает количество элементов на странице."""
        # assert not self.hasLoadedData()  # Количество элементов можно настраивать только до начала загрузки!
        if perPage != self.__perPage:
            self.__perPage = perPage
            self.perPageChanged.emit(perPage)

    def resetPerPage(self):
        """Сбрасывает количество элементов на странице на значение по-умолчанию."""
        self.setPerPage(self.DEFAULT_PER_PAGE)

    perPage = pyqtProperty(type=int, fget=getPerPage, fset=setPerPage, freset=resetPerPage, notify=perPageChanged,
            doc="Количество элементов на странице.")

    def getRequiredPage(self) -> int:
        """Возвращает номер требуемой страницы."""
        return self.__requiredPage

    def setRequiredPage(self, requiredPage: int):
        """Устанавливает номер требуемой страницы."""
        if requiredPage != self.__requiredPage:
            self.__requiredPage = requiredPage
            self.requiredPageChanged.emit(requiredPage)

    def resetRequiredPage(self):
        """Сбрасывает номер требуемой страницы на значение по-умолчанию - крайнюю страницу.

        .. note:: Номер крайней страницы зависит от направления последовательности загрузки.
        """
        if self.__direction == self.Direction.FromFirstToLast:
            self.setRequiredPage(self.DEFAULT_FIRST_PAGE)
        else:
            assert self.__direction == self.Direction.FromLastToFirst
            self.setRequiredPage(self.DEFAULT_UNKNOWN_LAST_PAGE)

    requiredPage = pyqtProperty(type=int, fget=getRequiredPage, fset=setRequiredPage, freset=resetRequiredPage,
            notify=requiredPageChanged, doc="Номер требуемой страницы.")

    @vFromQmlInvokable(result=int)
    def getFirstPage(self) -> int:
        """Возвращает номер первой страницы."""
        return self.DEFAULT_FIRST_PAGE

    @vFromQmlInvokable(result=int)
    def getLastPage(self) -> int:
        """Возвращает номер **известной** последней страницы."""
        return self.DEFAULT_FIRST_PAGE + self.__pageCount - 1

    # @vFromQmlInvokable(result=int)
    # def getUnknownLastPage(self) -> int:
    #     """Возвращает номер **не известной** последней страницы."""
    #     return self.DEFAULT_UNKNOWN_LAST_PAGE

    @vFromQmlInvokable(result=int)
    def getType(self) -> int:
        """Переопределяет соответствующий родительский метод."""
        return Vns.PaginationType.PagesAccumulation

    @vFromQmlInvokable(result=bool)
    def hasLoadedData(self) -> bool:
        """Переопределяет соответствующий родительский метод."""
        return self.__currentPage != self.DEFAULT_UNKNOWN_CURRENT_PAGE

    @vFromQmlInvokable(result=bool)
    def mustRemoveLoadedDataWhenLoadingNewData(self) -> bool:
        """Переопределяет соответствующий родительский метод."""
        return False

    @vFromQmlInvokable(result=bool)
    def canLoadNextData(self) -> bool:
        """Переопределяет соответствующий родительский метод.

        Возвращает True - если можно запросить следующую страницу, False - иначе.

        .. note:: Номер страницы зависит от направления последовательности загрузки.
        """
        if self.__currentPage == self.DEFAULT_UNKNOWN_CURRENT_PAGE:
            # Если еще ничего не загружено:
            return True

        if self.__direction == self.Direction.FromFirstToLast:
            return self.__currentPage < self.getLastPage()
        else:
            assert self.__direction == self.Direction.FromLastToFirst
            return self.__currentPage > self.DEFAULT_FIRST_PAGE

    def _requestToLoadingNextDataPart(self):
        """Переопределяет соответствующий родительский метод.

        Запрашивает следующую страницу.

        .. note:: Номер страницы зависит от направления последовательности загрузки.
        """
        assert self.canLoadNextData()
        if self.__currentPage == self.DEFAULT_UNKNOWN_CURRENT_PAGE:
            # Если еще ничего не загружено:
            self.resetRequiredPage()
        else:
            if self.__direction == self.Direction.FromFirstToLast:
                self.setRequiredPage(self.__currentPage + 1)
            else:
                assert self.__direction == self.Direction.FromLastToFirst
                self.setRequiredPage(self.__currentPage - 1)

    @vFromQmlInvokable(result=bool)
    def canLoadPreviousData(self) -> bool:
        """Переопределяет соответствующий родительский метод."""
        return False

    def _requestToLoadingPreviousDataPart(self):
        """Переопределяет соответствующий родительский метод."""
        raise RuntimeError("Method is not supported")  # Программист не проверил :func:`canLoadPreviousData()` перед вызовом этого метода.

    @vFromQmlInvokable(result=bool)
    def canReloadData(self) -> bool:
        """Переопределяет соответствующий родительский метод."""
        return True

    def _requestToReloadingData(self):
        """Переопределяет соответствующий родительский метод."""
        assert self.canReloadData()
        self.resetRequiredPage()

    def _resetWhenReloadingData(self):
        """Переопределяет соответствующий родительский метод."""
        self._resetCurrentPage()

    def _updateAfterLoadingData(self, action: VNetworkAction) -> bool:
        """Переопределяет соответствующий родительский метод."""
        assert action.replyErrorType() == QNetworkReply.NoError
        assert action.getType() == Vns.ActionType.LoadingChildren

        encoding = action.replyEncoding(default="utf-8")

        rawPageCountHeader = self.getPageCountHeader().encode(encoding)
        pageCount, ok = action.replyRawHeader(rawPageCountHeader).toInt()
        # assert ok  # Нет такого заголовка или в нем содержится не число!
        if not ok:
            return False
        self._setPageCount(pageCount)

        rawCurrentPageHeader = self.getCurrentPageHeader().encode(encoding)
        currentPage, ok = action.replyRawHeader(rawCurrentPageHeader).toInt()
        # assert ok  # Нет такого заголовка или в нем содержится не число!
        if not ok:
            return False
        assert currentPage == self.getRequiredPage()
        assert self.DEFAULT_FIRST_PAGE <= currentPage <= self.getLastPage()
        self._setCurrentPage(currentPage)
        return True

    def _resetAll(self):
        """Переопределяет соответствующий родительский метод."""
        self._resetCurrentPage()
        self._resetPageCount()
        self.resetPerPage()
        self.resetRequiredPage()
        self.resetCurrentPageHeader()
        self.resetPageCountHeader()


class VPagesReplacementPagination(VPagesAccumulationPagination):
    """Пагинация для постраничной загрузки с заменой предыдущей (ранее загруженной) страницы на новую."""

    @vFromQmlInvokable(int, result=bool)
    def pageIsValid(self, page: int) -> bool:
        """Возвращает True - если страница с номером `page` корректна (входит в диапазон существующих страниц),
        иначе - возвращает False."""
        return self.DEFAULT_FIRST_PAGE <= page <= self.getLastPage()

    @vFromQmlInvokable(int, result=bool)
    def canLoadPage(self, page: int) -> bool:
        """Возвращает True - если можно запросить страницу с номером `page`, False - иначе."""
        return self.pageIsValid(page)

    def requestToLoadingPage(self, page: int):
        """Запрашивает страницу с номером `page`."""
        assert self.canLoadPage(page)
        self.setRequiredPage(page)

    @vFromQmlInvokable(result=int)
    def getType(self) -> int:
        """Переопределяет соответствующий родительский метод."""
        return Vns.PaginationType.PagesReplacement

    # @vFromQmlInvokable(result=bool)
    # def hasLoadedData(self) -> bool:
    #     """Переопределяет соответствующий родительский метод."""
    #     return super().hasLoadedData()

    @vFromQmlInvokable(result=bool)
    def mustRemoveLoadedDataWhenLoadingNewData(self) -> bool:
        """Переопределяет соответствующий родительский метод."""
        return True

    # @vFromQmlInvokable(result=bool)
    # def canLoadNextData(self) -> bool:
    #     """Переопределяет соответствующий родительский метод."""
    #     return super().canLoadNextData()
    #
    # def _requestToLoadingNextDataPart(self):
    #     """Переопределяет соответствующий родительский метод."""
    #     super()._requestToLoadingNextDataPart()

    @vFromQmlInvokable(result=bool)
    def canLoadPreviousData(self) -> bool:
        """Переопределяет соответствующий родительский метод.

        Возвращает True - если можно запросить предыдущую страницу, False - иначе.

        .. note:: Номер страницы зависит от направления последовательности загрузки.
        """
        if self.__currentPage == self.DEFAULT_UNKNOWN_CURRENT_PAGE:
            # Если еще ничего не загружено:
            return False

        if self.__direction == self.Direction.FromFirstToLast:
            return self.__currentPage > self.DEFAULT_FIRST_PAGE
        else:
            assert self.__direction == self.Direction.FromLastToFirst
            return self.__currentPage < self.getLastPage()

    def _requestToLoadingPreviousDataPart(self):
        """Переопределяет соответствующий родительский метод.

        Запрашивает предыдущую страницу.

        .. note:: Номер страницы зависит от направления последовательности загрузки.
        """
        assert self.canLoadPreviousData()
        if self.__direction == self.Direction.FromFirstToLast:
            self.setRequiredPage(self.__currentPage - 1)
        else:
            assert self.__direction == self.Direction.FromLastToFirst
            self.setRequiredPage(self.__currentPage + 1)

    # @vFromQmlInvokable(result=bool)
    # def canReloadData(self) -> bool:
    #     """Переопределяет соответствующий родительский метод."""
    #     return super().canReloadData()

    def _requestToReloadingData(self):
        """Переопределяет соответствующий родительский метод.

        Запрашивает загрузку крайней страницы, если еще ничего не загружено, или перезагрузку текущей загруженной
        страницы.

        .. note:: Номер крайней страницы зависит от направления последовательности загрузки.
        """
        assert self.canReloadData()
        if self.__currentPage == self.DEFAULT_UNKNOWN_CURRENT_PAGE:
            # Если еще ничего не загружено:
            self.resetRequiredPage()
        else:
            self.setRequiredPage(self.__currentPage)

    # def _resetWhenReloadingData(self):
    #     """Переопределяет соответствующий родительский метод."""
    #     super()._resetWhenReloadingData()  # self._resetCurrentPage()

    # def _updateAfterLoadingData(self, action: VNetworkAction) -> bool:
    #     """Переопределяет соответствующий родительский метод."""
    #     return super()._updateAfterLoadingData(action)

    # def _resetAll(self):
    #     """Переопределяет соответствующий родительский метод."""
    #     super()._resetAll()
